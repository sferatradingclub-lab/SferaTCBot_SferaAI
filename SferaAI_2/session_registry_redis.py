"""
Redis-based Session Registry for Sfera AI
Distributed session tracking for multiple agent instances
"""
import os
import logging
from typing import List, Optional
from datetime import datetime
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisSessionRegistry:
    """Redis-backed session registry for distributed agent instances"""
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.session_ttl = 3600  # 1 hour
        logger.info(f"RedisSessionRegistry initialized with URL: {redis_url}")
    
    async def register(self, user_id: str, session_data: dict = None) -> None:
        """
        Register an active session for a user
        
        Args:
            user_id: User identifier
            session_data: Optional metadata about the session
        """
        key = f"session:{user_id}"
        
        # Store minimal session metadata
        data = {
            "user_id": user_id,
            "active": "true",
            "registered_at": datetime.now().isoformat()
        }
        
        if session_data:
            data.update(session_data)
        
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, self.session_ttl)
        logger.info(f"Session registered for user: {user_id}")
    
    async def unregister(self, user_id: str) -> None:
        """
        Remove a session from registry
        
        Args:
            user_id: User identifier
        """
        key = f"session:{user_id}"
        await self.redis.delete(key)
        logger.info(f"Session unregistered for user: {user_id}")
    
    async def is_active(self, user_id: str) -> bool:
        """
        Check if user has an active session
        
        Args:
            user_id: User identifier
            
        Returns:
            True if session exists and is active
        """
        key = f"session:{user_id}"
        exists = await self.redis.exists(key)
        return exists > 0
    
    async def get_session(self, user_id: str) -> Optional[dict]:
        """
        Get session data for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Session data dict or None if not found
        """
        key = f"session:{user_id}"
        session_data = await self.redis.hgetall(key)
        return session_data if session_data else None
    
    async def get_active_users(self) -> List[str]:
        """
        Get list of all users with active sessions
        
        Returns:
            List of user IDs
        """
        keys = await self.redis.keys("session:*")
        user_ids = [key.replace("session:", "") for key in keys]
        return user_ids
    
    async def clear(self) -> None:
        """Clear all sessions (for cleanup/testing)"""
        keys = await self.redis.keys("session:*")
        if keys:
            await self.redis.delete(*keys)
        logger.info("All sessions cleared from registry")
    
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy
        
        Returns:
            True if Redis is accessible
        """
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Singleton instance
_redis_registry_instance = None


def get_session_registry() -> RedisSessionRegistry:
    """
    Get singleton instance of RedisSessionRegistry
    
    Returns:
        RedisSessionRegistry instance
    """
    global _redis_registry_instance
    if _redis_registry_instance is None:
        _redis_registry_instance = RedisSessionRegistry()
    return _redis_registry_instance


# For backward compatibility - maintain same interface as old session_registry
class SessionRegistryCompat:
    """Compatibility wrapper for synchronous code"""
    
    def __init__(self):
        self._registry = get_session_registry()
    
    def is_active(self, user_id: str) -> bool:
        """Synchronous wrapper - DO NOT USE in async code"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._registry.is_active(user_id))
        except RuntimeError:
            logger.warning("Called sync is_active outside event loop, returning False")
            return False


# For code that still uses old synchronous interface
session_registry = SessionRegistryCompat()
