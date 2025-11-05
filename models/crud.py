# models/crud.py
from datetime import datetime, date
from typing import Iterator, Optional

import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from config import get_settings

settings = get_settings()
from .user import User
from .broadcast import ScheduledBroadcast  # Добавляем импорт новой модели


logger = logging.getLogger(__name__)


def get_user(db: Session, user_id: int):
    """Получает пользователя по его Telegram ID."""
    logger.info(f"Ищем пользователя с user_id={user_id}")
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        logger.info(f"Пользователь {user_id} найден в БД.")
    else:
        logger.info(f"Пользователь {user_id} НЕ найден в БД.")
    return user


def create_user(db: Session, user_data: dict):
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
        db.commit()
        logger.info(f"Создание пользователя {user_id_to_create} успешно подтверждено (commit).")
        logger.info(f"Вызываю db.refresh для пользователя {user_id_to_create}...")
        db.refresh(new_user)
        logger.info(f"Пользователь {user_id_to_create} успешно обновлен (refresh).")
    except Exception as e:
        logger.error(
            f"!!! ОШИБКА подтверждения (commit/refresh) создания для пользователя {user_id_to_create}: {e}",
            exc_info=True,
        )
        db.rollback()
        raise
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


def delete_user_in_db(db: Session, user_id: int) -> bool:
    """Удаляет пользователя из базы данных."""
    logger.info(f"Попытка удалить пользователя {user_id}...")
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        logger.warning(f"Пользователь {user_id} не найден для удаления.")
        return False
    try:
        logger.info(f"Найден пользователь {user_id}, вызываю db.delete...")
        db.delete(user)
        logger.info(f"Вызываю db.commit для удаления пользователя {user_id}...")
        db.commit()
        logger.info(f"Удаление пользователя {user_id} успешно подтверждено (commit).")
        return True
    except Exception as e:
        logger.error(
            f"!!! ОШИБКА подтверждения (commit) удаления для пользователя {user_id}: {e}",
            exc_info=True,
        )
        db.rollback()
        return False


def iter_broadcast_targets(db: Session, *, chunk_size: int = 500) -> Iterator[list[int]]:
    """Итератор батчей ID пользователей для рассылки без загрузки всей таблицы."""
    admin_id: Optional[int] = None
    if settings.ADMIN_CHAT_ID is not None:
        try:
            admin_id = int(settings.ADMIN_CHAT_ID)
        except (TypeError, ValueError):
            admin_id = None

    query = db.query(User.user_id).filter(User.is_banned.is_(False))
    if admin_id is not None:
        query = query.filter(User.user_id != admin_id)

    current_batch = []
    for row in query.order_by(User.user_id).yield_per(chunk_size):
        user_id = getattr(row, "user_id", row[0])
        current_batch.append(user_id)
        
        if len(current_batch) >= chunk_size:
            yield current_batch
            current_batch = []
    
    # Отправляем оставшиеся ID
    if current_batch:
        yield current_batch


def get_user_by_username(db: Session, username: Optional[str]):
    """Возвращает пользователя по его username без учета регистра."""
    if username is None:
        return None
    
    # Безопасный параметризованный запрос вместо экранирования
    return db.query(User).filter(
        func.lower(User.username) == func.lower(username.strip())
    ).first()



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


# CRUD-операции для отложенных рассылок

def create_scheduled_broadcast(db: Session, admin_id: int, message_content: str, scheduled_datetime: datetime):
    """Создает новую отложенную рассылку."""
    scheduled_broadcast = ScheduledBroadcast(
        admin_id=admin_id,
        message_content=message_content,
        scheduled_datetime=scheduled_datetime
    )
    db.add(scheduled_broadcast)
    db.commit()
    db.refresh(scheduled_broadcast)
    return scheduled_broadcast


def get_scheduled_broadcast(db: Session, broadcast_id: int):
    """Получает отложенную рассылку по ID."""
    from config import get_settings
    settings = get_settings()
    logger = settings.logger
    
    logger.info(f"Поиск рассылки с ID: {broadcast_id}")
    broadcast = db.query(ScheduledBroadcast).filter(ScheduledBroadcast.id == broadcast_id).first()
    if broadcast:
        logger.info(f"Найдена рассылка: ID {broadcast.id}, дата {broadcast.scheduled_datetime}, admin_id {broadcast.admin_id}")
    else:
        logger.warning(f"Рассылка с ID {broadcast_id} не найдена")
    return broadcast


def get_scheduled_broadcasts_by_admin(db: Session, admin_id: int):
    """Получает все отложенные рассылки для конкретного администратора."""
    from config import get_settings
    settings = get_settings()
    logger = settings.logger
    
    logger.info(f"Поиск запланированных рассылок для администратора {admin_id}")
    broadcasts = db.query(ScheduledBroadcast).filter(
        ScheduledBroadcast.admin_id == admin_id,
        ScheduledBroadcast.is_sent == False  # noqa: E712
    ).order_by(ScheduledBroadcast.scheduled_datetime).all()
    
    logger.info(f"Найдено {len(broadcasts)} запланированных рассылок для администратора {admin_id}")
    for broadcast in broadcasts:
        logger.debug(f"  - ID: {broadcast.id}, дата: {broadcast.scheduled_datetime}, текст: {broadcast.message_content[:100]}...")
    
    return broadcasts


def get_pending_scheduled_broadcasts(db: Session):
    """Получает все неотправленные отложенные рассылки."""
    from datetime import datetime
    return db.query(ScheduledBroadcast).filter(
        ScheduledBroadcast.is_sent == False,  # noqa: E712
        ScheduledBroadcast.scheduled_datetime <= datetime.now()
    ).order_by(ScheduledBroadcast.scheduled_datetime).all()


def update_scheduled_broadcast(db: Session, broadcast_id: int, **kwargs):
    """Обновляет данные отложенной рассылки."""
    updated_rows = db.query(ScheduledBroadcast).filter(ScheduledBroadcast.id == broadcast_id).update(kwargs)
    db.commit()
    return bool(updated_rows)


def mark_broadcast_as_sent(db: Session, broadcast_id: int):
    """Отмечает рассылку как отправленную."""
    updated_rows = db.query(ScheduledBroadcast).filter(ScheduledBroadcast.id == broadcast_id).update({
        ScheduledBroadcast.is_sent: True,
        ScheduledBroadcast.sent_at: datetime.now()
    })
    db.commit()
    return bool(updated_rows)


def delete_scheduled_broadcast(db: Session, broadcast_id: int):
    """Удаляет отложенную рассылку."""
    from config import get_settings
    settings = get_settings()
    logger = settings.logger
    
    logger.info(f"Попытка удалить рассылку с ID: {broadcast_id}")
    
    try:
        # Прямое удаление записи по ID с возвратом количества измененных строк
        deleted_count = db.query(ScheduledBroadcast).filter(
            ScheduledBroadcast.id == broadcast_id
        ).delete(synchronize_session=False)
        
        if deleted_count > 0:
            db.commit()
            logger.info(f"Рассылка с ID {broadcast_id} успешно удалена из базы данных")
            return True
        else:
            db.rollback()  # Необязательный откат, если ничего не удалено
            logger.warning(f"Рассылка с ID {broadcast_id} не найдена для удаления")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при удалении рассылки с ID {broadcast_id}: {e}", exc_info=True)
        db.rollback()
        return False


def delete_scheduled_messages(db: Session, broadcast_ids: list[int], batch_size: int = 50) -> tuple[int, int, list[int]]:
    """
    Удаляет отложенные рассылки пакетно с retry-логикой и логированием.
    
    Args:
        db: Сессия базы данных
        broadcast_ids: Список ID рассылок для удаления
        batch_size: Размер батча для удаления (по умолчанию 50)
        
    Returns:
        tuple: (успешно удалено, ошибок, список неудачных ID)
    """
    from config import get_settings
    settings = get_settings()
    logger = settings.logger
    
    if not broadcast_ids:
        logger.info("Список ID рассылок пуст, удаление не требуется")
        return 0, 0, []
    
    total_success = 0
    total_errors = 0
    failed_ids = []
    
    logger.info(f"Начинаю пакетное удаление {len(broadcast_ids)} отложенных рассылок")
    
    # Разбиваем список ID на батчи
    for i in range(0, len(broadcast_ids), batch_size):
        batch = broadcast_ids[i:i + batch_size]
        logger.info(f"Обработка батча {i//batch_size + 1}/{(len(broadcast_ids) + batch_size - 1)//batch_size}, размер: {len(batch)}")
        
        # Пытаемся удалить батч
        batch_success = 0
        batch_errors = 0
        
        # Сначала проверяем, какие рассылки существуют
        existing_broadcasts = db.query(ScheduledBroadcast.id).filter(
            ScheduledBroadcast.id.in_(batch)
        ).all()
        
        existing_ids = [b.id for b in existing_broadcasts]
        not_found_ids = [bid for bid in batch if bid not in existing_ids]
        
        if not_found_ids:
            logger.warning(f"Рассылки с ID {not_found_ids} не найдены для удаления")
            batch_errors += len(not_found_ids)
            failed_ids.extend(not_found_ids)
        
        # Удаляем существующие рассылки
        if existing_ids:
            try:
                deleted_count = db.query(ScheduledBroadcast).filter(
                    ScheduledBroadcast.id.in_(existing_ids)
                ).delete(synchronize_session=False)
                
                db.commit()
                batch_success += deleted_count
                logger.info(f"Успешно удалено {deleted_count} рассылок из батча")
                
            except Exception as e:
                logger.error(f"Ошибка при удалении батча {existing_ids}: {e}", exc_info=True)
                db.rollback()
                batch_errors += len(existing_ids)
                failed_ids.extend(existing_ids)
        
        total_success += batch_success
        total_errors += batch_errors
        
        # Делаем небольшую паузу между батчами, чтобы не перегружать БД
        import time
        time.sleep(0.1)
    
    logger.info(f"Пакетное удаление завершено: {total_success} успешно, {total_errors} ошибок")
    
    return total_success, total_errors, failed_ids


def delete_scheduled_messages_by_admin(db: Session, admin_id: int, batch_size: int = 50) -> tuple[int, int, list[int]]:
    """
    Удаляет все отложенные рассылки для конкретного администратора.
    
    Args:
        db: Сессия базы данных
        admin_id: ID администратора
        batch_size: Размер батча для удаления (по умолчанию 50)
        
    Returns:
        tuple: (успешно удалено, ошибок, список неудачных ID)
    """
    from config import get_settings
    settings = get_settings()
    logger = settings.logger
    
    logger.info(f"Начинаю удаление всех отложенных рассылок для администратора {admin_id}")
    
    # Получаем все ID рассылок для администратора
    broadcast_ids = [
        broadcast.id for broadcast in
        db.query(ScheduledBroadcast.id).filter(
            ScheduledBroadcast.admin_id == admin_id
        ).all()
    ]
    
    if not broadcast_ids:
        logger.info(f"Для администратора {admin_id} нет отложенных рассылок для удаления")
        return 0, 0, []
    
    logger.info(f"Найдено {len(broadcast_ids)} отложенных рассылок для администратора {admin_id}")
    
    # Выполняем пакетное удаление
    return delete_scheduled_messages(db, broadcast_ids, batch_size)
