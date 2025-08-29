from aiogram import Bot, Dispatcher
import asyncio
import logging
from typing import Optional
from aiogram.types import BotCommand
from aiogram.exceptions import (
     TelegramBadRequest, 
     TelegramRetryAfter,
     TelegramAPIError
)
# try to import project modules (these should exist as per structure)
try:
    import config
except Exception as e:
    raise RuntimeError(
        "Missing config.py — create it before running bot. See README.") from e

# core modules are optional at import time; but we'll attempt to import gracefully
try:
    from core import database, middleware, scheduler
except Exception:
    database = None
    middleware = None
    scheduler = None

HANDLER_MODULES = [
    "handlers.start",
    "handlers.menu",
    "handlers.ai",
    "handlers.downloader",
    "handlers.tools",
    "handlers.business",
    "handlers.entertainment",
    "handlers.premium",
    "handlers.profile",
    "handlers.admin",
]

# Set up logging
LOG_LEVEL = getattr(logging, getattr(config, "LOG_LEVEL", "INFO"))
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
)
logger = logging.getLogger("smartx_bot")

# Global singletons
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None


async def set_default_commands(b: Bot):
    """
    Set friendly bot commands visible in Telegram UI (global).
    Update as per features.
    """
    commands = [
        BotCommand(command="/start", description="Start the bot / भाषा चुनें"),
        BotCommand(command="/help", description="Help & commands list"),
        BotCommand(command="/profile", description="View your profile & plan"),
        BotCommand(command="/premium", description="Buy/Manage Premium"),
    ]
    try:
        await b.set_my_commands(commands)
        logger.debug("Default commands set.")
    except Exception as e:
        logger.warning("Failed to set default commands: %s", e)


async def register_handlers(dispatcher: Dispatcher):
    """
    Dynamically import and register handler modules.
    Each module must implement `def register(dp: Dispatcher):` function.
    This pattern avoids hard breaking import errors
    when some handler files are not yet implemented.
    """
    for module_path in HANDLER_MODULES:
        try:
            module = __import__(module_path, fromlist=["register"])
            register_fn = getattr(module, "register", None)
            if callable(register_fn):
                register_fn(dispatcher)
                logger.info("Registered handlers from %s", module_path)
            else:
                logger.debug(
                    "Module %s has no register(dp) — skipping", module_path)
        except ModuleNotFoundError:
            logger.debug(
                "Handler module %s not found — skipping", module_path)
        except Exception as e:
            logger.exception(
                "Error while registering handlers from %s: %s", module_path, e)


async def on_startup():
    """
    Startup tasks:
    - Initialize DB connection
    - Run migrations / ensure indexes (if implemented)
    - Start scheduler
    - Set default commands
    - Any owner notification
    """
    logger.info("Starting SmartX Assistance bot...")

    global bot
    if database:
        try:
            await database.connect()  
            # implement async connect in core/database.py
            logger.info("Database connected.")
        except Exception as e:
            logger.exception("Database connection failed: %s", e)
            raise

    if scheduler and getattr(scheduler, "start_scheduler", None):
        try:
            await scheduler.start_scheduler()
            logger.info("Scheduler started.")
        except Exception as e:
            logger.exception("Failed to start scheduler: %s", e)

    # set bot commands
    try:
        await set_default_commands(bot)
    except Exception:
        logger.exception("Failed to set default commands.")

    # Owner notification (optional)
    try:
        owner_id = getattr(config, "OWNER_ID", None)
        if owner_id:
            await bot.send_message(owner_id, "SmartX Assistance bot started ✅")
            logger.debug("Sent startup notification to owner %s", owner_id)
    except Exception:
        logger.debug("Could not notify owner on startup (it's optional).")


async def on_shutdown():
    """
    Graceful shutdown:
    - Stop scheduler
    - Close DB connection
    - Close bot session
    """
    logger.info("Shutting down SmartX Assistance bot...")

    if scheduler and getattr(scheduler, "stop_scheduler", None):
        try:
            await scheduler.stop_scheduler()
            logger.info("Scheduler stopped.")
        except Exception:
            logger.exception("Error stopping scheduler.")

    if database:
        try:
            await database.disconnect()
            logger.info("Database disconnected.")
        except Exception:
            logger.exception("Error disconnecting database.")

    # Close bot session
    global bot
    if bot:
        try:
            await bot.session.close()
            logger.info("Bot session closed.")
        except Exception:
            logger.exception("Error closing bot session.")


def setup_middlewares(dispatcher: Dispatcher):
    """
    Register middleware from core/middleware.py if present.
    Recommended middlewares:
     - LanguageLoaderMiddleware (loads locale strings per user)
     - AuthMiddleware (restricts admin commands)
     - LoggingMiddleware
    """
    if not middleware:
        logger.debug("No middleware package found; skipping middleware registration.")
        return

    try:
        if getattr(middleware, "LanguageMiddleware", None):
            dispatcher.message.outer_middleware(
            middleware.LanguageMiddleware())
            dispatcher.callback_query.outer_middleware(
            middleware.LanguageMiddleware())
            logger.info("LanguageMiddleware registered.")
    except Exception:
        logger.exception("Failed to register LanguageMiddleware.")


async def start_polling():
    """
    Start long polling (default development mode).
    """
    global bot, dp
    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    dp.bind_bot(bot)

    setup_middlewares(dp)

    # register handlers (dynamically)
    await register_handlers(dp)

    # start up tasks
    await on_startup()

    logger.info("Starting polling...")
    try:
        # in aiogram v3: dp.start_polling(bot) — but we'll use dp.start_polling()
        await dp.start_polling(bot)
    finally:
        await on_shutdown()


async def start_webhook():
    """
    Start webhook server. Requires config.WEBHOOK_* variables.
    This implementation expects `config.WEBHOOK_URL` and optional 
    `WEBAPP_HOST`, `WEBAPP_PORT`.
    Use an ASGI server (e.g., uvicorn) or aiogram's built-in 
    webhook runner depending on version.
    """
    webhook_url = getattr(config, "WEBHOOK_URL", None)
    if not webhook_url:
        raise RuntimeError(
        "WEBHOOK_URL not configured. Use polling or set webhook variables.")

    global bot, dp
    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    dp.bind_bot(bot)

    setup_middlewares(dp)
    await register_handlers(dp)
    await on_startup()

    # set webhook
    try:
        await bot.set_webhook(webhook_url)
        logger.info("Webhook set to %s", webhook_url)
    except Exception:
        logger.exception("Failed to set webhook.")

    # keep running until cancelled
    try:
        logger.info("Webhook mode is running. Press Ctrl+C to exit.")
        while True:
            await asyncio.sleep(3600)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Webhook loop cancelled.")
    finally:
        # remove webhook on shutdown
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted.")
        except Exception:
            logger.exception("Failed to delete webhook.")
        await on_shutdown()


def main():
    """
    Entry point. Choose mode based on config.
    """
    mode = getattr(config, "RUN_MODE", "polling").lower()
    logger.info("Run mode: %s", mode)

    if mode == "webhook":
        # run webhook loop
        try:
            asyncio.run(start_webhook())
        except Exception as e:
            logger.exception("Fatal error in webhook mode: %s", e)
    else:
        # default polling
        try:
            asyncio.run(start_polling())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user (KeyboardInterrupt).")
        except Exception as e:
            logger.exception("Fatal error in polling mode: %s", e)


if __name__ == "__main__":
    main()
