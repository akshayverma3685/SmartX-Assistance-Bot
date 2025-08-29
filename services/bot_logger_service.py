# services/bot_logger_service.py
"""
Bot events logger service.

Usage: import and call functions from handlers when key events happen:
 - on_start, on_new_user, on_command, on_error (delegates)
This module writes to logs/bot.log via core.logs.log_info and optionally to DB audit collections.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from core import logs as core_logs
from core import database, utils
import logging

logger = logging.getLogger("services.bot_logger")

async def record_startup():
    """Called when bot starts up"""
    core_logs.log_info("Bot startup", source="system.startup", meta={"ts": utils.utc_now().isoformat()})

async def record_new_user(user_id: int, username: Optional[str] = None, lang: Optional[str] = None):
    """When a user hits /start for first time"""
    meta = {"username": username, "language": lang, "joined_at": utils.utc_now().isoformat()}
    core_logs.log_info("New user joined", user_id=user_id, source="handlers.start", meta=meta)
    # Optionally store in DB's users collection if not present
    try:
        db = database.get_mongo_db()
        existing = await db.users.find_one({"user_id": int(user_id)})
        if not existing:
            doc = {
                "user_id": int(user_id),
                "username": username,
                "language": lang or "en",
                "plan": "free",
                "joined_date": datetime.utcnow().replace(tzinfo=timezone.utc),
                "is_active": True,
            }
            await db.users.insert_one(doc)
            core_logs.log_info("User created in DB", user_id=user_id, source="services.bot_logger")
    except Exception:
        logger.exception("Error while creating user in DB (best-effort)")

async def record_command(user_id: int, command: str, args: Optional[str] = None):
    """Log command usage"""
    meta = {"command": command, "args": args}
    core_logs.log_info("Command executed", user_id=user_id, source="handlers.command", meta=meta)

# Optional helper to add contextual logging in handlers
def handler_context(handler_name: str):
    """
    Use as:
        ctx = handler_context('start_handler')
        core_logs.log_info("x", user_id=..., source=ctx['source'])
    """
    return {"source": f"handlers.{handler_name}"}
