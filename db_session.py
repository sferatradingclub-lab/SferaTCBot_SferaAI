# db_session.py
from sqlalchemy.orm import sessionmaker
from models.base import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Создает и предоставляет сессию базы данных."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()