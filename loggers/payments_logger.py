import os
import logging
import json
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

PAYMENTS_LOG_PATH = os.path.join(LOGS_DIR, "payments.log")

class JSONLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("user_id", "source", "meta"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

def get_payments_logger() -> logging.Logger:
    logger = logging.getLogger("smartx.payments")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fh = RotatingFileHandler(
            PAYMENTS_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(JSONLogFormatter())
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(JSONLogFormatter())
        logger.addHandler(ch)

        logger.propagate = False

    return logger
