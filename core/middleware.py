# core/middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Awaitable, Any
import logging
import config
from core import database
logger = logging.getLogger("smartx_bot.middleware")

# Simple language middleware: loads user's language from DB and attaches to data
class LanguageMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Any, dict], Awaitable[Any]], event: Any, data: dict):
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        lang = config.LANG_DEFAULT
        try:
            if database.db:
                doc = await database.db.users.find_one({"user_id": user_id}, {"language": 1})
                if doc and doc.get("language"):
                    lang = doc["language"]
        except Exception as e:
            logger.debug("Failed to load user language: %s", e)

        data["lang"] = lang
        return await handler(event, data)

# Owner auth middleware for admin-only handlers (example usage via decorator)
class OwnerOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if hasattr(event, "from_user"):
            user_id = event.from_user.id
        if user_id != config.OWNER_ID:
            # raise or return silent
            return
        return await handler(event, data)
