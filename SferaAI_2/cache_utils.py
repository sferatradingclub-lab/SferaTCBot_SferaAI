"""
Simple TTL (Time-To-Live) cache for API responses.
Reduces redundant API calls and improves response time.
"""

import time
import hashlib
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class TTLCache:
    """Time-based cache with automatic expiration"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 100):
        """
        Initialize TTL cache.
        
        Args:
            ttl_seconds: Time to live for cached entries (default: 5 minutes)
            max_size: Maximum number of entries (oldest removed when exceeded)
        """
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                logger.debug(f"Cache HIT for key: {key[:20]}... (hit rate: {self.get_hit_rate():.1%})")
                return value
            else:
                # Expired, remove it
                del self.cache[key]
        
        self.misses += 1
        logger.debug(f"Cache MISS for key: {key[:20]}...")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Store value in cache with current timestamp"""
        # Remove oldest entry if at max capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
            logger.debug(f"Cache full, removed oldest entry: {oldest_key[:20]}...")
        
        self.cache[key] = (value, time.time())
        logger.debug(f"Cache SET for key: {key[:20]}... (size: {len(self.cache)}/{self.max_size})")
    
    def clear(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.get_hit_rate(),
            "ttl_seconds": self.ttl,
        }


def make_cache_key(*args, **kwargs) -> str:
    """Generate consistent cache key from arguments"""
    # Combine all args and kwargs into a single string
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = "|".join(key_parts)
    
    # Hash for consistent length
    return hashlib.md5(key_string.encode()).hexdigest()
