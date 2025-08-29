# core/__init__.py
"""
SmartX Assistance Bot - Core Package

Yeh package saare essential services handle karta hai:
- Database connection
- Caching
- Logging
- Security
- Middleware
- Scheduler
- Helpers & Utilities
"""

from .constants import *        # Global constants
from .database import get_db    # Database connection
from .cache import cache        # Cache instance
from .logger import logger      # Structured logger
from .logs import log_event     # Log event helper
from .middleware import request_middleware, response_middleware
from .scheduler import scheduler, schedule_task
from .security import (
    encrypt_data,
    decrypt_data,
    verify_signature,
    generate_token,
    validate_token
)
from .helpers import (
    json_response,
    format_datetime,
    generate_id,
    retry_on_failure
)
from .utils import *            # General utilities

__all__ = [
    # constants
    "BOT_NAME", "VERSION", "ENV",
    # database
    "get_db",
    # cache
    "cache",
    # logger
    "logger",
    # logs
    "log_event",
    # middleware
    "request_middleware", "response_middleware",
    # scheduler
    "scheduler", "schedule_task",
    # security
    "encrypt_data", "decrypt_data", "verify_signature",
    "generate_token", "validate_token",
    # helpers
    "json_response", "format_datetime", "generate_id", "retry_on_failure",
]

# Initialization logs
logger.info("✅ Core package initialized successfully.")
