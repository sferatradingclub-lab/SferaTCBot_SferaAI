from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Сервис для ограничения частоты запросов пользователей."""
    
    def __init__(self):
        self.user_requests: Dict[int, Deque] = defaultdict(lambda: deque(maxlen=10))
        self.blocked_users: Dict[int, datetime] = {}
        self.max_requests_per_minute = 10
        self.block_duration_minutes = 5
    
    def is_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли запрос для пользователя."""
        now = datetime.now()
        
        # Проверяем блокировку пользователя
        if user_id in self.blocked_users:
            if now < self.blocked_users[user_id]:
                logger.warning(f"Пользователь {user_id} заблокирован до {self.blocked_users[user_id]}")
                return False
            else:
                # Снимаем блокировку
                del self.blocked_users[user_id]
                logger.info(f"Блокировка снята для пользователя {user_id}")
        
        # Добавляем текущий запрос
        self.user_requests[user_id].append(now)
        
        # Подсчитываем запросы за последнюю минуту
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [req for req in self.user_requests[user_id] if req > minute_ago]
        
        if len(recent_requests) > self.max_requests_per_minute:
            # Блокируем пользователя
            self.blocked_users[user_id] = now + timedelta(minutes=self.block_duration_minutes)
            logger.warning(
                f"Пользователь {user_id} превысил лимит запросов. Заблокирован на {self.block_duration_minutes} минут"
            )
            return False
            
        return True
    
    def reset_user(self, user_id: int):
        """Сбрасывает лимиты для пользователя (например, при блокировке админом)."""
        self.user_requests.pop(user_id, None)
        self.blocked_users.pop(user_id, None)
        logger.info(f"Лимиты сброшены для пользователя {user_id}")
    
    def get_user_status(self, user_id: int) -> Dict:
        """Возвращает статус пользователя для мониторинга."""
        now = datetime.now()
        blocked_until = self.blocked_users.get(user_id)
        
        if blocked_until:
            remaining_time = int((blocked_until - now).total_seconds())
            return {
                "is_blocked": True,
                "blocked_until": blocked_until.isoformat(),
                "remaining_seconds": max(0, remaining_time)
            }
        
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [req for req in self.user_requests[user_id] if req > minute_ago]
        
        return {
            "is_blocked": False,
            "requests_in_last_minute": len(recent_requests),
            "remaining_requests": max(0, self.max_requests_per_minute - len(recent_requests))
        }