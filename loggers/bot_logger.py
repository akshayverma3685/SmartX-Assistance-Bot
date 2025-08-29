"""
bot_logger.py
Production-ready logger for SmartX Assistance Bot.
This writes all bot activity logs into logs/bot.log in JSON format.
"""

import os
import logging
import json
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

# =========================
# Paths & Directories
# =========================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

BOT_LOG_PATH = os.path.join(LOGS_DIR, "bot.log")

# =========================
# Custom JSON Formatter
# =========================
class JSONLogFormatter(logging.Formatter):
    """Format log records as JSON lines (one JSON object per line)."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Add extra fields if present
        for key in ("user_id", "source", "meta"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

# =========================
# Logger Factory
# =========================
def get_bot_logger() -> logging.Logger:
    """Return a configured logger for SmartX Bot activity."""
    logger = logging.getLogger("smartx.bot")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # File handler (rotating)
        fh = RotatingFileHandler(
            BOT_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(JSONLogFormatter())
        logger.addHandler(fh)

        # Optional: Console handler for debugging
        ch = logging.StreamHandler()
        ch.setFormatter(JSONLogFormatter())
        logger.addHandler(ch)

        logger.propagate = False

    return logger

# =========================
# Example Usage (remove in prod)
# =========================
if __name__ == "__main__":
    log = get_bot_logger()
    log.info("Bot started", extra={"source": "startup", "meta": {"pid": os.getpid()}})
    log.info("User executed /start", extra={"user_id": 123456789, "source": "handler.start"})
    log.warning("Rate limit hit", extra={"user_id": 999888777, "source": "middleware.rate_limit"})
    try:
        1 / 0
    except Exception:
        log.exception("Sample exception", extra={"source": "demo"})
    print(f"✅ Logs written to {BOT_LOG_PATH}")
