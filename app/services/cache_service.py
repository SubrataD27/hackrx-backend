import json
import hashlib
from typing import Optional, Any, Dict
import structlog
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

class CacheService:
    """In-memory cache service with LRU eviction"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = 1000
        self.access_order = []
    
    async def initialize(self):
        """Initialize cache service"""
        logger.info("Initializing cache service")
        self.cache.clear()
        self.access_order.clear()
    
    async def health_check(self) -> bool:
        """Health check for cache service"""
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            if key in self.cache:
                # Update access order (LRU)
                self.access_order.remove(key)
                self.access_order.append(key)
                
                entry = self.cache[key]
                # Check TTL
                import time
                if entry['expires_at'] > time.time():
                    return entry['value']
                else:
                    # Expired, remove
                    del self.cache[key]
                    self.access_order.remove(key)
            
            return None
            
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache with TTL"""
        try:
            import time
            
            # Evict if cache is full
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = self.access_order.pop(0)
                del self.cache[oldest_key]
            
            # Set new value
            self.cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl
            }
            
            # Update access order
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)
            
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
    
    async def delete(self, key: str):
        """Delete key from cache"""
        try:
            if key in self.cache:
                del self.cache[key]
                self.access_order.remove(key)
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
    
    async def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.access_order.clear()
    
    async def close(self):
        """Close cache service"""
        logger.info("Closing cache service")
        await self.clear()
    
    def _generate_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_string = "|".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()