"""Асинхронные базовые настройки для работы с БД."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from config import get_settings

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Определяем, используется ли SQLite
is_sqlite = DATABASE_URL.startswith("sqlite")

# Создаем асинхронный движок с учетом особенностей SQLite
if is_sqlite:
    # Для SQLite нужен этот аргумент для корректной работы в многопоточном окружении Telegram-бота
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Для PostgreSQL и других БД дополнительные аргументы не требуются
    engine = create_async_engine(DATABASE_URL)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

__all__ = ["Base", "AsyncSessionLocal", "engine"]