"""Утилиты для работы с сессиями базы данных."""

from contextlib import contextmanager

from models.base import SessionLocal


@contextmanager
def get_db():
    """Предоставляет сессию базы данных и гарантирует её закрытие."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
