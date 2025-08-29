# core/logger.py
"""
Structured logging bootstrap.
- configure root logger
- optional Sentry integration (if SENTRY_DSN in config)
- exported function setup_logging(level)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# optional sentry-sdk for error capture (import lazily)
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except Exception:
    SENTRY_AVAILABLE = False

import config

LOG_DIR = getattr(config, "LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logging(level: str = "INFO"):
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s | %(levelname)8s | %(name)s : %(message)s")

    # Stdout handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler(os.path.join(LOG_DIR, "bot.log"), maxBytes=10*1024*1024, backupCount=5)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # payments log separate
    payh = RotatingFileHandler(os.path.join(LOG_DIR, "payments.log"), maxBytes=5*1024*1024, backupCount=3)
    payh.setFormatter(fmt)
    logging.getLogger("smartx_bot.payment_service").addHandler(payh)

    # errors log file
    errh = RotatingFileHandler(os.path.join(LOG_DIR, "errors.log"), maxBytes=5*1024*1024, backupCount=3)
    errh.setFormatter(fmt)
    logging.getLogger("smartx_bot").addHandler(errh)

    # Optional Sentry
    SENTRY_DSN = getattr(config, "SENTRY_DSN", os.getenv("SENTRY_DSN", None))
    if SENTRY_DSN and SENTRY_AVAILABLE:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        sentry_sdk.init(dsn=SENTRY_DSN, integrations=[sentry_logging])
        root.info("Sentry initialized")

    root.info("Logging configured (level=%s)", level)


# convenience alias
setup = setup_logging
