# logs/loggers/__init__.py
"""
Aggregate access to all SmartX Assistance Bot loggers.
"""

from .bot_logger import get_bot_logger
from .error_logger import get_error_logger
from .payments_logger import get_payments_logger
from .usage_logger import get_usage_logger

__all__ = [
    "get_bot_logger",
    "get_error_logger",
    "get_payments_logger",
    "get_usage_logger",
]
