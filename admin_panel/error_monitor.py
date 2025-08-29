#!/usr/bin/env python3
"""
admin_panel/error_monitor.py

SmartX Assistance - Error Monitoring & Alert System

- Captures all runtime errors from bot
- Stores them in MongoDB for later analysis
- Notifies owner/admin instantly on critical errors
- Extendable for Email/Slack integrations
"""

import logging
import traceback
import datetime
import asyncio
from typing import Dict, Any, Optional

from aiogram import Bot
import config
from core import database

logger = logging.getLogger("admin_panel.error_monitor")

# MongoDB collection for errors
ERROR_COLLECTION = "error_logs"


class ErrorMonitor:
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
        self.admin_id = int(config.OWNER_ID) if hasattr(config, "OWNER_ID") else None

    async def log_error(self, source: str, err: Exception, user_id: Optional[int] = None):
        """Save error into MongoDB and notify admin if critical"""
        db = database.get_mongo_db()
        ts = datetime.datetime.utcnow()

        error_doc = {
            "timestamp": ts,
            "source": source,
            "user_id": user_id,
            "error_type": type(err).__name__,
            "error_message": str(err),
            "traceback": traceback.format_exc(),
        }

        # save to DB
        await db[ERROR_COLLECTION].insert_one(error_doc)
        logger.error(f"[ErrorMonitor] {source} | {err}")

        # Notify admin if bot available
        if self.bot and self.admin_id:
            try:
                await self.bot.send_message(
                    chat_id=self.admin_id,
                    text=(
                        f"⚠️ *Critical Error Alert!*\n"
                        f"Source: `{source}`\n"
                        f"User: `{user_id or 'N/A'}`\n"
                        f"Type: `{type(err).__name__}`\n"
                        f"Message: `{str(err)}`\n"
                        f"Time: {ts.isoformat()} UTC"
                    ),
                    parse_mode="Markdown"
                )
            except Exception as notify_err:
                logger.warning(f"Failed to notify admin: {notify_err}")

    async def get_recent_errors(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Fetch recent errors for admin panel"""
        db = database.get_mongo_db()
        cursor = db[ERROR_COLLECTION].find().sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def clear_errors(self):
        """Clear all stored errors"""
        db = database.get_mongo_db()
        await db[ERROR_COLLECTION].delete_many({})
        logger.info("All error logs cleared.")


# Global error monitor instance
error_monitor = ErrorMonitor()


# Example middleware/handler usage
async def handle_exception(source: str, err: Exception, user_id: Optional[int] = None):
    """Helper to log error from anywhere in the bot"""
    await error_monitor.log_error(source, err, user_id)


# ========== For CLI Testing ==========
if __name__ == "__main__":
    import asyncio

    async def test():
        await database.connect()
        try:
            try:
                1 / 0  # generate error
            except Exception as e:
                await error_monitor.log_error("manual_test", e, user_id=12345)

            errors = await error_monitor.get_recent_errors()
            print("Recent Errors:")
            for e in errors:
                print(f"- {e['timestamp']}: {e['error_type']} -> {e['error_message']}")
        finally:
            await database.disconnect()

    asyncio.run(test())
