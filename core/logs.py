# core/logs.py
"""
core/logs.py

Centralized logging manager for SmartX Assistance.

Features:
- Rotating file handlers for: bot.log, errors.log, payments.log, usage.log
- Structured JSON-ish formatter (timestamp, level, source, user_id, meta)
- Async MongoDB recording (collection: logs) via motor (scheduled on running event loop)
- Convenience helper functions to log to the proper channel
- Utilities to read/tail log files (for admin panel or CLI)
"""

import logging
import os
import json
import asyncio
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# project imports
import config
from core import database  # assumes core.database.get_mongo_db() returns motor db

LOG_DIR = getattr(config, "LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_MAX_BYTES = int(getattr(config, "LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
LOG_BACKUP_COUNT = int(getattr(config, "LOG_BACKUP_COUNT", 5))

# collection name in Mongo where logs are duplicated for admin viewing
MONGO_LOG_COLLECTION = getattr(config, "MONGO_LOG_COLLECTION", "logs")

# -------------------------
# JSON-ish formatter
# -------------------------
class StructuredFormatter(logging.Formatter):
    """
    Format log record into JSON-ish string but readable. Will include:
    timestamp (ISO), level, logger, message, and optional fields from extra dict:
    user_id, source, meta (dict)
    """
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        # include extra props if present in record.__dict__
        extra_keys = ("user_id", "source", "meta", "ctx")
        for k in extra_keys:
            v = getattr(record, k, None)
            if v is not None:
                try:
                    base[k] = v
                except Exception:
                    base[k] = str(v)

        # include exc info if present
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)

        # produce pretty JSON (one-liner)
        try:
            return json.dumps(base, ensure_ascii=False, default=str)
        except Exception:
            # fallback to simple string
            return f"{base['timestamp']} | {base['level']} | {base['logger']} : {record.getMessage()}"

# -------------------------
# Async Mongo handler
# -------------------------
class AsyncMongoHandler(logging.Handler):
    """
    Schedules insertion of log documents into MongoDB collection.
    Uses motor (async). It schedules coroutine on current event loop.
    If event loop is not running, it will silently skip DB insertion (file logging still works).
    This avoids blocking the logging flow.
    """

    def __init__(self, collection_name: str = MONGO_LOG_COLLECTION):
        super().__init__()
        self.collection_name = collection_name
        # don't create mongo connection here; use core.database.get_mongo_db() at runtime

    def emit(self, record: logging.LogRecord):
        try:
            doc = self._record_to_doc(record)
            # schedule insertion if loop running
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # no running loop
                loop = None

            if loop and loop.is_running():
                # schedule the async insert and don't await
                asyncio.ensure_future(self._async_insert(doc))
            else:
                # no loop, try to run sync fallback: enqueue to background thread? For simplicity: skip
                # to avoid blocking main thread - log a warning
                # (We intentionally don't block here; DB logging is best-effort)
                logging.getLogger("core.logs").debug("No running loop; skipping Mongo log insert (best-effort).")
        except Exception:
            logging.getLogger("core.logs").exception("AsyncMongoHandler emit error")

    def _record_to_doc(self, record: logging.LogRecord) -> Dict[str, Any]:
        doc = {
            "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for k in ("user_id", "source", "meta", "ctx"):
            v = getattr(record, k, None)
            if v is not None:
                doc[k] = v
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return doc

    async def _async_insert(self, doc: Dict[str, Any]):
        try:
            # ensure DB connected (core.database.connect should have been called on startup)
            db = database.get_mongo_db()
            await db[self.collection_name].insert_one(doc)
        except Exception:
            # avoid infinite recursion: use plain print or low-level logging
            logging.getLogger("core.logs").exception("Failed to write log to Mongo (async)")

# -------------------------
# Logs Manager (setup)
# -------------------------
class LogsManager:
    def __init__(self, log_dir: str = LOG_DIR):
        self.log_dir = log_dir
        self.formatter = StructuredFormatter()
        self.mongo_handler = AsyncMongoHandler()

        # set up loggers
        self.bot_logger = self._create_logger("smartx_bot", os.path.join(self.log_dir, "bot.log"))
        self.error_logger = self._create_logger("smartx_errors", os.path.join(self.log_dir, "errors.log"))
        self.payment_logger = self._create_logger("smartx_payments", os.path.join(self.log_dir, "payments.log"))
        self.usage_logger = self._create_logger("smartx_usage", os.path.join(self.log_dir, "usage.log"))

    def _create_logger(self, name: str, filepath: str) -> logging.Logger:
        logger_ = logging.getLogger(name)
        logger_.setLevel(logging.INFO)  # default; individual handlers can be different
        # avoid duplicate handlers if re-init
        if any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == os.path.abspath(filepath) for h in logger_.handlers):
            return logger_
        fh = RotatingFileHandler(filepath, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8")
        fh.setFormatter(self.formatter)
        logger_.addHandler(fh)
        # also add mongo handler for DB duplication
        logger_.addHandler(self.mongo_handler)
        # also stream to root for visibility (optional)
        logger_.propagate = False
        return logger_

    # convenience logging methods
    def info(self, msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
        self.bot_logger.info(msg, extra={"user_id": user_id, "source": source, "meta": meta})

    def error(self, msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None, exc_info=None):
        self.error_logger.error(msg, extra={"user_id": user_id, "source": source, "meta": meta}, exc_info=exc_info)

    def payment(self, msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
        self.payment_logger.info(msg, extra={"user_id": user_id, "source": source, "meta": meta})

    def usage(self, msg: str, *, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
        self.usage_logger.info(msg, extra={"user_id": user_id, "source": source, "meta": meta})

# module-level singleton
_logs_manager: Optional[LogsManager] = None

def init_logs_manager():
    global _logs_manager
    if _logs_manager is None:
        _logs_manager = LogsManager()
    return _logs_manager

def get_logs_manager() -> LogsManager:
    if _logs_manager is None:
        return init_logs_manager()
    return _logs_manager

# Convenience top-level functions
def log_info(msg: str, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
    get_logs_manager().info(msg, user_id=user_id, source=source, meta=meta)

def log_error(msg: str, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None, exc_info=None):
    get_logs_manager().error(msg, user_id=user_id, source=source, meta=meta, exc_info=exc_info)

def log_payment(msg: str, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
    get_logs_manager().payment(msg, user_id=user_id, source=source, meta=meta)

def log_usage(msg: str, user_id: Optional[int] = None, source: Optional[str] = None, meta: Optional[dict] = None):
    get_logs_manager().usage(msg, user_id=user_id, source=source, meta=meta)

# -------------------------
# File read / tail utilities
# -------------------------
def read_last_lines(filepath: str, num_lines: int = 200) -> List[str]:
    """
    Efficiently read last `num_lines` lines from a file.
    Not async — used by admin scripts / web endpoints that want quick preview.
    """
    if not os.path.exists(filepath):
        return []
    # approximate: read blocks from end
    lines: List[str] = []
    with open(filepath, "rb") as f:
        f.seek(0, os.SEEK_END)
        block_size = 1024
        block = b""
        pointer = f.tell()
        while len(lines) <= num_lines and pointer > 0:
            read_size = min(block_size, pointer)
            pointer -= read_size
            f.seek(pointer)
            data = f.read(read_size)
            block = data + block
            lines = block.splitlines()
            if pointer == 0:
                break
    # decode and return last lines
    out = [l.decode("utf-8", errors="ignore") for l in lines[-num_lines:]]
    return out

async def tail_file_async(filepath: str, callback, poll_interval: float = 0.8):
    """
    Async tail file: call callback(line) for each new line appended.
    callback may be async or sync function.
    """
    if not os.path.exists(filepath):
        open(filepath, "a").close()
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        # go to end
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                await asyncio.sleep(poll_interval)
                continue
            if asyncio.iscoroutinefunction(callback):
                await callback(line.rstrip("\n"))
            else:
                try:
                    callback(line.rstrip("\n"))
                except Exception:
                    logging.getLogger("core.logs").exception("tail callback error")

# -------------------------
# Example initialization hook
# -------------------------
def setup_logging_integration():
    """
    Should be called early in bot startup (e.g., inside bot.py after core.logger.setup).
    This ensures logs manager is ready and used by other modules.
    """
    init_logs_manager()
    logging.getLogger("core.logs").info("LogsManager initialized")

# If imported, initialize default manager (safe)
init_logs_manager()
