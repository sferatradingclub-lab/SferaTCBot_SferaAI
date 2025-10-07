from datetime import time
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from fastapi import FastAPI, Request, Response
import uvicorn

from config import (
    TELEGRAM_TOKEN,
    WEBHOOK_URL,
    WEBHOOK_PORT,
    WEBHOOK_PATH,
    WEBHOOK_LISTEN,
    WEBHOOK_SECRET_TOKEN,
    WEBHOOK_DROP_PENDING_UPDATES,
    BOT_USERNAME,
    logger,
    ensure_required_settings,
    SUPPORT_ESCALATION_CALLBACK
)

# Импорты для настройки базы данных
from models.base import Base, engine
from models.user import User # Убедитесь, что импортируете все ваши модели

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

def setup_database():
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


def main() -> Application:
    """Главная функция, которая собирает и запускает бота."""

    # Сначала настраиваем базу данных
    setup_database()

    # Проверяем наличие обязательных настроек перед запуском бота
    ensure_required_settings()

    # Собираем приложение и добавляем post_shutdown callback
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )


    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---

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
    application.add_handler(CallbackQueryHandler(escalate_support_to_admin, pattern=rf'^{SUPPORT_ESCALATION_CALLBACK}$'))

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
    application.job_queue.run_daily(daily_stats_job, time=time(0, 0), name="daily_stats_report")
    
    return application

# --- ЗАПУСК БОТА ---
if WEBHOOK_URL:
    # --- ЗАПУСК БОТА ЧЕРЕЗ ASGI ---
    asgi_app = FastAPI()
    application = main()

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
        await application.bot.set_webhook(
            url=f"{WEBHOOK_URL.rstrip('/')}/{WEBHOOK_PATH}",
            secret_token=WEBHOOK_SECRET_TOKEN,
            drop_pending_updates=WEBHOOK_DROP_PENDING_UPDATES,
        )

    @asgi_app.on_event("shutdown")
    async def on_shutdown() -> None:
        """Выполняется при остановке сервера."""
        await _ensure_shutdown()

    @asgi_app.post(f"/{WEBHOOK_PATH}")
    async def telegram(request: Request) -> Response:
        """Принимает обновления от Telegram."""
        if WEBHOOK_SECRET_TOKEN:
            secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_header != WEBHOOK_SECRET_TOKEN:
                return Response(status_code=403)

        try:
            await _ensure_started()

            update_data = await request.json()
            update = Update.de_json(data=update_data, bot=application.bot)
            await application.process_update(update)
            return Response(status_code=200)
        except Exception as error:  # noqa: BLE001
            logger.error("Ошибка обработки обновления: %s", error)
            return Response(status_code=500)

    # Запуск Uvicorn, если файл запущен напрямую (для локальной отладки)
    if __name__ == "__main__":
        uvicorn.run(
            asgi_app,
            host=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
        )
else:
    # --- ЗАПУСК В РЕЖИМЕ POLLING ---
    logger.info(f"Бот @{BOT_USERNAME} запускается в режиме Polling.")
    application = main()
    application.run_polling()
