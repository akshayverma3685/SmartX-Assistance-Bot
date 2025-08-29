from .constants import BOT_NAME, VERSION, ENV
from .database import get_db
from .cache import cache
from .logger import logger
from .logs import log_event
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
from .utils import (
    parse_config,
    send_request,
    some_util_func   # Replace with actual utility functions needed
)

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
    # utils
    "parse_config", "send_request", "some_util_func",
]

# Initialization logs
logger.info("✅ Core package initialized successfully.")
