"""
logs/log_config.py

Production-ready logging setup for SmartX Assistance.

Creates four dedicated loggers (rotating file handlers):
 - bot_logger      -> logs/bot.log        (INFO+)
 - error_logger    -> logs/errors.log     (ERROR+)
 - payment_logger  -> logs/payments.log   (INFO+)
 - usage_logger    -> logs/usage.log      (INFO+)

Features:
 - RotatingFileHandler (maxBytes, backupCount)
 - JSON-like structured formatter (one-line JSON per event)
 - Optional console handler (controlled by LOG_STDOUT env)
 - Safe UTF-8 output
 - Simple functions to get loggers
"""

import logging
import os
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Optional

# Configuration (can be overriden via environment variables)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR)  # logs/ directory (this file is inside logs/)
os.makedirs(LOG_DIR, exist_ok=True)

MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", 5 * 1024 * 1024))   # 5 MB
BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 7))            # keep 7 backups
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
ENABLE_STDOUT = os.getenv("LOG_STDOUT", "false").lower() in ("1", "true", "yes")

# Helper: structured formatter (JSON-ish single line)
class JSONLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # include common extras if present
        for key in ("user_id", "source", "meta"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        # include exception text if present
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        try:
            return json.dumps(payload, default=str, ensure_ascii=False)
        except Exception:
            # fallback to simple str
            return f'{payload["ts"]} | {payload["level"]} | {payload["logger"]} : {record.getMessage()}'

def _make_rotating_handler(filename: str) -> RotatingFileHandler:
    path = os.path.join(LOG_DIR, filename)
    handler = RotatingFileHandler(path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8")
    handler.setFormatter(JSONLineFormatter())
    return handler

def _attach_console_handler(logger_obj: logging.Logger):
    ch = logging.StreamHandler()
    ch.setFormatter(JSONLineFormatter())
    logger_obj.addHandler(ch)

def _create_logger(name: str, filename: str, level: Optional[str] = None) -> logging.Logger:
    lvl = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
    logger_obj = logging.getLogger(name)
    # Avoid duplicate handlers on repeated imports
    if any(isinstance(h, RotatingFileHandler) and os.path.abspath(getattr(h, "baseFilename", "")) == os.path.abspath(os.path.join(LOG_DIR, filename)) for h in logger_obj.handlers):
        logger_obj.setLevel(lvl)
        return logger_obj

    logger_obj.setLevel(lvl)
    logger_obj.propagate = False
    fh = _make_rotating_handler(filename)
    logger_obj.addHandler(fh)
    if ENABLE_STDOUT:
        _attach_console_handler(logger_obj)
    return logger_obj

# Instantiate the four loggers
bot_logger     = _create_logger("smartx.bot", "bot.log", level="INFO")
error_logger   = _create_logger("smartx.error", "errors.log", level="ERROR")
payment_logger = _create_logger("smartx.payment", "payments.log", level="INFO")
usage_logger   = _create_logger("smartx.usage", "usage.log", level="INFO")

# Convenience wrappers (fast import)
def log_bot(msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
    bot_logger.info(msg, extra={"user_id": user_id, "source": source, "meta": meta})

def log_error(msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None, exc_info: bool = False):
    # exc_info=True will include stacktrace automatically
    error_logger.error(msg, extra={"user_id": user_id, "source": source, "meta": meta}, exc_info=exc_info)

def log_payment(msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
    payment_logger.info(msg, extra={"user_id": user_id, "source": source, "meta": meta})

def log_usage(msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
    usage_logger.info(msg, extra={"user_id": user_id, "source": source, "meta": meta})

# Optional: helper to read last N lines (admin use)
def read_last_lines(file_name: str, n: int = 200):
    path = os.path.join(LOG_DIR, file_name)
    if not os.path.exists(path):
        return []
    # efficient tail
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        block = 1024
        data = b""
        lines = []
        while len(lines) <= n and size > 0:
            read_size = min(block, size)
            f.seek(size - read_size)
            chunk = f.read(read_size)
            data = chunk + data
            lines = data.splitlines()
            size -= read_size
            if size == 0:
                break
    # decode last n lines
    decoded = [l.decode("utf-8", errors="replace") for l in lines[-n:]]
    return decoded

# Export names for easy import
__all__ = [
    "bot_logger", "error_logger", "payment_logger", "usage_logger",
    "log_bot", "log_error", "log_payment", "log_usage",
    "read_last_lines",
]
