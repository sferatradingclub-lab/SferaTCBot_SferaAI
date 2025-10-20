from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from datetime import datetime

from models.user import User
from models.crud import get_user


class DatabaseOptimizer:
    """Сервис для оптимизированных операций с базой данных."""
    
    @staticmethod
    def get_user_optimized(db: Session, user_id: int) -> Optional[User]:
        """Оптимизированное получение пользователя с минимальными полями при необходимости."""
        # Используем индекс по user_id
        return db.query(User).filter(User.user_id == user_id).first()
    
    @staticmethod
    def update_user_last_seen_optimized(db: Session, user_id: int) -> bool:
        """Оптимизированное обновление времени последней активности."""
        result = db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(last_seen=datetime.now())
            .execution_options(synchronize_session=False)
        )
        db.commit()
        return result.rowcount > 0
    
    @staticmethod
    def bulk_update_users_last_seen(db: Session, user_ids: List[int]) -> int:
        """Массовое обновление времени последней активности для списка пользователей."""
        if not user_ids:
            return 0
            
        # Обновляем last_seen для всех пользователей в списке
        current_time = datetime.now()
        result = db.execute(
            update(User)
            .where(User.user_id.in_(user_ids))
            .values(last_seen=current_time)
            .execution_options(synchronize_session=False)
        )
        db.commit()
        return result.rowcount
    
    @staticmethod
    def get_active_users_count(db: Session, days: int = 7) -> int:
        """Получение количества активных пользователей за последние N дней."""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        count = db.query(func.count(User.id)).filter(
            User.last_seen >= cutoff_date
        ).scalar()
        
        return count or 0
    
    @staticmethod
    def get_users_for_broadcast(db: Session, limit: int = 1000) -> List[int]:
        """Получение ID пользователей для рассылки с оптимизированным запросом."""
        from config import get_settings
        settings = get_settings()
        
        admin_id = None
        if settings.ADMIN_CHAT_ID:
            try:
                admin_id = int(settings.ADMIN_CHAT_ID)
            except (TypeError, ValueError):
                pass
        
        query = db.query(User.user_id).filter(User.is_banned.is_(False))
        if admin_id is not None:
            query = query.filter(User.user_id != admin_id)
        
        # Используем индекс и ограничиваем количество результатов
        # ИСПРАВЛЕНО: извлекаем значения user_id из кортежей
        results = query.order_by(User.user_id).limit(limit).all()
        return [row[0] for row in results]  # Извлекаем user_id из кортежа
    
    @staticmethod
    def upsert_user(db: Session, user_data: Dict[str, Any]) -> User:
        """Оптимизированная операция upsert (обновление или создание) пользователя."""
        user_id = user_data['id']
        
        # Сначала пытаемся получить существующего пользователя
        existing_user = db.query(User).filter(User.user_id == user_id).first()
        
        if existing_user:
            # Обновляем существующего пользователя
            for field, value in user_data.items():
                if field in ['username', 'full_name'] and hasattr(existing_user, field):
                    setattr(existing_user, field, value)
            
            # Обновляем время последнего посещения
            existing_user.last_seen = datetime.now()
            db.commit()
            db.refresh(existing_user)
            return existing_user
        else:
            # Создаем нового пользователя
            new_user = User(
                user_id=user_id,
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