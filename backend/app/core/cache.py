"""
Simple in-memory cache for API responses
"""
import time
from typing import Any, Optional, Callable
from functools import wraps
import hashlib
import json

# Simple in-memory cache
_cache: dict = {}


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def get_cached(key: str, ttl: int = 60) -> Optional[Any]:
    """Get value from cache if not expired"""
    if key in _cache:
        data, expires = _cache[key]
        if time.time() < expires:
            return data
        else:
            # Clean up expired entry
            del _cache[key]
    return None


def set_cached(key: str, value: Any, ttl: int = 60):
    """Set value in cache with TTL"""
    _cache[key] = (value, time.time() + ttl)


def clear_cache(prefix: str = None):
    """Clear cache entries, optionally by prefix"""
    global _cache
    if prefix:
        keys_to_delete = [k for k in _cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del _cache[key]
    else:
        _cache = {}


def cached(ttl: int = 60, prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = f"{prefix}:{func.__name__}:{cache_key(*args[1:], **kwargs)}"  # Skip 'self' or 'db'
            
            # Try cache first
            cached_value = get_cached(key, ttl)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            set_cached(key, result, ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = f"{prefix}:{func.__name__}:{cache_key(*args[1:], **kwargs)}"
            
            cached_value = get_cached(key, ttl)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            set_cached(key, result, ttl)
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Cache statistics
def get_cache_stats() -> dict:
    """Get cache statistics"""
    now = time.time()
    total = len(_cache)
    expired = sum(1 for _, (_, exp) in _cache.items() if exp < now)
    return {
        "total_entries": total,
        "expired_entries": expired,
        "active_entries": total - expired
    }
