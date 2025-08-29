"""
services package initialization
This file makes all services easily importable from services.*
and ensures proper logging + error handling.
"""

import logging

# Local imports (all service modules)
from .ai_service import AIService
from .bot_logger_service import BotLoggerService
from .download_service import DownloadService
from .error_service import ErrorService
from .image_service import ImageService
from .news_service import NewsService
from .payment_service import PaymentService
from .s3_service import S3Service
from .usage_tracker import UsageTracker
from .utils_service import UtilsService

__all__ = [
    "AIService",
    "BotLoggerService",
    "DownloadService",
    "ErrorService",
    "ImageService",
    "NewsService",
    "PaymentService",
    "S3Service",
    "UsageTracker",
    "UtilsService",
]

# Setup a base logger for services
logger = logging.getLogger("services")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

logger.info("✅ services package initialized successfully")
