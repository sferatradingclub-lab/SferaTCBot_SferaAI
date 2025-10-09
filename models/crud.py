# models/crud.py
from datetime import datetime, date
from typing import Iterator, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from config import ADMIN_CHAT_ID
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
    db.query(User).filter(User.user_id == user_id).update(
        {User.last_seen: datetime.now()},
        synchronize_session=False,
    )
    db.commit()


def set_awaiting_verification(db: Session, user_id: int, status: bool):
    """Устанавливает флаг ожидания верификации."""
    db.query(User).filter(User.user_id == user_id).update(
        {User.awaiting_verification: status},
        synchronize_session=False,
    )
    db.commit()


def approve_user_in_db(db: Session, user_id: int) -> bool:
    """Одобряет пользователя."""
    updated_rows = db.query(User).filter(User.user_id == user_id).update(
        {
            User.is_approved: True,
            User.awaiting_verification: False,
            User.approval_date: datetime.now(),
        },
        synchronize_session=False,
    )
    db.commit()
    return bool(updated_rows)


def reject_user_in_db(db: Session, user_id: int) -> bool:
    """Отклоняет заявку пользователя."""
    updated_rows = db.query(User).filter(User.user_id == user_id).update(
        {User.awaiting_verification: False},
        synchronize_session=False,
    )
    db.commit()
    return bool(updated_rows)


def revoke_user_in_db(db: Session, user_id: int) -> bool:
    """Отзывает одобрение пользователя."""
    updated_rows = db.query(User).filter(User.user_id == user_id).update(
        {
            User.is_approved: False,
            User.approval_date: None,
        },
        synchronize_session=False,
    )
    db.commit()
    return bool(updated_rows)


def ban_user_in_db(db: Session, user_id: int, ban_status: bool) -> bool:
    """Блокирует или разблокирует пользователя."""
    updated_rows = db.query(User).filter(User.user_id == user_id).update(
        {User.is_banned: ban_status},
        synchronize_session=False,
    )
    db.commit()
    return bool(updated_rows)


def iter_broadcast_targets(db: Session, *, chunk_size: int = 500) -> Iterator[int]:
    """Итератор ID пользователей для рассылки без загрузки всей таблицы."""
    admin_id: Optional[int] = None
    if ADMIN_CHAT_ID is not None:
        try:
            admin_id = int(ADMIN_CHAT_ID)
        except (TypeError, ValueError):
            admin_id = None

    query = db.query(User.user_id).filter(User.is_banned.is_(False))
    if admin_id is not None:
        query = query.filter(User.user_id != admin_id)

    for row in query.order_by(User.user_id).yield_per(chunk_size):
        yield getattr(row, "user_id", row[0])


def get_user_by_username(db: Session, username: Optional[str]):
    """Возвращает пользователя по его username без учета регистра."""
    if username is None:
        return None
    normalized_username = username.lower()
    return db.query(User).filter(func.lower(User.username) == normalized_username).first()



def _count_users(db: Session, *conditions) -> int:
    """Возвращает количество пользователей, удовлетворяющих условиям."""
    query = db.query(func.count()).select_from(User)
    if conditions:
        query = query.filter(*conditions)
    result = query.scalar()
    return int(result or 0)



def count_total_users(db: Session) -> int:
    """Подсчитывает общее количество пользователей."""
    return _count_users(db)



def count_approved_users(db: Session) -> int:
    """Подсчитывает количество одобренных пользователей."""
    return _count_users(db, User.is_approved.is_(True))



def count_awaiting_verification_users(db: Session) -> int:
    """Подсчитывает количество пользователей в ожидании верификации."""
    return _count_users(db, User.awaiting_verification.is_(True))



def count_new_users_on_date(db: Session, target_date: date) -> int:
    """Подсчитывает количество пользователей, впервые появившихся в указанную дату."""
    return _count_users(
        db,
        User.first_seen.isnot(None),
        func.date(User.first_seen) == target_date,
    )



def count_active_users_on_date(db: Session, target_date: date) -> int:
    """Подсчитывает количество пользователей, которые были активны в указанную дату."""
    return _count_users(
        db,
        User.last_seen.isnot(None),
        func.date(User.last_seen) == target_date,
    )



def count_approved_users_on_date(db: Session, target_date: date) -> int:
    """Подсчитывает количество пользователей, одобренных в указанную дату."""
    return _count_users(
        db,
        User.approval_date.isnot(None),
        func.date(User.approval_date) == target_date,
    )



def count_active_users_since(db: Session, since_datetime: datetime) -> int:
    """Подсчитывает количество пользователей, активных начиная с указанного времени."""
    return _count_users(
        db,
        User.last_seen.isnot(None),
        User.last_seen >= since_datetime,
    )
