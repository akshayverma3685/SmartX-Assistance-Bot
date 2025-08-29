# services/error_service.py
"""
Centralized error handling helper used by handlers and services.

- Logs errors to logs/errors.log (core.logs.log_error)
- Persists detailed error doc in Mongo via admin_panel.error_monitor.ErrorMonitor
- Optionally notifies owner via Telegram (ErrorMonitor handles messaging)
"""

import logging
import traceback
from typing import Optional, Any, Dict

from core import logs as core_logs
from core import database
from admin_panel.error_monitor import error_monitor  # previously provided module
import config

logger = logging.getLogger("services.error_service")


async def capture_exception(source: str, exc: Exception, user_id: Optional[int] = None, extra: Optional[Dict[str, Any]] = None):
    """
    Use this in except blocks across the codebase.
    Example:
        try:
            ...
        except Exception as e:
            await capture_exception("handlers.start", e, user_id=msg.from_user.id)
    """
    # log to errors.log (file + mongo via core.logs)
    core_logs.log_error(str(exc), user_id=user_id, source=source, meta=extra, exc_info=True)

    # store detailed error in dedicated collection and notify admin
    try:
        # error_monitor.log_error will write to DB and notify owner if configured
        await error_monitor.log_error(source, exc, user_id=user_id)
    except Exception:
        # ensure the capture itself never raises
        logger.exception("error_monitor.log_error failed (best-effort)")

    # optionally return a friendly error message for the user
    return "An internal error occurred — the admins have been notified."


# Helper decorator for async functions (handlers/services)
def with_error_capture(source: str):
    """
    Decorator to wrap handler functions and automatically capture exceptions.
    Works for async functions.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # attempt to extract user_id if available in args/kwargs
                user_id = None
                for a in args:
                    try:
                        if hasattr(a, "from_user") and a.from_user:
                            user_id = getattr(a.from_user, "id", None)
                            break
                    except Exception:
                        continue
                await capture_exception(source, e, user_id=user_id)
                # suppress exception after logging to prevent crash of dispatcher
                return None
        return wrapper
    return decorator
