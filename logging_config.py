# logging_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging(level="INFO"):
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s | %(levelname)8s | %(name)s : %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = RotatingFileHandler(os.path.join(LOG_DIR, "bot.log"), maxBytes=10*1024*1024, backupCount=5)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ph = RotatingFileHandler(os.path.join(LOG_DIR, "payments.log"), maxBytes=5*1024*1024, backupCount=3)
    ph.setFormatter(fmt)
    logging.getLogger("smartx_bot.payment_service").addHandler(ph)

    eh = RotatingFileHandler(os.path.join(LOG_DIR, "errors.log"), maxBytes=5*1024*1024, backupCount=3)
    eh.setFormatter(fmt)
    logging.getLogger("smartx_bot").addHandler(eh)
