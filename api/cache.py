# api/cache.py
"""
Caching configuration and utilities using Redis with fastapi-cache2
Falls back to in-memory cache if Redis is unavailable
"""

import os
import logging
from typing import Optional
from fastapi import Request, Response
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

# Redis connection instance
redis_client: Optional[aioredis.Redis] = None


async def init_cache():
    """
    Initialize caching backend (Redis or fallback to in-memory)
    Call this during FastAPI startup event
    """
    global redis_client

    # Get Redis URL from environment (optional)
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        # Attempt to connect to Redis
        redis_client = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5  # 5 second timeout
        )

        # Test connection
        await redis_client.ping()

        # Initialize FastAPICache with Redis backend
        FastAPICache.init(RedisBackend(redis_client), prefix="aianalyst:")

        logger.info(f"✅ Redis cache initialized successfully (URL: {redis_url})")

    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}")
        logger.info("📦 Falling back to in-memory cache")

        # Fallback to in-memory cache
        FastAPICache.init(InMemoryBackend(), prefix="aianalyst:")
        redis_client = None


async def close_cache():
    """
    Close Redis connection gracefully
    Call this during FastAPI shutdown event
    """
    global redis_client

    if redis_client:
        try:
            await redis_client.close()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Redis: {e}")


def cache_key_builder(
    func,
    namespace: str = "",
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
):
    """
    Custom cache key builder for fastapi-cache2
    Builds hierarchical cache keys with request parameters

    Example key: "aianalyst:admin:users:page=1:limit=10:status=all"
    """
    from fastapi_cache import FastAPICache

    prefix = FastAPICache.get_prefix()
    cache_key = f"{prefix}{namespace}:{func.__module__}:{func.__name__}"

    # Add query parameters to cache key
    if request and request.query_params:
        query_string = ":".join(
            f"{k}={v}" for k, v in sorted(request.query_params.items())
        )
        cache_key = f"{cache_key}:{query_string}"

    return cache_key


async def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache keys matching a pattern

    Args:
        pattern: Redis pattern (e.g., "aianalyst:admin:users:*")

    Example:
        await invalidate_cache_pattern("aianalyst:admin:users:*")
    """
    global redis_client

    if not redis_client:
        logger.warning("⚠️  Cannot invalidate cache pattern: Redis not available")
        return

    try:
        # Find all keys matching pattern
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)

        # Delete all matching keys
        if keys:
            await redis_client.delete(*keys)
            logger.info(f"✅ Invalidated {len(keys)} cache keys matching '{pattern}'")
        else:
            logger.debug(f"No cache keys found matching '{pattern}'")

    except Exception as e:
        logger.error(f"❌ Error invalidating cache pattern '{pattern}': {e}")


async def invalidate_user_cache(user_id: int):
    """
    Invalidate all caches for a specific user

    Args:
        user_id: User ID to invalidate caches for

    Example:
        await invalidate_user_cache(123)
    """
    pattern = f"aianalyst:*user*{user_id}*"
    await invalidate_cache_pattern(pattern)


async def clear_all_caches():
    """
    Clear all application caches
    Use with caution - only for admin operations
    """
    global redis_client

    if not redis_client:
        logger.warning("⚠️  Cannot clear caches: Redis not available")
        return

    try:
        # Delete all keys with our prefix
        pattern = "aianalyst:*"
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await redis_client.delete(*keys)
            logger.info(f"✅ Cleared all caches ({len(keys)} keys)")
        else:
            logger.info("No caches to clear")

    except Exception as e:
        logger.error(f"❌ Error clearing all caches: {e}")


# Export cache decorator for easy use
__all__ = [
    "cache",
    "init_cache",
    "close_cache",
    "cache_key_builder",
    "invalidate_cache_pattern",
    "invalidate_user_cache",
    "clear_all_caches",
]
