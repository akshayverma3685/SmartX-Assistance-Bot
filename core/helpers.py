# core/helpers.py
"""
SmartX Assistance - helper utilities

Contains:
- datetime / expiry helpers (UTC-safe)
- premium checks and activation helpers
- user CRUD conveniences that use core.database
- referral & usage increment helpers
- serialization helpers for datetimes

All functions are async where they touch DB. Pure utils are sync.
Comments & variable names in Hinglish for clarity.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging

import config
from core import database

logger = logging.getLogger("smartx_bot.helpers")

# ---------- Time helpers (UTC) ----------
UTC = timezone.utc

def now_utc() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO string (UTC). If None -> None."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def from_iso(iso_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string to timezone-aware datetime (UTC)."""
    if not iso_str:
        return None
    try:
        # Python 3.11+: fromisoformat supports offset; safe fallback with dateutil if needed
        try:
            dt = datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception:
            # use dateutil as fallback
            from dateutil.parser import parse
            dt = parse(iso_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
    except Exception as e:
        logger.debug("from_iso parse failed for %s: %s", iso_str, e)
        return None


def get_expiry_from_days(days: int) -> datetime:
    """Return a timezone-aware UTC expiry datetime 'days' from now."""
    return now_utc() + timedelta(days=days)


# ---------- Premium / Plan helpers ----------
async def is_premium(user_id: int) -> bool:
    """
    Check if user is premium.
    Works with Mongo or Postgres depending on config.DB_TYPE.
    """
    try:
        user = await database.find_user(user_id)
        if not user:
            return False
        expiry = user.get("expiry_date")
        if isinstance(expiry, str):
            expiry_dt = from_iso(expiry)
        elif isinstance(expiry, datetime):
            expiry_dt = expiry if expiry.tzinfo else expiry.replace(tzinfo=UTC)
        else:
            expiry_dt = None

        if expiry_dt and expiry_dt > now_utc():
            return True
        # Also consider explicit plan flag
        if user.get("plan") == "premium":
            # if expiry missing but plan says premium, treat as premium (defensive)
            return True
        return False
    except Exception as e:
        logger.exception("is_premium check failed for %s: %s", user_id, e)
        return False


async def extend_user_premium(user_id: int, days: int) -> Optional[Dict[str, Any]]:
    """
    Extend premium for a user by 'days'.
    If user not exists: create user doc with premium for 'days'.
    Returns updated user doc (Mongo) or dict-like record.
    """
    try:
        updated = await database.activate_premium_for_user(int(user_id), int(days))
        return updated
    except Exception as e:
        logger.exception("extend_user_premium failed: %s", e)
        return None


# ---------- User Creation / Ensure ----------
async def ensure_user_record(user_id: int, username: Optional[str] = None, language: Optional[str] = None) -> Dict[str, Any]:
    """
    Ensure user doc exists. If not, create with sane defaults (free plan).
    Returns user document.
    """
    try:
        existing = await database.find_user(user_id)
        if existing:
            # update username or language if changed
            update_fields = {}
            if username and existing.get("username") != username:
                update_fields["username"] = username
            if language and existing.get("language") != language:
                update_fields["language"] = language
            if update_fields:
                update_fields["last_updated"] = now_utc()
                if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
                    await database.get_mongo_db().users.update_one({"user_id": int(user_id)}, {"$set": update_fields})
                    existing = await database.find_user(user_id)
                else:
                    # use generic create_or_update_user to set data (Postgres path)
                    doc = existing
                    doc.update(update_fields)
                    await database.create_or_update_user(doc)
                    existing = await database.find_user(user_id)
            return existing
        # create new user
        user_doc = {
            "user_id": int(user_id),
            "username": username,
            "plan": "free",
            "expiry_date": None,
            "trial_used": False,
            "joined_date": now_utc(),
            "referrals": 0,
            "commands_used": 0,
            "language": language or getattr(config, "DEFAULT_LANGUAGE", "en"),
            "last_active": now_utc(),
        }
        created = await database.create_or_update_user(user_doc)
        return created
    except Exception as e:
        logger.exception("ensure_user_record failed for %s: %s", user_id, e)
        # last resort: return a minimal dict
        return {
            "user_id": int(user_id),
            "username": username,
            "plan": "free",
            "language": language or getattr(config, "DEFAULT_LANGUAGE", "en"),
        }


# ---------- Usage counters ----------
async def increment_command_count(user_id: int, delta: int = 1) -> None:
    """
    Increment commands_used counter for user by delta.
    Best-effort; non-blocking.
    """
    try:
        if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
            db = database.get_mongo_db()
            await db.users.update_one({"user_id": int(user_id)}, {"$inc": {"commands_used": int(delta)}, "$set": {"last_active": now_utc()}})
        else:
            user = await database.find_user(user_id)
            if not user:
                await ensure_user_record(user_id)
                user = await database.find_user(user_id)
            user["commands_used"] = int(user.get("commands_used", 0)) + int(delta)
            user["last_active"] = now_utc()
            await database.create_or_update_user(user)
    except Exception as e:
        logger.exception("increment_command_count failed for %s: %s", user_id, e)


# ---------- Referrals ----------
async def apply_referral_bonus(referrer_id: int, new_user_id: int, bonus_days: int = 1) -> bool:
    """
    Apply referral bonus: give 'bonus_days' to referrer and record referral document.
    Returns True on success.
    """
    try:
        db_type = getattr(config, "DB_TYPE", "mongo").lower()
        if db_type == "mongo":
            db = database.get_mongo_db()
            # check duplicate referral
            existing = await db.referrals.find_one({"referrer_id": int(referrer_id), "new_user_id": int(new_user_id)})
            if existing:
                logger.info("Referral already exists referrer=%s new=%s", referrer_id, new_user_id)
                return False
            # add referral record
            rec = {
                "referrer_id": int(referrer_id),
                "new_user_id": int(new_user_id),
                "bonus_days": int(bonus_days),
                "date": now_utc()
            }
            await db.referrals.insert_one(rec)
            # increment referrer counter and extend premium
            await db.users.update_one({"user_id": int(referrer_id)}, {"$inc": {"referrals": 1}})
            await extend_user_premium(referrer_id, bonus_days)
            logger.info("Referral applied: %s -> %s (+%sd)", referrer_id, new_user_id, bonus_days)
            return True
        else:
            # Postgres path: basic implementation using helpers
            # ensure referral unique logic left to DB schema; here we optimistic insert
            await database.add_payment({})  # placeholder to ensure DB available; replace as needed
            # simpler approach: extend premium
            await extend_user_premium(referrer_id, bonus_days)
            return True
    except Exception as e:
        logger.exception("apply_referral_bonus failed: %s", e)
        return False


# ---------- Display helpers ----------
def format_expiry_for_display(expiry: Optional[Any]) -> str:
    """
    Nicely format expiry datetime for showing to users.
    Accepts datetime or ISO str.
    """
    if not expiry:
        return "N/A"
    if isinstance(expiry, str):
        dt = from_iso(expiry)
    elif isinstance(expiry, datetime):
        dt = expiry if expiry.tzinfo else expiry.replace(tzinfo=UTC)
    else:
        return str(expiry)
    try:
        # format like: 2025-09-10 14:22 UTC
        return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return to_iso(dt)


# ---------- Limits check ----------
def user_feature_limits(user_doc: Dict[str, Any]) -> Dict[str, int]:
    """
    Return allowed limits for a user based on their plan.
    Example structure: {"ai_messages_per_day": X, "downloads_per_day": Y}
    """
    plan = user_doc.get("plan", "free") if user_doc else "free"
    if plan == "premium":
        return {
            "ai_messages_per_day": int(getattr(config, "PLAN_PREMIUM_LIMIT", 500)),
            "downloads_per_day": int(getattr(config, "PLAN_PREMIUM_LIMIT", 500)),
        }
    else:
        return {
            "ai_messages_per_day": int(getattr(config, "PLAN_BASIC_LIMIT", 50)),
            "downloads_per_day": int(getattr(config, "PLAN_BASIC_LIMIT", 50)),
        }


# ---------- Serialization helpers for sending over network ----------
def serialize_user_for_api(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert DB user doc to plain serializable dict (ISO strings).
    Use when returning via webhooks / API endpoints.
    """
    if not user_doc:
        return {}
    out = {}
    for k, v in user_doc.items():
        if isinstance(v, datetime):
            out[k] = to_iso(v)
        else:
            out[k] = v
    return out


# ---------- Export list ----------
__all__ = [
    "now_utc",
    "to_iso",
    "from_iso",
    "get_expiry_from_days",
    "is_premium",
    "extend_user_premium",
    "ensure_user_record",
    "increment_command_count",
    "apply_referral_bonus",
    "format_expiry_for_display",
    "user_feature_limits",
    "serialize_user_for_api",
        ]
