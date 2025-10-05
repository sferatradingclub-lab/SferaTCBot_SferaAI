import asyncio
from datetime import time
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

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

from services.chatgpt_service import close_chatgpt_client

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

def main() -> None:
    """Главная функция, которая собирает и запускает бота."""

    # Сначала настраиваем базу данных
    setup_database()

    # Проверяем наличие обязательных настроек перед запуском бота
    ensure_required_settings()

    # Собираем приложение и добавляем post_shutdown callback
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_shutdown(close_chatgpt_client)
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

    # --- ЗАПУСК БОТА ---
    if WEBHOOK_URL:
        webhook_path = WEBHOOK_PATH or (TELEGRAM_TOKEN.split(':')[-1] if TELEGRAM_TOKEN else "")
        webhook_full_url = WEBHOOK_URL.rstrip('/')
        if webhook_path:
            webhook_full_url = f"{webhook_full_url}/{webhook_path}"

        logger.info(
            "Бот @%s запускается через Webhook (listen=%s, port=%s, path='/%s').",
            BOT_USERNAME,
            WEBHOOK_LISTEN,
            WEBHOOK_PORT,
            webhook_path,
        )
        if WEBHOOK_SECRET_TOKEN:
            logger.info("Используется секретный токен вебхука.")

        application.run_webhook(
            listen=WEBHOOK_LISTEN,
            port=WEBHOOK_PORT,
            url_path=webhook_path,
            webhook_url=webhook_full_url,
            secret_token=WEBHOOK_SECRET_TOKEN,
            drop_pending_updates=WEBHOOK_DROP_PENDING_UPDATES,
        )
    else:
        logger.info(f"Бот @{BOT_USERNAME} запускается в режиме Polling.")
        application.run_polling()

if __name__ == "__main__":
    main()
