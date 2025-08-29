# core/cache.py
"""
Redis-backed cache abstraction (async).

Provides:
- get/set/del
- incr/ttl
- distributed lock (simple lock with SET NX)
- rate-limit helper (sliding/ fixed-window via INCR + EXPIRE)

This is used by middleware for rate-limiting and can be used anywhere else.
"""

import os
import asyncio
import logging
from typing import Optional
import aioredis

logger = logging.getLogger("core.cache")

REDIS_URL = getattr(__import__("config"), "REDIS_URL", None) or os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis = None

def get_redis_sync():
    """Synchronous accessor for non-async code (creates connection if not exists)."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis

async def get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis

# Basic operations
async def cache_get(key: str) -> Optional[str]:
    r = await get_redis()
    try:
        return await r.get(key)
    except Exception:
        logger.exception("cache_get error")
        return None

async def cache_set(key: str, value: str, ex: Optional[int] = None) -> bool:
    r = await get_redis()
    try:
        if ex:
            await r.set(key, value, ex=ex)
        else:
            await r.set(key, value)
        return True
    except Exception:
        logger.exception("cache_set error")
        return False

async def cache_delete(key: str) -> bool:
    r = await get_redis()
    try:
        await r.delete(key)
        return True
    except Exception:
        logger.exception("cache_delete error")
        return False

async def cache_incr(key: str, ex: Optional[int] = None) -> int:
    r = await get_redis()
    try:
        val = await r.incr(key)
        if ex:
            await r.expire(key, ex)
        return int(val)
    except Exception:
        logger.exception("cache_incr error")
        return 0

async def cache_ttl(key: str) -> int:
    r = await get_redis()
    try:
        return int(await r.ttl(key))
    except Exception:
        logger.exception("cache_ttl error")
        return -1

# Simple lock (non reentrant)
class RedisLock:
    """
    Simple distributed lock using SET NX with expiry.
    Usage:
        lock = RedisLock("mykey", ttl=10)
        async with lock:
            ...
    """
    def __init__(self, name: str, ttl: int = 10):
        self._name = f"lock:{name}"
        self._ttl = ttl
        self._token = None
        self._redis = None

    async def __aenter__(self):
        self._redis = await get_redis()
        # generate token
        self._token = os.urandom(16).hex()
        got = await self._redis.set(self._name, self._token, nx=True, ex=self._ttl)
        backoff = 0.1
        waited = 0.0
        while not got:
            await asyncio.sleep(backoff)
            waited += backoff
            backoff = min(1.0, backoff * 2)
            got = await self._redis.set(self._name, self._token, nx=True, ex=self._ttl)
            if waited > 5.0:
                raise TimeoutError("RedisLock acquire timeout")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        try:
            # release only if token matches (safe delete)
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await self._redis.eval(script, keys=[self._name], args=[self._token])
        except Exception:
            logger.exception("RedisLock release failed")
