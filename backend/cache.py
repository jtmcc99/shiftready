"""
Simple in-memory TTL cache for async functions.

Usage:
    @cached(ttl=900)
    async def my_func(arg1, arg2):
        ...
"""

import time
import functools
from typing import Any, Dict

# Module-level store: key -> (value, expires_at)
_cache = {}  # type: Dict[str, tuple]


def cached(ttl: int = 900):
    """
    Async decorator that caches the return value of the decorated function
    for `ttl` seconds. The cache key is built from the function name plus
    a string representation of all positional and keyword arguments.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__module__}.{func.__qualname__}:{str(args)}:{str(sorted(kwargs.items()))}"
            now = time.monotonic()

            if key in _cache:
                value, expires_at = _cache[key]
                if now < expires_at:
                    return value
                # Expired — remove stale entry
                del _cache[key]

            result = await func(*args, **kwargs)
            _cache[key] = (result, now + ttl)
            return result

        def invalidate(*args, **kwargs):
            """Manually remove a cached entry."""
            key = f"{func.__module__}.{func.__qualname__}:{str(args)}:{str(sorted(kwargs.items()))}"
            _cache.pop(key, None)

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper

    return decorator


def clear_all():
    """Remove every entry from the in-memory cache."""
    _cache.clear()


def cache_stats() -> dict:
    """Return basic stats about the current cache state."""
    now = time.monotonic()
    live = sum(1 for _, (_, exp) in _cache.items() if now < exp)
    return {"total_keys": len(_cache), "live_keys": live, "expired_keys": len(_cache) - live}
