"""Утилиты для работы с сессиями базы данных."""

from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker

from models.base import engine


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Предоставляет сессию базы данных и гарантирует её закрытие."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
