# core/database.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import asyncio
import config

logger = logging.getLogger("smartx_bot.database")
_client: Optional[AsyncIOMotorClient] = None
db = None

async def connect():
    global _client, db
    if _client:
        return
    logger.info("Connecting to MongoDB...")
    _client = AsyncIOMotorClient(config.MONGO_URI)
    # optional: wait for server info
    try:
        await _client.server_info()
    except Exception as e:
        logger.exception("MongoDB server_info failed")
        raise
    db = _client.get_default_database()
    logger.info("MongoDB connected: %s", db.name)

async def disconnect():
    global _client
    if _client:
        logger.info("Closing MongoDB connection...")
        _client.close()
        _client = None
