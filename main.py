from datetime import time
from json import JSONDecodeError

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import (
    BOT_USERNAME,
    SUPPORT_ESCALATION_CALLBACK,
    TELEGRAM_TOKEN,
    WEBHOOK_DROP_PENDING_UPDATES,
    WEBHOOK_LISTEN,
    WEBHOOK_PATH,
    WEBHOOK_PORT,
    WEBHOOK_SECRET_TOKEN,
    WEBHOOK_URL,
    ensure_required_settings,
    logger,
)
from handlers.admin_handlers import (
    admin_menu_handler,
    approve_user,
    broadcast_confirmation_handler,
    daily_stats_job,
    reset_user,
    show_admin_panel,
    show_stats,
    show_status,
)
from handlers.common_handlers import (
    escalate_support_to_admin,
    handle_message,
    help_command,
    show_chatgpt_menu,
    show_psychologist_menu,
    show_support_menu,
    show_training_menu,
    start,
    stop_chatgpt_session,
)
from handlers.tools_handlers import show_tools_menu, tools_menu_handler
from handlers.verification_handlers import (
    support_dm_handler,
    support_rejection_handler,
    user_actions_handler,
)
from models.base import Base, engine
from models.user import User  # noqa: F401  # Убедитесь, что импортируете все ваши модели


def setup_database() -> None:
    """Создает все таблицы в базе данных на основе моделей SQLAlchemy."""
    logger.info("Настройка базы данных...")
    Base.metadata.create_all(bind=engine)
    logger.info("База данных успешно настроена.")


async def post_init(application: Application) -> None:
    """Инициализирует HTTP-клиент OpenRouter после запуска приложения."""
    if "httpx_client" in application.bot_data:
        client = application.bot_data["httpx_client"]
        if isinstance(client, httpx.AsyncClient) and not getattr(client, "is_closed", False):
            return

    application.bot_data["httpx_client"] = httpx.AsyncClient(timeout=60.0)


async def post_shutdown(application: Application) -> None:
    """Корректно закрывает HTTP-клиент перед остановкой приложения."""
    client = application.bot_data.pop("httpx_client", None)

    if isinstance(client, httpx.AsyncClient) and not getattr(client, "is_closed", False):
        try:
            await client.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось корректно закрыть AsyncClient OpenRouter: %s", exc)


def _configure_handlers(application: Application) -> None:
    """Регистрирует обработчики команд, сообщений и задач."""
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("training", show_training_menu))
    application.add_handler(CommandHandler("psychologist", show_psychologist_menu))
    application.add_handler(CommandHandler("tools", show_tools_menu))
    application.add_handler(CommandHandler("chatgpt", show_chatgpt_menu))
    application.add_handler(CommandHandler("support", show_support_menu))
    application.add_handler(CommandHandler("stop_chat", stop_chatgpt_session))

    # Команды только для админа
    application.add_handler(CommandHandler("admin", show_admin_panel))
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("status", show_status))
    application.add_handler(CommandHandler("reset_user", reset_user))

    # Инлайн-кнопки (CallbackQueryHandler)
    application.add_handler(CallbackQueryHandler(admin_menu_handler, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(broadcast_confirmation_handler, pattern="^broadcast_"))
    application.add_handler(CallbackQueryHandler(tools_menu_handler, pattern="^tool"))
    application.add_handler(CallbackQueryHandler(user_actions_handler, pattern="^user_"))
    application.add_handler(CallbackQueryHandler(support_rejection_handler, pattern="^support_from_rejection$"))
    application.add_handler(CallbackQueryHandler(support_dm_handler, pattern="^support_from_dm$"))
    application.add_handler(
        CallbackQueryHandler(escalate_support_to_admin, pattern=rf"^{SUPPORT_ESCALATION_CALLBACK}$")
    )

    # Кнопки главного меню (MessageHandler)
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex("^Пройти бесплатное обучение$"), show_training_menu)
    )
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^ИИ-психолог$"), show_psychologist_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Полезные инструменты$"), show_tools_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Бесплатный ChatGPT$"), show_chatgpt_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Поддержка$"), show_support_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^👑 Админка$"), show_admin_panel))

    # Все остальные текстовые сообщения (должен быть последним!)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Задачи
    application.job_queue.run_daily(daily_stats_job, time=time(0, 0), name="daily_stats_report")


def build_application() -> Application:
    """Создает и настраивает экземпляр Telegram Application."""
    setup_database()
    ensure_required_settings()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    _configure_handlers(application)
    return application


telegram_application = build_application()
WEBHOOK_ROUTE_PATH = f"/{WEBHOOK_PATH}" if WEBHOOK_PATH else "/"
asgi_app = FastAPI()


def _resolve_webhook_urls() -> tuple[str, str]:
    base_webhook_url = WEBHOOK_URL.rstrip("/") if WEBHOOK_URL else ""

    if WEBHOOK_PATH:
        return f"{base_webhook_url}/{WEBHOOK_PATH}", f"/{WEBHOOK_PATH}"

    return f"{base_webhook_url}/", "/"


@asgi_app.on_event("startup")
async def on_startup() -> None:
    """Подготавливает Telegram Application и настраивает вебхук при запуске FastAPI."""
    await telegram_application.initialize()
    await telegram_application.start()

    if not WEBHOOK_URL:
        logger.warning("WEBHOOK_URL не задан, но FastAPI приложение запущено без настройки вебхука.")
        return

    webhook_full_url, display_path = _resolve_webhook_urls()
    logger.info(
        "Настройка вебхука Telegram (url='%s', path='%s', drop_pending_updates=%s).",
        webhook_full_url,
        display_path,
        WEBHOOK_DROP_PENDING_UPDATES,
    )

    await telegram_application.bot.set_webhook(
        url=webhook_full_url,
        secret_token=WEBHOOK_SECRET_TOKEN,
        drop_pending_updates=WEBHOOK_DROP_PENDING_UPDATES,
    )

    if WEBHOOK_SECRET_TOKEN:
        logger.info("Используется секретный токен вебхука.")


@asgi_app.on_event("shutdown")
async def on_shutdown() -> None:
    """Останавливает Telegram Application при завершении работы FastAPI."""
    await telegram_application.stop()
    await telegram_application.shutdown()


@asgi_app.post(WEBHOOK_ROUTE_PATH)
async def telegram_webhook(request: Request) -> Response:
    """Принимает обновления Telegram и передает их в очередь обработки бота."""
    if WEBHOOK_SECRET_TOKEN:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != WEBHOOK_SECRET_TOKEN:
            logger.warning("Получен запрос с некорректным секретным токеном вебхука.")
            return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        update_data = await request.json()
    except (ValueError, JSONDecodeError):
        logger.warning("Получен запрос с некорректным JSON телом.")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        update = Update.de_json(data=update_data, bot=telegram_application.bot)
    except Exception as exc:  # noqa: BLE001
        logger.error("Не удалось десериализовать обновление Telegram: %s", exc)
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    try:
        await telegram_application.process_update(update)
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка обработки обновления Telegram: %s", exc, exc_info=exc)
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(status_code=status.HTTP_200_OK)


def main() -> None:
    """Главная функция, которая запускает бота в режиме webhook или polling."""
    if WEBHOOK_URL:
        webhook_full_url, display_path = _resolve_webhook_urls()
        logger.info(
            "Бот @%s запускается через Webhook (listen=%s, port=%s, path='%s', url='%s') с сервером Uvicorn.",
            BOT_USERNAME,
            WEBHOOK_LISTEN,
            WEBHOOK_PORT,
            display_path,
            webhook_full_url,
        )
        if WEBHOOK_SECRET_TOKEN:
            logger.info("Используется секретный токен вебхука.")

        uvicorn.run(
            asgi_app,
            host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
        )
    else:
        logger.info("Бот @%s запускается в режиме Polling.", BOT_USERNAME)
        telegram_application.run_polling()


if __name__ == "__main__":
    main()
