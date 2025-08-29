#!/usr/bin/env python3
"""
admin_panel/user_manager.py

Admin CLI to manage users: search, view, ban/unban, extend premium, set plan, soft-delete, export.

Usage examples:
  python user_manager.py --list --page 1 --limit 30
  python user_manager.py --search 123456
  python user_manager.py --detail 123456
  python user_manager.py --ban 123456 --confirm
  python user_manager.py --unban 123456 --confirm
  python user_manager.py --extend 123456 --days 30 --confirm
  python user_manager.py --set-plan 123456 --plan premium --days 30 --confirm
  python user_manager.py --delete 123456 --confirm
  python user_manager.py --list --plan premium --export premium_page1.csv
"""

import argparse
import asyncio
import logging
import os
import sys
import json
import csv
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# project imports
import config
from core import database, helpers

# logging
LOG_PATH = os.path.join(os.path.dirname(__file__), "user_management.log")
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH)],
)
logger = logging.getLogger("admin_panel.user_management")


# ----------------- utility helpers -----------------
def parse_args():
    p = argparse.ArgumentParser(description="Admin: Manage users")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List users (use --page/--limit/filters)")
    group.add_argument("--search", help="Search user by user_id or username (partial allowed)")
    group.add_argument("--detail", help="Show user detail by user_id")
    group.add_argument("--ban", help="Ban user by user_id (soft flag)")
    group.add_argument("--unban", help="Unban user by user_id")
    group.add_argument("--extend", help="Extend user's premium by days: provide user_id")
    group.add_argument("--set-plan", help="Set user plan explicitly (user_id)")
    group.add_argument("--delete", help="Soft-delete user by user_id")
    p.add_argument("--page", type=int, default=1, help="Page number for listing")
    p.add_argument("--limit", type=int, default=50, help="Limit per page for listing")
    p.add_argument("--plan", help="Filter by plan (free/premium) or used with --set-plan")
    p.add_argument("--lang", help="Filter by language code for listing")
    p.add_argument("--days", type=int, help="Number of days (for extend or set-plan expiry)")
    p.add_argument("--confirm", action="store_true", help="Confirm action (required for modifying ops)")
    p.add_argument("--export", help="Export current listing to CSV file")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    return p.parse_args()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def audit_log(action: str, actor: Optional[int], target_user: Optional[int], details: Dict[str, Any]):
    """
    Record admin actions to admin_actions collection for audit trail.
    """
    try:
        db = database.get_mongo_db()
        rec = {
            "action": action,
            "actor": actor,
            "target_user": target_user,
            "details": details,
            "timestamp": now_iso(),
        }
        await db.admin_actions.insert_one(rec)
    except Exception:
        logger.exception("Failed to write audit log (best-effort)")


# ----------------- DB operations -----------------
async def list_users(query: Dict[str, Any], page: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Return list of user docs for given query with pagination.
    Works with Mongo primarily.
    """
    if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
        db = database.get_mongo_db()
        skip = (page - 1) * limit
        cursor = db.users.find(query).sort("joined_date", -1).skip(skip).limit(limit)
        out = []
        async for d in cursor:
            out.append(d)
        return out
    else:
        # Postgres path: depends on schema; use generic find_user usage by scanning users table is heavy.
        # Use database.create_or_update_user / find_user as appropriate. Here we'll fallback to scanning via SQL if implemented.
        session_factory = database.get_postgres_session_factory()
        async with session_factory() as session:
            q = "SELECT data FROM users LIMIT :limit OFFSET :offset"
            res = await session.execute(q, {"limit": limit, "offset": (page - 1) * limit})
            rows = res.fetchall()
            return [r[0] for r in rows]


async def find_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    return await database.find_user(user_id)


async def find_users_by_username_partial(partial: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Partial username search (Mongo regex). Returns list.
    """
    if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
        db = database.get_mongo_db()
        cursor = db.users.find({"username": {"$regex": partial, "$options": "i"}}).limit(limit)
        out = []
        async for d in cursor:
            out.append(d)
        return out
    else:
        # Postgres fallback not implemented generically
        return []


async def set_user_flag(user_id: int, flag: str, value: Any) -> bool:
    """
    Generic setter for boolean flags like is_banned, is_deleted.
    """
    try:
        if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
            db = database.get_mongo_db()
            await db.users.update_one({"user_id": int(user_id)}, {"$set": {flag: value}})
            return True
        else:
            user = await database.find_user(user_id)
            if not user:
                return False
            user[flag] = value
            await database.create_or_update_user(user)
            return True
    except Exception:
        logger.exception("set_user_flag failed")
        return False


async def set_user_plan(user_id: int, plan: str, expiry_days: Optional[int] = None) -> bool:
    """
    Set user's plan and optionally expiry. expiry_days = None => no expiry set.
    """
    try:
        if plan not in ("free", "premium"):
            raise ValueError("plan must be 'free' or 'premium'")
        if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
            db = database.get_mongo_db()
            update = {"plan": plan}
            if expiry_days:
                expiry_dt = helpers.get_expiry_from_days(expiry_days)
                update["expiry_date"] = expiry_dt
            else:
                # if setting to free, clear expiry
                if plan == "free":
                    update["expiry_date"] = None
            await db.users.update_one({"user_id": int(user_id)}, {"$set": update})
            return True
        else:
            user = await database.find_user(user_id)
            if not user:
                return False
            user["plan"] = plan
            if expiry_days:
                user["expiry_date"] = helpers.get_expiry_from_days(expiry_days)
            else:
                if plan == "free":
                    user["expiry_date"] = None
            await database.create_or_update_user(user)
            return True
    except Exception:
        logger.exception("set_user_plan failed")
        return False


async def soft_delete_user(user_id: int) -> bool:
    return await set_user_flag(user_id, "is_deleted", True)


async def export_users_to_csv(docs: List[Dict[str, Any]], path: str):
    if not docs:
        logger.info("No users to export.")
        return
    keys = set()
    for d in docs:
        keys.update(d.keys())
    preferred = ["user_id", "username", "plan", "expiry_date", "joined_date", "language", "referrals", "commands_used", "is_banned", "is_deleted"]
    headers = [k for k in preferred if k in keys] + [k for k in sorted(keys) if k not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for d in docs:
            row = {}
            for h in headers:
                val = d.get(h, "")
                if isinstance(val, (dict, list)):
                    row[h] = json.dumps(val, ensure_ascii=False)
                else:
                    row[h] = str(val) if val is not None else ""
            writer.writerow(row)
    logger.info("Exported %d users to %s", len(docs), path)


# ----------------- CLI orchestration -----------------
async def run():
    args = parse_args()

    # connect DB
    try:
        await database.connect()
    except Exception as e:
        logger.exception("DB connect failed: %s", e)
        return

    try:
        # LIST
        if args.list:
            q = {}
            if args.plan:
                q["plan"] = args.plan
            if args.lang:
                q["language"] = args.lang
            # skip deleted by default
            q["is_deleted"] = {"$ne": True}
            users = await list_users(q, page=args.page, limit=args.limit)
            if args.json:
                print(json.dumps(users, default=str, ensure_ascii=False, indent=2))
            else:
                rows = []
                for u in users:
                    rows.append({
                        "user_id": u.get("user_id"),
                        "username": u.get("username"),
                        "plan": u.get("plan"),
                        "expiry": helpers.format_expiry_for_display(u.get("expiry_date")),
                        "joined": str(u.get("joined_date")),
                        "lang": u.get("language"),
                        "banned": u.get("is_banned", False),
                    })
                cols = ["user_id", "username", "plan", "expiry", "joined", "lang", "banned"]
                # print table
                widths = {c: len(c) for c in cols}
                for r in rows:
                    for c in cols:
                        widths[c] = max(widths[c], len(str(r.get(c, ""))))
                hdr = " | ".join(c.ljust(widths[c]) for c in cols)
                sep = "-+-".join("-" * widths[c] for c in cols)
                print(hdr); print(sep)
                for r in rows:
                    print(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
            # export if requested
            if args.export:
                await export_users_to_csv(users, args.export)

        # SEARCH
        elif args.search:
            q = args.search.strip()
            # if numeric treat as user_id
            if q.isdigit():
                user = await find_user_by_id(int(q))
                if not user:
                    print(f"No user found with id {q}")
                else:
                    print(json.dumps(user, default=str, ensure_ascii=False, indent=2))
            else:
                users = await find_users_by_username_partial(q, limit=args.limit)
                if not users:
                    print("No users found for username partial:", q)
                else:
                    print(json.dumps(users, default=str, ensure_ascii=False, indent=2))

        # DETAIL
        elif args.detail:
            uid = int(args.detail)
            user = await find_user_by_id(uid)
            if not user:
                print("User not found.")
            else:
                print(json.dumps(user, default=str, ensure_ascii=False, indent=2))

        # BAN
        elif args.ban:
            uid = int(args.ban)
            if not args.confirm:
                print("Action requires --confirm flag to proceed.")
                return
            ok = await set_user_flag(uid, "is_banned", True)
            if ok:
                print(f"User {uid} banned.")
                await audit_log("ban", getattr(config, "OWNER_ID", None), uid, {"by": "admin_panel", "time": now_iso()})
            else:
                print("Failed to ban user. See logs.")

        # UNBAN
        elif args.unban:
            uid = int(args.unban)
            if not args.confirm:
                print("Action requires --confirm flag to proceed.")
                return
            ok = await set_user_flag(uid, "is_banned", False)
            if ok:
                print(f"User {uid} unbanned.")
                await audit_log("unban", getattr(config, "OWNER_ID", None), uid, {"by": "admin_panel", "time": now_iso()})
            else:
                print("Failed to unban user. See logs.")

        # EXTEND
        elif args.extend:
            uid = int(args.extend)
            if not args.days:
                print("Provide --days to extend premium.")
                return
            if not args.confirm:
                print("Action requires --confirm flag.")
                return
            res = await helpers.extend_user_premium(uid, args.days)
            if res:
                print(f"Extended premium for {uid} by {args.days} days.")
                await audit_log("extend_premium", getattr(config, "OWNER_ID", None), uid, {"days": args.days, "time": now_iso()})
            else:
                print("Failed to extend premium. See logs.")

        # SET-PLAN
        elif args.set_plan:
            uid = int(args.set_plan)
            if not args.plan:
                print("Provide --plan (free|premium).")
                return
            if args.plan not in ("free", "premium"):
                print("Invalid plan. Use 'free' or 'premium'.")
                return
            if not args.confirm:
                print("Action requires --confirm flag.")
                return
            ok = await set_user_plan(uid, args.plan, expiry_days=args.days)
            if ok:
                print(f"User {uid} set to plan '{args.plan}'.")
                await audit_log("set_plan", getattr(config, "OWNER_ID", None), uid, {"plan": args.plan, "days": args.days, "time": now_iso()})
            else:
                print("Failed to set plan. See logs.")

        # DELETE (soft)
        elif args.delete:
            uid = int(args.delete)
            if not args.confirm:
                print("Action requires --confirm flag.")
                return
            ok = await soft_delete_user(uid)
            if ok:
                print(f"User {uid} soft-deleted.")
                await audit_log("soft_delete", getattr(config, "OWNER_ID", None), uid, {"time": now_iso()})
            else:
                print("Failed to delete user. See logs.")

    finally:
        # disconnect DB
        try:
            await database.disconnect()
        except Exception:
            logger.debug("DB disconnect failed")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
