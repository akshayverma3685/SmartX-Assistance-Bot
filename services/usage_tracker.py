# services/usage_tracker.py
"""
Usage tracker service.

- Logs usage events (downloads, ai requests, commands) to logs/usage.log
- Updates aggregated counters in Redis (via core.cache)
- Stores lightweight event doc in db.usage for analytics
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging
import asyncio

from core import logs as core_logs
from core import cache, database, utils
from admin_panel.error_monitor import error_monitor

logger = logging.getLogger("services.usage_tracker")

async def track_event(user_id: Optional[int], event_type: str, meta: Optional[Dict[str, Any]] = None):
    """
    Record an usage event.
    - event_type: e.g. "download", "ai_request", "command"
    - meta: arbitrary dict with details (size, model, command_name)
    """
    ts = datetime.utcnow().replace(tzinfo=timezone.utc)
    # log to usage.log
    core_logs.log_usage(f"Event: {event_type}", user_id=user_id, source="usage_tracker.track_event", meta={"event_type": event_type, "meta": meta, "ts": ts.isoformat()})

    # increment Redis counters (daily counters)
    try:
        today = ts.date().isoformat()
        # global counter for event_type
        await cache.cache_incr(f"usage:{event_type}:total", ex=60*60*24*7)  # keep weekly
        # daily per-event counter
        await cache.cache_incr(f"usage:{event_type}:{today}", ex=60*60*24*30)
        # per-user counter (optional)
        if user_id:
            await cache.cache_incr(f"usage:user:{user_id}:{event_type}", ex=60*60*24*30)
    except Exception:
        logger.exception("Redis counter update failed (best-effort)")

    # store light doc in DB for analytics
    try:
        db = database.get_mongo_db()
        doc = {
            "user_id": int(user_id) if user_id else None,
            "event_type": event_type,
            "meta": meta or {},
            "timestamp": ts,
        }
        # insert asynchronously (db available)
        await db.usage.insert_one(doc)
    except Exception as e:
        logger.exception("Failed to persist usage event to DB")
        try:
            # notify admin about persistent DB failure
            await error_monitor.log_error("usage_tracker_db", e, user_id=user_id)
        except Exception:
            logger.debug("error_monitor call failed while logging usage DB error")
