"""Модуль создания и настройки приложения для SferaTC Bot."""
from datetime import time
from zoneinfo import ZoneInfo
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import get_settings
from models.user import User  # Убедитесь, что импортируете все ваши модели
from handlers.common_handlers import (
    start,
    help_command,
    handle_message,
    show_training_menu,
    show_psychologist_menu,
)
from handlers.user.chatgpt_handler import show_chatgpt_menu, stop_chatgpt_session
from handlers.user.support_handler import show_support_menu, escalate_support_to_admin
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
from .database import setup_database
from .http_client import post_init, post_shutdown
from .error_handler import global_error_handler

settings = get_settings()
logger = settings.logger


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
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^Пройти бесплатное обучение$"),
            show_training_menu,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^ИИ-психолог$"),
            show_psychologist_menu,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^Полезные инструменты$"),
            show_tools_menu,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^Бесплатный ChatGPT$"),
            show_chatgpt_menu,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^Поддержка$"),
            show_support_menu,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^👑 Админка$"),
            show_admin_panel,
        )
    )

    # Все остальные сообщения пользователя (должен быть последним!)
    media_filters = (
        filters.TEXT
        | filters.PHOTO
        | filters.VIDEO
        | filters.Document.ALL
        | filters.AUDIO
    )
    application.add_handler(MessageHandler(media_filters & ~filters.COMMAND, handle_message))

    # Задачи
    application.job_queue.run_daily(
        daily_stats_job,
        time=time(0, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        name="daily_stats_report",
    )

    return application