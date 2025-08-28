# core/middleware.py
"""
Advanced Middlewares for SmartX Assistance Bot.

Provides:
- LanguageMiddleware: load user's language from DB and attach to handler data
- RateLimitMiddleware: per-user rate limiting with Redis fallback (in-memory)
- OwnerAuthMiddleware: restrict certain handlers to owner/admin
- ExceptionMiddleware: centralized exception catching/logging + user-friendly reply helpers

Usage:
- In bot.py call: setup_middlewares(dp) which will register these middlewares
- For aiogram v3: middlewares subclass BaseMiddleware and are used via dp.message.middleware(...) etc.
"""

from typing import Callable, Any, Optional, Dict
import logging
import time
import asyncio

from aiogram import BaseMiddleware, types
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.flags import get_flag

import config
from core import database

logger = logging.getLogger("smartx_bot.middleware")

# Try to import aioredis for distributed rate-limiting
try:
    import aioredis
    _has_redis = True
except Exception:
    _has_redis = False

# In-memory rate limiter fallback
_rate_store: Dict[int, Dict[str, Any]] = {}  # {user_id: {"count":int, "reset":timestamp}}


class LanguageMiddleware(BaseMiddleware):
    """
    Loads user's language from DB and attaches it to `data["lang"]`.
    Also loads locale strings into `data["lang_strings"]` for convenience.
    """

    async def __call__(self, handler: Callable, event: Any, data: dict):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            # unknown event type: continue with default language
            data["lang"] = getattr(config, "DEFAULT_LANGUAGE", "en")
            data["lang_strings"] = {}
            return await handler(event, data)

        lang = getattr(config, "DEFAULT_LANGUAGE", "en")
        try:
            if database:
                # best-effort: DB may not be connected yet
                user = await database.find_user(user_id)
                if user and user.get("language"):
                    lang = user.get("language")
        except Exception as e:
            logger.debug("LanguageMiddleware DB read failed: %s", e)

        data["lang"] = lang
        # load locale JSON into lang_strings (synchronous tiny read)
        try:
            import json, os
            base_dir = os.path.dirname(os.path.dirname(__file__))
            path = os.path.join(base_dir, "locales", f"{lang}.json")
            if not os.path.exists(path):
                path = os.path.join(base_dir, "locales", "en.json")
            with open(path, "r", encoding="utf-8") as f:
                data["lang_strings"] = json.load(f)
        except Exception as e:
            logger.debug("Failed loading locale file: %s", e)
            data["lang_strings"] = {}

        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """
    Rate limiter middleware.
    Uses Redis if available for persistence across workers; otherwise in-memory fallback.
    Configurable via config.ANTI_FLOOD_LIMIT and cache TTL.
    """

    def __init__(self, limit: int = None, window_seconds: int = 1):
        super().__init__()
        self.limit = limit or getattr(config, "ANTI_FLOOD_LIMIT", 3)
        self.window = window_seconds
        self.redis = None
        self._in_memory = _rate_store
        if _has_redis:
            # lazy connect
            self.redis = None

    async def _ensure_redis(self):
        if not _has_redis:
            return None
        if self.redis:
            return self.redis
        try:
            redis_url = getattr(config, "REDIS_URL", "redis://localhost:6379/0")
            self.redis = await aioredis.from_url(redis_url)
            return self.redis
        except Exception as e:
            logger.warning("Redis connect failed in RateLimitMiddleware: %s", e)
            self.redis = None
            return None

    async def __call__(self, handler: Callable, event: Any, data: dict):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        # Owner bypass
        if user_id == config.OWNER_ID:
            return await handler(event, data)

        # Check rate using Redis if available
        try:
            redis = await self._ensure_redis()
            if redis:
                key = f"rl:{user_id}"
                # using INCR with expiry as atomic
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, self.window)
                if count > self.limit:
                    # too many requests
                    # optionally, set ban time in redis
                    await self._on_limit_reached(event, data)
                    return
                else:
                    return await handler(event, data)
            else:
                # in-memory fallback
                now = time.time()
                rec = self._in_memory.get(user_id)
                if rec is None or rec.get("reset", 0) <= now:
                    # reset window
                    self._in_memory[user_id] = {"count": 1, "reset": now + self.window}
                    return await handler(event, data)
                else:
                    rec["count"] += 1
                    if rec["count"] > self.limit:
                        await self._on_limit_reached(event, data)
                        return
                    else:
                        return await handler(event, data)
        except Exception as e:
            logger.exception("RateLimitMiddleware error: %s", e)
            # if limiter fails, allow request (fail-open)
            return await handler(event, data)

    async def _on_limit_reached(self, event: Any, data: dict):
        # Send gentle warning to user. For CallbackQuery answer, use cb.answer
        try:
            if isinstance(event, CallbackQuery):
                await event.answer("You're doing too many actions — thoda slow karo please 😅", show_alert=False)
            elif isinstance(event, Message):
                await event.answer("You're sending too many requests right now. Please wait a moment.")
        except Exception:
            logger.debug("Failed to send rate limit message to user.")


class OwnerAuthMiddleware(BaseMiddleware):
    """
    Simple middleware ensuring only owner can hit certain handlers.
    Use by checking flags in handler or by explicit decorator that sets 'owner_only' flag.
    We'll look for flag 'owner_only' in handler flags (get_flag).
    """

    async def __call__(self, handler: Callable, event: Any, data: dict):
        # check flag on handler
        owner_only_flag = get_flag(handler, "owner_only", False)
        if not owner_only_flag:
            return await handler(event, data)

        user_id = None
        if hasattr(event, "from_user") and event.from_user:
            user_id = event.from_user.id

        if user_id != config.OWNER_ID:
            # unauthorized: reply or answer
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer("Unauthorized: Owner only command.", show_alert=True)
                elif isinstance(event, Message):
                    await event.reply("Unauthorized: Owner only command.")
            except Exception:
                pass
            return  # drop the event
        return await handler(event, data)


class ExceptionMiddleware(BaseMiddleware):
    """
    Catch unhandled exceptions in handlers, log them and send friendly message to user.
    Also optionally notify owner (config.OWNER_ID) about critical exceptions.
    """

    async def __call__(self, handler: Callable, event: Any, data: dict):
        try:
            return await handler(event, data)
        except Exception as e:
            # log full exception
            logger.exception("Unhandled exception in handler: %s", e)
            # notify owner (best-effort)
            try:
                from aiogram import Bot
                bot = data.get("bot")  # aiogram may inject bot in data, else create one
                if not bot:
                    bot = Bot(token=config.BOT_TOKEN)
                owner = getattr(config, "OWNER_ID", None)
                txt = f"⚠️ Exception in handler:\nUser: {getattr(event, 'from_user', None)}\nError: {repr(e)}"
                if owner:
                    # don't await if creating new bot (avoid blocking); schedule fire-and-forget
                    asyncio.create_task(bot.send_message(owner, txt))
            except Exception:
                logger.debug("Failed to notify owner about exception.")

            # Friendly message to user
            try:
                if isinstance(event, CallbackQuery):
                    await event.answer("Kuch gadbad ho gayi — try again later.", show_alert=False)
                elif isinstance(event, Message):
                    await event.reply("Sorry, something went wrong. Try again later.")
            except Exception:
                logger.debug("Failed sending error message to user after exception.")
            # swallow exception so it doesn't crash dispatcher
            return None


# ---- Utilities / Decorators to mark handlers ----

def owner_only(handler):
    """
    Decorator to mark a handler function as owner-only.
    Usage:
        @router.message(commands=['admin'])
        @owner_only
        async def cmd_admin(message: Message):
            ...
    """
    from functools import wraps

    if hasattr(handler, "__dict__"):
        handler.__dict__["owner_only"] = True

    @wraps(handler)
    async def wrapper(*args, **kwargs):
        return await handler(*args, **kwargs)

    return wrapper


# ---- Helper to register middlewares conveniently ----
def register_middlewares(dp):
    """
    Call this from bot startup to attach middlewares to dispatcher.
    Example:
        from core.middleware import register_middlewares
        register_middlewares(dp)
    """
    # order matters: ExceptionMiddleware should be outermost to catch everything
    try:
        dp.update.middleware(ExceptionMiddleware())
    except Exception:
        # fallback for other aiogram versions
        dp.message.middleware(ExceptionMiddleware())

    try:
        dp.message.middleware(LanguageMiddleware())
        dp.callback_query.middleware(LanguageMiddleware())
    except Exception:
        logger.debug("LanguageMiddleware registration fallback.")

    try:
        rl = RateLimitMiddleware(limit=getattr(config, "ANTI_FLOOD_LIMIT", 3), window_seconds=1)
        dp.message.middleware(rl)
        dp.callback_query.middleware(rl)
    except Exception:
        logger.debug("RateLimitMiddleware registration fallback.")

    try:
        dp.message.middleware(OwnerAuthMiddleware())
        dp.callback_query.middleware(OwnerAuthMiddleware())
    except Exception:
        logger.debug("OwnerAuthMiddleware registration fallback.")
