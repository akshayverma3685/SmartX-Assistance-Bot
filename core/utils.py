"""
core/utils.py

Utility functions for SmartX Assistance bot.
Reusable helpers for formatting, conversions, retries, etc.
"""

import asyncio
import datetime
import functools
import json
import logging
import random
import string
import traceback
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger("core.utils")

# ---------------------------
# Datetime Helpers
# ---------------------------

def utc_now() -> datetime.datetime:
    """Return current UTC time"""
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

def format_datetime(dt: datetime.datetime, fmt: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """Format datetime to string"""
    return dt.strftime(fmt)

def human_time_delta(seconds: int) -> str:
    """Convert seconds to human readable format (e.g., 2d 3h 4m)"""
    periods = [
        ('d', 60 * 60 * 24),
        ('h', 60 * 60),
        ('m', 60),
        ('s', 1)
    ]
    parts = []
    for suffix, length in periods:
        value, seconds = divmod(seconds, length)
        if value:
            parts.append(f"{value}{suffix}")
    return " ".join(parts) if parts else "0s"

# ---------------------------
# Formatting Helpers
# ---------------------------

def format_currency(amount: float, currency: str = "INR") -> str:
    """Format number as currency"""
    return f"{currency} {amount:,.2f}"

def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human readable size"""
    if size_bytes == 0:
        return "0B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {units[i]}"

def mask_user_id(user_id: int) -> str:
    """Mask Telegram user ID for privacy"""
    uid = str(user_id)
    return uid[:2] + "*" * (len(uid) - 4) + uid[-2:]

# ---------------------------
# Retry Decorator
# ---------------------------

def retry(times: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Retry decorator for functions.
    Example:
        @retry(times=3, delay=2)
        async def my_func(): ...
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                for attempt in range(times):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        logger.warning(f"[Retry] {func.__name__} failed ({attempt+1}/{times}): {e}")
                        if attempt < times - 1:
                            await asyncio.sleep(delay)
                        else:
                            raise
            return wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(times):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        logger.warning(f"[Retry] {func.__name__} failed ({attempt+1}/{times}): {e}")
                        if attempt < times - 1:
                            import time; time.sleep(delay)
                        else:
                            raise
            return wrapper
    return decorator

# ---------------------------
# Async Helpers
# ---------------------------

async def run_parallel(tasks: list[Coroutine]) -> list[Any]:
    """Run multiple async tasks in parallel"""
    return await asyncio.gather(*tasks, return_exceptions=True)

async def safe_await(coro: Coroutine, default: Any = None) -> Any:
    """Safely await a coroutine and catch errors"""
    try:
        return await coro
    except Exception as e:
        logger.error(f"[safe_await] Error: {e}\n{traceback.format_exc()}")
        return default

# ---------------------------
# Random Generators
# ---------------------------

def random_token(length: int = 16) -> str:
    """Generate random alphanumeric token"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def random_numeric_code(length: int = 6) -> str:
    """Generate random numeric code (OTP)"""
    return ''.join(random.choice(string.digits) for _ in range(length))

# ---------------------------
# JSON Helpers
# ---------------------------

def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """Safe JSON stringify"""
    try:
        return json.dumps(obj, indent=indent, default=str, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[safe_json_dumps] Failed: {e}")
        return "{}"

def safe_json_loads(data: str, default: Any = None) -> Any:
    """Safe JSON parse"""
    try:
        return json.loads(data)
    except Exception as e:
        logger.error(f"[safe_json_loads] Failed: {e}")
        return default
