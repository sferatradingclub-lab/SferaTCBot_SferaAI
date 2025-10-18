"""Модуль запуска приложения для SferaTC Bot."""
import uvicorn
from config import get_settings
from .core.application import main
from .web.server import create_webhook_app

settings = get_settings()
logger = settings.logger


def run_application():
    """Запускает приложение в режиме вебхуков или polling."""
    if settings.WEBHOOK_URL:
        # Режим вебхуков
        asgi_app = create_webhook_app()
        
        # Добавляем обработчики startup и shutdown
        @asgi_app.on_event("startup")
        async def on_startup():
            """Выполняется при старте сервера."""
            from src.app.web.routes import _ensure_started
            await _ensure_started()
            webhook_base = settings.WEBHOOK_URL.rstrip("/")
            webhook_path = settings.WEBHOOK_PATH
            webhook_url = f"{webhook_base}/{webhook_path}" if webhook_path else f"{webhook_base}/"
            from src.app.web.routes import application
            await application.bot.set_webhook(
                url=webhook_url,
                secret_token=settings.WEBHOOK_SECRET_TOKEN,
                drop_pending_updates=settings.WEBHOOK_DROP_PENDING_UPDATES,
            )

        @asgi_app.on_event("shutdown")
        async def on_shutdown():
            """Выполняется при остановке сервера."""
            from src.app.web.routes import _ensure_shutdown
            await _ensure_shutdown()

        if __name__ == "__main__":
            uvicorn.run(
                asgi_app,
                host=settings.WEBHOOK_LISTEN,
                port=settings.WEBHOOK_PORT,
            )
    else:
        # Режим polling
        logger.info(f"Бот @{settings.BOT_USERNAME} запускается в режиме Polling.")
        application = main()
        # Добавляем проверку наличия вебхука и выводим предупреждение о безопасности
        if not settings.WEBHOOK_URL:
            logger.warning(
                "ВНИМАНИЕ: Бот запускается в режиме polling без вебхука. "
                "Рекомендуется использовать вебхуки для продакшена. "
                "Убедитесь, что токен Telegram защищен и не публикуется в открытом виде."
            )
        application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_application()