"""Модуль настройки базы данных для SferaTC Bot."""
from models.base import Base, engine
from config import get_settings

settings = get_settings()
logger = settings.logger


def setup_database() -> None:
    """Создает все таблицы в базе данных на основе моделей SQLAlchemy."""
    logger.info("Настройка базы данных...")
    Base.metadata.create_all(bind=engine)
    logger.info("База данных успешно настрона.")