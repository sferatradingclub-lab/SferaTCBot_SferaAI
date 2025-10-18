"""Асинхронные CRUD-операции для SferaTC Bot."""
from datetime import datetime, date
from typing import Optional

import logging

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import get_settings
from .user import User

settings = get_settings()
logger = logging.getLogger(__name__)


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Получает пользователя по его Telegram ID."""
    logger.info(f"Ищем пользователя с user_id={user_id}")
    result = await db.execute(select(User).filter(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user:
        logger.info(f"Пользователь {user_id} найден в БД.")
    else:
        logger.info(f"Пользователь {user_id} НЕ найден в БД.")
    return user


async def create_user(db: AsyncSession, user_data: dict) -> User:
    """Создает нового пользователя в базе данных."""
    user_id_to_create = user_data['id']
    logger.info(f"Попытка создать пользователя {user_id_to_create}...")
    new_user = User(
        user_id=user_id_to_create,
        username=user_data.get('username'),
        full_name=user_data.get('full_name'),
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        is_approved=False,
        is_banned=False,
        awaiting_verification=False
    )
    try:
        db.add(new_user)
        logger.info(f"Вызываю db.commit для создания пользователя {user_id_to_create}...")
        await db.commit()
        logger.info(f"Создание пользователя {user_id_to_create} успешно подтверждено (commit).")
        logger.info(f"Вызываю db.refresh для пользователя {user_id_to_create}...")
        await db.refresh(new_user)
        logger.info(f"Пользователь {user_id_to_create} успешно обновлен (refresh).")
    except Exception as e:
        logger.error(
            f"!!! ОШИБКА подтверждения (commit/refresh) создания для пользователя {user_id_to_create}: {e}",
            exc_info=True,
        )
        await db.rollback()
        raise
    return new_user


async def update_user_last_seen(db: AsyncSession, user_id: int) -> None:
    """Обновляет время последней активности пользователя."""
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.last_seen = datetime.now()
        await db.commit()


async def set_awaiting_verification(db: AsyncSession, user_id: int, status: bool) -> None:
    """Устанавливает флаг ожидания верификации."""
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.awaiting_verification = status
        await db.commit()


async def approve_user_in_db(db: AsyncSession, user_id: int) -> bool:
    """Одобряет пользователя."""
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.is_approved = True
        user.awaiting_verification = False
        user.approval_date = datetime.now()
        await db.commit()
        return True
    return False


async def reject_user_in_db(db: AsyncSession, user_id: int) -> bool:
    """Отклоняет заявку пользователя."""
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.awaiting_verification = False
        await db.commit()
        return True
    return False


async def revoke_user_in_db(db: AsyncSession, user_id: int) -> bool:
    """Отзывает одобрение пользователя."""
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.is_approved = False
        user.approval_date = None
        await db.commit()
        return True
    return False


async def ban_user_in_db(db: AsyncSession, user_id: int, ban_status: bool) -> bool:
    """Блокирует или разблокирует пользователя."""
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.is_banned = ban_status
        await db.commit()
        return True
    return False


async def delete_user_in_db(db: AsyncSession, user_id: int) -> bool:
    """Удаляет пользователя из базы данных."""
    logger.info(f"Попытка удалить пользователя {user_id}...")
    result = await db.execute(
        select(User).filter(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(f"Пользователь {user_id} не найден для удаления.")
        return False
    try:
        logger.info(f"Найден пользователь {user_id}, вызываю db.delete...")
        await db.delete(user)
        logger.info(f"Вызываю db.commit для удаления пользователя {user_id}...")
        await db.commit()
        logger.info(f"Удаление пользователя {user_id} успешно подтверждено (commit).")
        return True
    except Exception as e:
        logger.error(
            f"!!! ОШИБКА подтверждения (commit) удаления для пользователя {user_id}: {e}",
            exc_info=True,
        )
        await db.rollback()
        return False


async def get_user_by_username(db: AsyncSession, username: Optional[str]) -> Optional[User]:
    """Возвращает пользователя по его username без учета регистра."""
    if username is None:
        return None
    # Экранируем специальные символы для безопасности SQL запроса
    normalized_username = username.lower().replace('%', '\\%').replace('_', '\\_')
    result = await db.execute(
        select(User).filter(func.lower(User.username) == normalized_username)
    )
    return result.scalar_one_or_none()


async def _count_users(db: AsyncSession, *conditions) -> int:
    """Возвращает количество пользователей, удовлетворяющих условиям."""
    query = select(func.count()).select_from(User)
    if conditions:
        query = query.filter(*conditions)
    result = await db.execute(query)
    count = result.scalar()
    return int(count or 0)


async def count_total_users(db: AsyncSession) -> int:
    """Подсчитывает общее количество пользователей."""
    return await _count_users(db)


async def count_approved_users(db: AsyncSession) -> int:
    """Подсчитывает количество одобренных пользователей."""
    return await _count_users(db, User.is_approved.is_(True))


async def count_awaiting_verification_users(db: AsyncSession) -> int:
    """Подсчитывает количество пользователей в ожидании верификации."""
    return await _count_users(db, User.awaiting_verification.is_(True))


async def count_new_users_on_date(db: AsyncSession, target_date: date) -> int:
    """Подсчитывает количество пользователей, впервые появившихся в указанную дату."""
    return await _count_users(
        db,
        User.first_seen.isnot(None),
        func.date(User.first_seen) == target_date,
    )


async def count_active_users_on_date(db: AsyncSession, target_date: date) -> int:
    """Подсчитывает количество пользователей, которые были активны в указанную дату."""
    return await _count_users(
        db,
        User.last_seen.isnot(None),
        func.date(User.last_seen) == target_date,
    )


async def count_approved_users_on_date(db: AsyncSession, target_date: date) -> int:
    """Подсчитывает количество пользователей, одобренных в указанную дату."""
    return await _count_users(
        db,
        User.approval_date.isnot(None),
        func.date(User.approval_date) == target_date,
    )


async def count_active_users_since(db: AsyncSession, since_datetime: datetime) -> int:
    """Подсчитывает количество пользователей, активных начиная с указанного времени."""
    return await _count_users(
        db,
        User.last_seen.isnot(None),
        User.last_seen >= since_datetime,
    )