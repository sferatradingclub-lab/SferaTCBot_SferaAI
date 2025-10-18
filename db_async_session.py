"""Асинхронные утилиты для работы с сессиями базы данных."""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from models.async_base import AsyncSessionLocal


@asynccontextmanager
async def get_async_db():
    """Предоставляет асинхронную сессию базы данных и гарантирует её закрытие."""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()