"""Модуль вебхук-сервера для SferaTC Bot."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import get_settings
from .routes import telegram

settings = get_settings()
logger = settings.logger
MINI_APP_PUBLIC_DIR = Path(__file__).resolve().parent.parent.parent / "mini_app" / "public"
MINI_APP_STATIC_ROUTE = "/mini-app/static"


def create_webhook_app():
    """Создает и настраивает FastAPI приложение для вебхуков."""
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

    # Подключаем маршруты
    asgi_app.post(f"/{settings.WEBHOOK_PATH}")(telegram)

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

    return asgi_app