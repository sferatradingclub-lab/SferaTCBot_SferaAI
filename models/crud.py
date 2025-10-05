# models/crud.py
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from .user import User

def get_user(db: Session, user_id: int):
    """Получает пользователя по его Telegram ID."""
    return db.query(User).filter(User.user_id == user_id).first()

def create_user(db: Session, user_data: dict):
    """Создает нового пользователя в базе данных."""
    new_user = User(
        user_id=user_data['id'],
        username=user_data.get('username'),
        full_name=user_data.get('full_name'),
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        is_approved=False,
        is_banned=False,
        awaiting_verification=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def update_user_last_seen(db: Session, user_id: int):
    """Обновляет время последней активности пользователя."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.last_seen = datetime.now()
        db.commit()

def set_awaiting_verification(db: Session, user_id: int, status: bool):
    """Устанавливает флаг ожидания верификации."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.awaiting_verification = status
        db.commit()

def approve_user_in_db(db: Session, user_id: int):
    """Одобряет пользователя."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.is_approved = True
        db_user.awaiting_verification = False
        db_user.approval_date = datetime.now()
        db.commit()
    return db_user

def reject_user_in_db(db: Session, user_id: int):
    """Отклоняет заявку пользователя."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.awaiting_verification = False
        db.commit()
    return db_user

def revoke_user_in_db(db: Session, user_id: int):
    """Отзывает одобрение пользователя."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.is_approved = False
        db_user.approval_date = None
        db.commit()
    return db_user

def ban_user_in_db(db: Session, user_id: int, ban_status: bool):
    """Блокирует или разблокирует пользователя."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.is_banned = ban_status
        db.commit()
    return db_user
    
def get_all_users(db: Session):
    """Возвращает всех пользователей."""
    return db.query(User).all()


def get_user_by_username(db: Session, username: str):
    """Возвращает пользователя по его username без учета регистра."""
    return db.query(User).filter(func.lower(User.username) == username).first()
