"""Модуль управления HTTP-клиентом для SferaTC Bot."""
import httpx
from httpx import Timeout
from telegram.ext import Application
from config import get_settings

settings = get_settings()
logger = settings.logger

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