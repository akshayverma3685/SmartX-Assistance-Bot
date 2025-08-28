# core/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core import database
from datetime import datetime
logger = logging.getLogger("smartx_bot.scheduler")

_scheduler = AsyncIOScheduler()

async def start_scheduler():
    # example: daily job at midnight UTC to expire/check users
    _scheduler.add_job(check_expired_users, 'interval', hours=24, next_run_time=datetime.utcnow())
    _scheduler.start()
    logger.info("Scheduler started with daily check job.")

async def stop_scheduler():
    _scheduler.shutdown()
    logger.info("Scheduler stopped.")

async def check_expired_users():
    logger.info("Running check_expired_users job.")
    try:
        coll = database.db.users
        now = datetime.utcnow()
        # find expired premium users
        cursor = coll.find({"expiry_date": {"$lte": now}})
        updated = []
        async for u in cursor:
            # set plan to free
            await coll.update_one({"_id": u["_id"]}, {"$set": {"plan": "free", "expiry_date": None}})
            updated.append(u["user_id"])
        logger.info("Expired users reset to free: %d", len(updated))
    except Exception as e:
        logger.exception("Error in check_expired_users: %s", e)
