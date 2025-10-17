import traceback
from pprint import pformat
from datetime import time
from zoneinfo import ZoneInfo
from pathlib import Path

import httpx
from httpx import Timeout
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import get_settings

# Импорты для настройки базы данных
from models.base import Base, engine
from models.user import User  # Убедитесь, что импортируете все ваши модели

# Импортируем наши обработчики
from handlers.common_handlers import (
    start,
    help_command,
    handle_message,
    show_training_menu,
    show_psychologist_menu,
    show_chatgpt_menu,
    show_support_menu,
    stop_chatgpt_session,
    escalate_support_to_admin
)
from handlers.admin_handlers import (
    show_admin_panel,
    admin_menu_handler,
    broadcast_confirmation_handler,
    approve_user,
    reset_user,
    show_stats,
    show_status,
    daily_stats_job,
)
from handlers.tools_handlers import (
    show_tools_menu,
    tools_menu_handler,
)
from handlers.verification_handlers import (
    user_actions_handler,
    support_rejection_handler,
    support_dm_handler,
)

settings = get_settings()
logger = settings.logger
MINI_APP_PUBLIC_DIR = Path(__file__).resolve().parent / "mini_app" / "public"
MINI_APP_STATIC_ROUTE = "/mini-app/static"


def setup_database() -> None:
    """Создает все таблицы в базе данных на основе моделей SQLAlchemy."""
    logger.info("Настройка базы данных...")
    Base.metadata.create_all(bind=engine)
    logger.info("База данных успешно настроена.")


ASYNC_HTTPX_KEY = "httpx_client"


async def post_init(application: Application) -> None:
    """Инициализирует HTTP-клиент OpenRouter после запуска приложения."""
    if ASYNC_HTTPX_KEY in application.bot_data:
        client = application.bot_data[ASYNC_HTTPX_KEY]
        if isinstance(client, httpx.AsyncClient) and not getattr(client, "is_closed", False):
            return

    application.bot_data[ASYNC_HTTPX_KEY] = httpx.AsyncClient(timeout=Timeout(10.0, read=30.0))


async def post_shutdown(application: Application) -> None:
    """Корректно закрывает HTTP-клиент перед остановкой приложения."""
    client = application.bot_data.pop(ASYNC_HTTPX_KEY, None)

    if isinstance(client, httpx.AsyncClient) and not getattr(client, "is_closed", False):
        try:
            await client.aclose()
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось корректно закрыть AsyncClient OpenRouter: %s", exc)


def _sanitize_code_block(text: str) -> str:
    """Экранирует тройные кавычки внутри блока кода MarkdownV2."""

    return text.replace("```", "\\`\\`\\`") if text else ""


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок PTB на случай неперехваченных исключений."""

    error = getattr(context, "error", None)

    if isinstance(error, Exception):
        logger.error("Неперехваченное исключение в PTB: %s", error, exc_info=True)
        captured_error = error
    elif error is not None:
        logger.error("Неперехваченное исключение в PTB (неизвестный тип): %r", error)
        captured_error = Exception(str(error))
    else:
        logger.error("Неперехваченное исключение в PTB без объекта ошибки")
        captured_error = Exception("Неизвестная ошибка")

    if isinstance(update, Update):
        try:
            update_repr = pformat(update.to_dict())
        except Exception:  # noqa: BLE001
            update_repr = repr(update)
    else:
        update_repr = repr(update)

    update_block = _sanitize_code_block(update_repr or "None")

    traceback_lines = traceback.format_exception(
        type(captured_error),
        captured_error,
        captured_error.__traceback__,
    )
    traceback_text = "".join(traceback_lines)
    traceback_block = _sanitize_code_block(traceback_text or "Нет данных")

    admin_message = (
        "🔴 *Глобальная ошибка в боте* 🔴\n\n"
        "*Update:*\n"
        f"```\n{update_block}\n```\n\n"
        "*Traceback:*\n"
        f"```traceback\n{traceback_block}\n```"
    )

    bot = getattr(context, "bot", None)
    if not bot:
        return

    try:
        await bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
    except Exception as send_error:  # noqa: BLE001
        logger.error(
            "Не удалось отправить сообщение админу о глобальной ошибке: %s",
            send_error,
        )


def main() -> Application:
    """Главная функция, которая собирает и запускает бота."""

    setup_database()

    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_error_handler(global_error_handler)

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
    application.add_handler(CallbackQueryHandler(admin_menu_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(broadcast_confirmation_handler, pattern='^broadcast_'))
    application.add_handler(CallbackQueryHandler(tools_menu_handler, pattern='^tool'))
    application.add_handler(CallbackQueryHandler(user_actions_handler, pattern='^user_'))
    application.add_handler(CallbackQueryHandler(support_rejection_handler, pattern='^support_from_rejection$'))
    application.add_handler(CallbackQueryHandler(support_dm_handler, pattern='^support_from_dm$'))
    application.add_handler(CallbackQueryHandler(escalate_support_to_admin, pattern=rf'^{settings.SUPPORT_ESCALATION_CALLBACK}$'))

    # Кнопки главного меню (MessageHandler)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Пройти бесплатное обучение$'), show_training_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^ИИ-психолог$'), show_psychologist_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Полезные инструменты$'), show_tools_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Бесплатный ChatGPT$'), show_chatgpt_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Поддержка$'), show_support_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^👑 Админка$'), show_admin_panel))

    # Все остальные текстовые сообщения (должен быть последним!)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Задачи
    application.job_queue.run_daily(
        daily_stats_job,
        time=time(0, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        name="daily_stats_report",
    )

    return application


if settings.WEBHOOK_URL:
    asgi_app = FastAPI()
    asgi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://web.telegram.org", "https://t.me"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    asgi_app.mount(
        MINI_APP_STATIC_ROUTE,
        StaticFiles(directory=MINI_APP_PUBLIC_DIR),
        name="mini_app_static",
    )
    application = main()

    @asgi_app.get("/", include_in_schema=False)
    async def serve_mini_app() -> FileResponse:
        """Отдает HTML мини-приложения с заголовками, запрещающими кэширование."""

        response = FileResponse(MINI_APP_PUBLIC_DIR / "index.html")
        # Telegram-клиенты агрессивно кешируют HTML. Это приводит к тому, что
        # пользователи в мобильных клиентах видят устаревшую разметку (например,
        # кнопку "Закрыть"). Явно запрещаем кеширование, чтобы гарантировать
        # получение свежей версии страницы без необходимости ручного обновления.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    async def _ensure_started() -> None:
        """Гарантирует корректный запуск приложения и инициализацию ресурсов."""
        if not application._initialized:  # noqa: SLF001 - внутреннее свойство PTB
            await application.initialize()

        await post_init(application)

        if not application.running:
            await application.start()

    async def _ensure_shutdown() -> None:
        """Корректно останавливает приложение и освобождает ресурсы."""
        if application.running:
            await application.stop()

        if application._initialized:  # noqa: SLF001 - внутреннее свойство PTB
            await application.shutdown()

        await post_shutdown(application)

    @asgi_app.on_event("startup")
    async def on_startup() -> None:
        """Выполняется при старте сервера."""
        await _ensure_started()
        webhook_base = settings.WEBHOOK_URL.rstrip("/")
        webhook_path = settings.WEBHOOK_PATH
        webhook_url = f"{webhook_base}/{webhook_path}" if webhook_path else f"{webhook_base}/"
        await application.bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET_TOKEN,
            drop_pending_updates=settings.WEBHOOK_DROP_PENDING_UPDATES,
        )

    @asgi_app.on_event("shutdown")
    async def on_shutdown() -> None:
        """Выполняется при остановке сервера."""
        await _ensure_shutdown()

    @asgi_app.post(f"/{settings.WEBHOOK_PATH}")
    async def telegram(request: Request) -> Response:
        """Принимает обновления от Telegram."""
        if settings.WEBHOOK_SECRET_TOKEN:
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_header != settings.WEBHOOK_SECRET_TOKEN:
                return Response(status_code=403)

        try:
            await _ensure_started()

            update_data = await request.json()
            update = Update.de_json(data=update_data, bot=application.bot)
            await application.update_queue.put(update)
            return Response(status_code=200)
        except Exception as error:  # noqa: BLE001
            logger.error("Ошибка обработки обновления: %s", error)
            return Response(status_code=500)

    if __name__ == "__main__":
        uvicorn.run(
            asgi_app,
            host=settings.WEBHOOK_LISTEN,
            port=settings.WEBHOOK_PORT,
        )
else:
    logger.info(f"Бот @{settings.BOT_USERNAME} запускается в режиме Polling.")
    application = main()
    application.run_polling()
