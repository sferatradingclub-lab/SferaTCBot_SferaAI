from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_settings

settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

# Определяем, используется ли SQLite
is_sqlite = DATABASE_URL.startswith("sqlite")

# Создаем движок с учетом особенностей SQLite
if is_sqlite:
    # Для SQLite нужен этот аргумент для корректной работы в многопоточном окружении Telegram-бота
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Для PostgreSQL и других БД дополнительные аргументы не требуются
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

__all__ = ["Base", "SessionLocal", "engine"]
