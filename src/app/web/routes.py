"""Модуль обработчиков вебхуков для SferaTC Bot."""
from fastapi import Request, Response
from telegram import Update
from config import get_settings
from src.app.core.application import main
from security_utils import validate_telegram_webhook, validate_update_data

settings = get_settings()
logger = settings.logger

# Создаем приложение бота
application = main()


async def _ensure_started() -> None:
    """Гарантирует корректный запуск приложения инициализацию ресурсов."""
    if not application._initialized: # noqa: SLF001 - внутреннее свойство PTB
        await application.initialize()

    from src.app.core.http_client import post_init
    await post_init(application)

    if not application.running:
        await application.start()


async def _ensure_shutdown() -> None:
    """Корректно останавливает приложение и освобождает ресурсы."""
    if application.running:
        await application.stop()

    if application._initialized:  # noqa: SLF001 - внутреннее свойство PTB
        await application.shutdown()

    from src.app.core.http_client import post_shutdown
    await post_shutdown(application)


async def telegram(request: Request) -> Response:
    """Принимает обновления от Telegram."""
    # Проверяем, что запрос пришел от Telegram
    if not validate_telegram_webhook(request):
        return Response(status_code=403)

    try:
        await _ensure_started()

        update_data = await request.json()
        # Проверяем, что данные являются валидным обновлением Telegram
        if not validate_update_data(update_data):
            logger.warning(f"Получены неверные данные обновления: {update_data}")
            return Response(status_code=40)

        update = Update.de_json(data=update_data, bot=application.bot)
        await application.update_queue.put(update)
        return Response(status_code=20)
    except Exception as error: # noqa: BLE001
        logger.error("Ошибка обработки обновления: %s", error)
        return Response(status_code=500)