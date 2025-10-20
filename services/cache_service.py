import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from config import get_settings
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Сервис кеширования для оптимизации производительности."""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_ttl_minutes = int(self.settings._read_optional("CACHE_TTL_MINUTES") or "60")
        self.max_cache_size = int(self.settings._read_optional("MAX_CACHE_SIZE") or "1000")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, datetime] = {}
        
    def _generate_key(self, *args, **kwargs) -> str:
        """Генерирует уникальный ключ для кеша на основе аргументов."""
        # Создаем строку из аргументов
        cache_input = f"{args}_{sorted(kwargs.items())}"
        # Хешируем для получения уникального ключа
        return hashlib.sha256(cache_input.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Удаляет просроченные записи из кеша."""
        now = datetime.now()
        expired_keys = [
            key for key, access_time in self._access_times.items()
            if now - access_time > timedelta(minutes=self.cache_ttl_minutes)
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def _evict_lru(self):
        """Удаляет наименее используемые записи при достижении лимита."""
        if len(self._cache) <= self.max_cache_size:
            return
            
        # Сортируем по времени доступа (наименее недавние первыми)
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
        keys_to_remove = len(self._cache) - self.max_cache_size + 1
        
        for key, _ in sorted_keys[:keys_to_remove]:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Получает значение из кеша по ключу."""
        self._cleanup_expired()
        
        if key in self._cache:
            self._access_times[key] = datetime.now()
            return self._cache[key]["value"]
        
        return None
    
    def set(self, key: str, value: Any, ttl_minutes: Optional[int] = None):
        """Сохраняет значение в кеш с указанным временем жизни."""
        self._cleanup_expired()
        self._evict_lru()
        
        ttl = ttl_minutes or self.cache_ttl_minutes
        self._cache[key] = {
            "value": value,
            "ttl": ttl
        }
        self._access_times[key] = datetime.now()
    
    def delete(self, key: str):
        """Удаляет значение из кеша."""
        self._cache.pop(key, None)
        self._access_times.pop(key, None)
    
    def clear(self):
        """Очищает весь кеш."""
        self._cache.clear()
        self._access_times.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кеша."""
        self._cleanup_expired()
        return {
            "size": len(self._cache),
            "max_size": self.max_cache_size,
            "ttl_minutes": self.cache_ttl_minutes,
            "keys": list(self._cache.keys())
        }


# Инициализация глобального экземпляра кеша
cache_service = CacheService()


# Сервис кеширования для ChatGPT
class ChatGPTCache:
    """Специализированный кеш для ответов ChatGPT."""
    
    @staticmethod
    def _generate_chatgpt_key(messages: list, model: str) -> str:
        """Генерирует уникальный ключ для кеша на основе сообщений и модели."""
        # Создаем хеш от последних N сообщений для уникальности
        messages_str = json.dumps([msg for msg in messages[-5:]], sort_keys=True, default=str)  # последние 5 сообщений
        key_input = f"{messages_str}_{model}"
        return hashlib.sha256(key_input.encode()).hexdigest()
    
    @classmethod
    def get_cached_response(cls, messages: list, model: str) -> Optional[str]:
        """Получает закешированный ответ ChatGPT."""
        key = cls._generate_chatgpt_key(messages, model)
        cached_response = cache_service.get(key)
        
        if cached_response:
            logger.info(f"Найден закешированный ответ для модели {model}")
            return cached_response
        
        return None
    
    @classmethod
    def cache_response(cls, messages: list, model: str, response: str, ttl_minutes: int = 60):
        """Кеширует ответ ChatGPT."""
        key = cls._generate_chatgpt_key(messages, model)
        cache_service.set(key, response, ttl_minutes)
        logger.info(f"Ответ закеширован для модели {model}, ключ: {key[:8]}...")
    
    @classmethod
    def invalidate_conversation_cache(cls, messages: list, model: str):
        """Инвалидирует кеш для конкретного разговора."""
        key = cls._generate_chatgpt_key(messages, model)
        cache_service.delete(key)
        logger.info(f"Кеш инвалидирован для модели {model}, ключ: {key[:8]}...")