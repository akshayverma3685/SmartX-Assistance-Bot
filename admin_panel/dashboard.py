#!/usr/bin/env python3
"""
admin_panel/stats_dashboard.py

Admin CLI for SmartX Assistance Bot Stats Dashboard.

Features:
- Show overall stats (users, messages, payments, errors)
- Filter by date range (--from, --to)
- Aggregated payment stats (total, success, failed)
- Daily trends (user signups, messages, revenue)
- Output as table or JSON
"""

import argparse
import asyncio
import logging
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any

import config
from core import database

# logging setup
LOG_PATH = os.path.join(os.path.dirname(__file__), "stats_dashboard.log")
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH)],
)
logger = logging.getLogger("admin_panel.stats_dashboard")


# ---------- helpers ----------
def parse_date(val: str) -> datetime:
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.strptime(val, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def print_table(rows: list, columns: list, title: str = ""):
    if title:
        print(f"\n== {title} ==")
    if not rows:
        print("(no data)")
        return
    widths = {c: len(c) for c in columns}
    for r in rows:
        for c in columns:
            widths[c] = max(widths[c], len(str(r.get(c, ""))))
    hdr = " | ".join(c.ljust(widths[c]) for c in columns)
    sep = "-+-".join("-" * widths[c] for c in columns)
    print(hdr)
    print(sep)
    for r in rows:
        print(" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))


# ---------- DB queries ----------
async def get_user_stats(date_query: Dict[str, Any]):
    db = database.get_mongo_db()
    q = {}
    if date_query:
        q["created_at"] = date_query

    total = await db.users.count_documents(q)
    active = await db.users.count_documents({**q, "is_active": True})
    banned = await db.users.count_documents({**q, "is_banned": True})

    return {"total": total, "active": active, "banned": banned}


async def get_payment_stats(date_query: Dict[str, Any]):
    db = database.get_mongo_db()
    q = {}
    if date_query:
        q["timestamp"] = date_query

    pipeline = [
        {"$match": q},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_amount": {"$sum": "$amount"}
        }}
    ]
    results = []
    async for row in db.payments.aggregate(pipeline):
        results.append(row)

    return results


async def get_logs_stats(date_query: Dict[str, Any]):
    db = database.get_mongo_db()
    q = {}
    if date_query:
        q["timestamp"] = date_query

    total = await db.logs.count_documents(q)
    errors = await db.logs.count_documents({**q, "level": "ERROR"})
    warnings = await db.logs.count_documents({**q, "level": "WARNING"})

    return {"total_logs": total, "errors": errors, "warnings": warnings}


async def get_daily_trends(date_query: Dict[str, Any]):
    db = database.get_mongo_db()

    # user signups per day
    user_pipeline = [
        {"$match": {"created_at": date_query}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    user_trend = []
    async for row in db.users.aggregate(user_pipeline):
        user_trend.append(row)

    # revenue per day
    pay_pipeline = [
        {"$match": {"timestamp": date_query, "status": "success"}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}}, "revenue": {"$sum": "$amount"}}},
        {"$sort": {"_id": 1}}
    ]
    rev_trend = []
    async for row in db.payments.aggregate(pay_pipeline):
        rev_trend.append(row)

    return {"users": user_trend, "revenue": rev_trend}


# ---------- CLI ----------
def build_argparser():
    p = argparse.ArgumentParser(description="Admin: Stats Dashboard")
    p.add_argument("--from", dest="from_date", help="From date (YYYY-MM-DD or ISO)")
    p.add_argument("--to", dest="to_date", help="To date (YYYY-MM-DD or ISO)")
    p.add_argument("--json", action="store_true", help="Output in JSON format")
    return p


async def run():
    args = build_argparser().parse_args()

    date_query = {}
    if args.from_date or args.to_date:
        q = {}
        if args.from_date:
            q["$gte"] = parse_date(args.from_date)
        if args.to_date:
            q["$lte"] = parse_date(args.to_date)
        date_query = q

    await database.connect()
    try:
        user_stats = await get_user_stats(date_query)
        pay_stats = await get_payment_stats(date_query)
        log_stats = await get_logs_stats(date_query)
        trends = await get_daily_trends(date_query if date_query else {"$exists": True})

        if args.json:
            result = {
                "users": user_stats,
                "payments": pay_stats,
                "logs": log_stats,
                "trends": trends,
            }
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            # Users
            print_table([user_stats], ["total", "active", "banned"], "User Stats")

            # Payments
            pay_rows = [{"status": r["_id"], "count": r["count"], "total_amount": r["total_amount"]} for r in pay_stats]
            print_table(pay_rows, ["status", "count", "total_amount"], "Payment Stats")

            # Logs
            print_table([log_stats], ["total_logs", "errors", "warnings"], "Logs Stats")

            # Trends
            urows = [{"date": r["_id"], "signups": r["count"]} for r in trends["users"]]
            print_table(urows, ["date", "signups"], "User Signups Trend")

            rrows = [{"date": r["_id"], "revenue": r["revenue"]} for r in trends["revenue"]]
            print_table(rrows, ["date", "revenue"], "Daily Revenue Trend")

    finally:
        await database.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
