# core/database.py
"""
Advanced DB connector & helpers for SmartX Assistance Bot.

Features:
- Supports MongoDB (motor) and Postgres (SQLAlchemy async) depending on config.DB_TYPE
- Async connect() / disconnect() for lifecycle management
- create_indexes() for Mongo collections
- Common helper functions for Users/Payments/Logs
- Connection retry logic and simple health check
- Type hints and clear logging for production use

Usage:
    await connect()
    db = get_db()            # If mongo: returns motor async database object
                             # If postgres: returns async session factory (async_sessionmaker)
    await disconnect()
"""

from typing import Optional, Any, Dict, List
import logging
import asyncio
import os
import time
from datetime import datetime, timedelta

import config

logger = logging.getLogger("smartx_bot.database")

# ---- Mongo variables ----
_mongo_client = None
_mongo_db = None

# ---- Postgres / SQLAlchemy variables ----
_async_engine = None
_async_session_factory = None

# Retry config
_MAX_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "5"))
_RETRY_DELAY = float(os.getenv("DB_CONNECT_RETRY_DELAY", "2.0"))  # seconds


# -------------------------
# CONNECT / DISCONNECT
# -------------------------
async def connect() -> None:
    """
    Initialize DB connection(s) based on config.DB_TYPE.
    This is idempotent: multiple calls won't recreate connections.
    """
    db_type = getattr(config, "DB_TYPE", "mongo").lower()
    logger.info("Initializing DB connection. DB_TYPE=%s", db_type)

    if db_type == "mongo":
        await _connect_mongo()
    elif db_type in ("postgres", "postgresql"):
        await _connect_postgres()
    else:
        raise RuntimeError(f"Unsupported DB_TYPE: {db_type}")


async def disconnect() -> None:
    """Gracefully close DB connections."""
    db_type = getattr(config, "DB_TYPE", "mongo").lower()
    logger.info("Disconnecting DB. DB_TYPE=%s", db_type)

    if db_type == "mongo":
        await _disconnect_mongo()
    else:
        await _disconnect_postgres()


# -------------------------
# MONGO (motor) impl
# -------------------------
async def _connect_mongo() -> None:
    global _mongo_client, _mongo_db
    if _mongo_client:
        logger.debug("Mongo client already connected.")
        return

    from motor.motor_asyncio import AsyncIOMotorClient

    uri = getattr(config, "MONGO_URI", None)
    if not uri:
        raise RuntimeError("MONGO_URI not configured in config.py/.env")

    attempt = 0
    while attempt < _MAX_RETRIES:
        try:
            logger.info("Connecting to MongoDB (attempt %d)...", attempt + 1)
            _mongo_client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
            # wait for server info to ensure connection
            await _mongo_client.server_info()
            db_name = getattr(config, "MONGO_DB_NAME", None) or _mongo_client.get_default_database().name
            _mongo_db = _mongo_client[db_name]
            logger.info("Connected to MongoDB database: %s", db_name)
            # create indexes (non-blocking)
            try:
                await create_mongo_indexes()
            except Exception as e:
                logger.exception("create_mongo_indexes failed: %s", e)
            return
        except Exception as e:
            attempt += 1
            logger.warning("MongoDB connect failed (attempt %d): %s", attempt, e)
            await asyncio.sleep(_RETRY_DELAY * attempt)
    raise RuntimeError("Could not connect to MongoDB after retries.")


async def _disconnect_mongo() -> None:
    global _mongo_client
    if _mongo_client:
        try:
            _mongo_client.close()
            logger.info("MongoDB client closed.")
        except Exception:
            logger.exception("Error closing MongoDB client.")
        finally:
            _mongo_client = None


def get_mongo_db():
    """Return motor database object (or raise if not connected)."""
    if not _mongo_db:
        raise RuntimeError("MongoDB not connected. Call connect() first.")
    return _mongo_db


# -------------------------
# POSTGRES (SQLAlchemy async) impl
# -------------------------
async def _connect_postgres() -> None:
    """
    Create async engine and session factory using SQLAlchemy 1.4/2.0 async API.
    """
    global _async_engine, _async_session_factory
    if _async_engine:
        logger.debug("Async PG engine already initialized.")
        return

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    user = getattr(config, "POSTGRES_USER", "postgres")
    pw = getattr(config, "POSTGRES_PASSWORD", "password")
    host = getattr(config, "POSTGRES_HOST", "localhost")
    port = getattr(config, "POSTGRES_PORT", 5432)
    db = getattr(config, "POSTGRES_DB", "smartx")

    dsn = f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}"

    attempt = 0
    while attempt < _MAX_RETRIES:
        try:
            logger.info("Connecting to Postgres (attempt %d)...", attempt + 1)
            _async_engine = create_async_engine(dsn, echo=False, pool_size=10, max_overflow=20)
            _async_session_factory = async_sessionmaker(_async_engine, expire_on_commit=False)
            # quick test connection
            async with _async_engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: None)
            logger.info("Connected to Postgres DB: %s@%s:%s/%s", user, host, port, db)
            return
        except Exception as e:
            attempt += 1
            logger.warning("Postgres connect failed (attempt %d): %s", attempt, e)
            await asyncio.sleep(_RETRY_DELAY * attempt)
    raise RuntimeError("Could not connect to Postgres after retries.")


async def _disconnect_postgres() -> None:
    global _async_engine, _async_session_factory
    if _async_engine:
        try:
            await _async_engine.dispose()
            logger.info("Postgres engine disposed.")
        except Exception:
            logger.exception("Error disposing Postgres engine.")
        finally:
            _async_engine = None
            _async_session_factory = None


def get_postgres_session_factory():
    """
    Returns async_sessionmaker instance for use with 'async with session_factory()' blocks.
    """
    if not _async_session_factory:
        raise RuntimeError("Postgres not connected. Call connect() first.")
    return _async_session_factory


# -------------------------
# INDEX CREATION (Mongo)
# -------------------------
async def create_mongo_indexes():
    """
    Create indexes for MongoDB collections used by the bot.
    Non-blocking best-effort; called on startup.
    """
    db = get_mongo_db()
    # Users collection: index on user_id (unique), expiry_date for queries
    try:
        await db.users.create_index("user_id", unique=True)
        await db.users.create_index("expiry_date")
        await db.users.create_index("plan")
        # Payments: index on payment_id, user_id, date
        await db.payments.create_index("payment_id", unique=True)
        await db.payments.create_index("user_id")
        await db.payments.create_index("date")
        # Logs: timestamp index
        await db.logs.create_index("timestamp")
        # Referrals
        await db.referrals.create_index("referrer_id")
        logger.info("MongoDB indexes created/ensured.")
    except Exception:
        logger.exception("Error creating MongoDB indexes.")


# -------------------------
# HEALTH CHECK
# -------------------------
async def healthcheck() -> Dict[str, Any]:
    """Return a simple health dict for monitoring."""
    db_type = getattr(config, "DB_TYPE", "mongo").lower()
    status = {"db_type": db_type, "ok": False, "details": {}}
    try:
        if db_type == "mongo":
            db = get_mongo_db()
            # ping
            res = await db.command({"ping": 1})
            status["ok"] = res.get("ok") == 1
            status["details"] = res
        else:
            # try simple query
            session_factory = get_postgres_session_factory()
            async with session_factory() as session:
                res = await session.execute("SELECT 1")
                status["ok"] = True
                status["details"] = {"msg": "pg ok"}
    except Exception as e:
        logger.exception("Healthcheck failed: %s", e)
        status["ok"] = False
        status["error"] = str(e)
    return status


# -------------------------
# COMMON HELPERS (Users / Payments / Logs)
# -------------------------
# NOTE: For Postgres mode you should implement ORM models & use session CRUD.
# Here we provide generic helpers for Mongo default (most common for bots).
# If DB_TYPE == postgres you can either map these helpers to SQLAlchemy models
# or keep a separate implementation file.
# For now these helpers are optimized for Mongo usage.

async def find_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Return user document or None."""
    if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
        db = get_mongo_db()
        return await db.users.find_one({"user_id": int(user_id)})
    else:
        # Postgres path: implement as needed (simple example using JSON store table)
        session_factory = get_postgres_session_factory()
        async with session_factory() as session:
            # expecting a 'users' table with jsonb 'data' column; customize as per your schema
            q = "SELECT data FROM users WHERE user_id = :uid LIMIT 1"
            result = await session.execute(q, {"uid": user_id})
            row = result.first()
            return row[0] if row else None


async def create_or_update_user(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert or update user document. Returns the final user document.
    user_doc must contain 'user_id'.
    """
    if "user_id" not in user_doc:
        raise ValueError("user_doc must contain user_id")

    if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
        db = get_mongo_db()
        await db.users.update_one({"user_id": int(user_doc["user_id"])}, {"$set": user_doc}, upsert=True)
        return await db.users.find_one({"user_id": int(user_doc["user_id"])})
    else:
        # Postgres: upsert example (requires proper table schema)
        session_factory = get_postgres_session_factory()
        async with session_factory() as session:
            # This is just illustrative - adapt to your ORM/table
            q = """
            INSERT INTO users (user_id, data, created_at)
            VALUES (:uid, :data, now())
            ON CONFLICT (user_id) DO UPDATE SET data = :data
            RETURNING data;
            """
            params = {"uid": int(user_doc["user_id"]), "data": user_doc}
            res = await session.execute(q, params)
            await session.commit()
            row = res.first()
            return row[0] if row else user_doc


async def add_payment(payment_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert payment doc to payments collection/table.
    Required fields: payment_id, user_id, amount, status, method
    """
    if "payment_id" not in payment_doc:
        raise ValueError("payment_doc requires 'payment_id'")

    if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
        db = get_mongo_db()
        await db.payments.insert_one(payment_doc)
        return payment_doc
    else:
        session_factory = get_postgres_session_factory()
        async with session_factory() as session:
            q = "INSERT INTO payments (payment_id, user_id, data, created_at) VALUES (:pid, :uid, :data, now())"
            params = {"pid": payment_doc["payment_id"], "uid": payment_doc["user_id"], "data": payment_doc}
            await session.execute(q, params)
            await session.commit()
            return payment_doc


async def log_event(log_doc: Dict[str, Any]) -> None:
    """
    Insert log to logs collection (non-blocking best effort).
    log_doc often contains: {type, user_id, action, details, timestamp}
    """
    try:
        if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
            db = get_mongo_db()
            await db.logs.insert_one(log_doc)
        else:
            session_factory = get_postgres_session_factory()
            async with session_factory() as session:
                q = "INSERT INTO logs (data, created_at) VALUES (:data, now())"
                await session.execute(q, {"data": log_doc})
                await session.commit()
    except Exception:
        logger.exception("Failed to write log (best-effort).")


# -------------------------
# UTILS: Premium helpers
# -------------------------
async def activate_premium_for_user(user_id: int, days: int) -> Dict[str, Any]:
    """
    Give user premium for 'days' days. Handles creation if user missing.
    Returns updated user doc.
    """
    if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
        db = get_mongo_db()
        user = await db.users.find_one({"user_id": int(user_id)})
        from dateutil.parser import parse

        if not user:
            expiry = datetime.utcnow() + timedelta(days=days)
            user_doc = {
                "user_id": int(user_id),
                "username": None,
                "plan": "premium",
                "expiry_date": expiry,
                "trial_used": False,
                "joined_date": datetime.utcnow(),
                "referrals": 0,
                "commands_used": 0,
                "language": getattr(config, "DEFAULT_LANGUAGE", "en"),
            }
            await db.users.insert_one(user_doc)
            logger.info("Created user %s and activated premium until %s", user_id, expiry)
            return user_doc
        else:
            expiry = user.get("expiry_date")
            # parse if string
            if expiry and isinstance(expiry, str):
                expiry = parse(expiry)
            if not expiry or expiry < datetime.utcnow():
                new_expiry = datetime.utcnow() + timedelta(days=days)
            else:
                new_expiry = expiry + timedelta(days=days)
            await db.users.update_one({"user_id": int(user_id)}, {"$set": {"plan": "premium", "expiry_date": new_expiry}})
            updated = await db.users.find_one({"user_id": int(user_id)})
            logger.info("Activated premium for user %s until %s", user_id, new_expiry)
            return updated
    else:
        # Postgres example: implement using your schema
        session_factory = get_postgres_session_factory()
        async with session_factory() as session:
            # simplistic approach: store user data as json in 'users' table
            q = "SELECT data FROM users WHERE user_id = :uid"
            res = await session.execute(q, {"uid": user_id})
            row = res.first()
            if not row:
                new_doc = {
                    "user_id": user_id,
                    "plan": "premium",
                    "expiry_date": (datetime.utcnow() + timedelta(days=days)).isoformat(),
                }
                insert_q = "INSERT INTO users (user_id, data, created_at) VALUES (:uid, :data, now())"
                await session.execute(insert_q, {"uid": user_id, "data": new_doc})
                await session.commit()
                return new_doc
            else:
                data = row[0]
                expiry = data.get("expiry_date")
                if expiry:
                    from dateutil.parser import parse as _parse
                    expiry_dt = _parse(expiry) if isinstance(expiry, str) else expiry
                else:
                    expiry_dt = None
                if not expiry_dt or expiry_dt < datetime.utcnow():
                    new_expiry = datetime.utcnow() + timedelta(days=days)
                else:
                    new_expiry = expiry_dt + timedelta(days=days)
                data["plan"] = "premium"
                data["expiry_date"] = new_expiry.isoformat()
                update_q = "UPDATE users SET data = :data WHERE user_id = :uid"
                await session.execute(update_q, {"data": data, "uid": user_id})
                await session.commit()
                return data


# -------------------------
# EXPORTS
# -------------------------
__all__ = [
    "connect",
    "disconnect",
    "get_mongo_db",
    "get_postgres_session_factory",
    "healthcheck",
    "find_user",
    "create_or_update_user",
    "add_payment",
    "log_event",
    "activate_premium_for_user",
    ]
