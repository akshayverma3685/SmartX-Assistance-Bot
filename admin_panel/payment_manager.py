import argparse
import asyncio
import logging
import os
import sys
import csv
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import config
from core import database

# logging setup
LOG_PATH = os.path.join(
    os.path.dirname(__file__), "payment_logs.log")
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH)],
)
logger = logging.getLogger("admin_panel.payment_logs")


# ---------- helpers ----------
def parse_date(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            dt = datetime.strptime(val, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            raise ValueError(f"Invalid date format: {val}")


def build_query(args: argparse.Namespace) -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    if args.user:
        try:
            q["user_id"] = int(args.user)
        except Exception:
            q["user_id"] = args.user
    if args.status:
        q["status"] = args.status.lower()
    date_query = {}
    if args.from_date:
        date_query["$gte"] = parse_date(args.from_date)
    if args.to_date:
        date_query["$lte"] = parse_date(args.to_date)
    if date_query:
        q["timestamp"] = date_query
    return q


def print_table(rows: list, columns: list):
    if not rows:
        print("(no rows)")
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


# ---------- DB operations ----------
async def fetch_payments(query: dict, page: int, limit: int):
    db = database.get_mongo_db()
    skip = (page - 1) * limit
    cursor = db.payments.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = []
    async for doc in cursor:
        docs.append(doc)
    return docs


async def export_csv(docs, path: str):
    if not docs:
        logger.info("No payments to export.")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        keys = set()
        for d in docs:
            keys.update(d.keys())
        preferred = [
            "timestamp", "user_id",
            "amount", "currency", "status", "method", "transaction_id"]
        headers = [k for k in preferred if k in keys] + [
            k for k in sorted(keys) if k not in preferred]
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
    logger.info("Exported %d payments to %s", len(docs), path)


async def summary_stats(query: dict):
    db = database.get_mongo_db()
    pipeline = [
        {"$match": query},
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


# ---------- CLI ----------
def build_argparser():
    p = argparse.ArgumentParser(description="Admin: view & export payment logs")
    p.add_argument("--user", help="Filter by user id")
    p.add_argument("--status", help="Filter by status (success, failed, pending)")
    p.add_argument("--from", dest="from_date", help="From date (YYYY-MM-DD or ISO)")
    p.add_argument("--to", dest="to_date", help="To date (YYYY-MM-DD or ISO)")
    p.add_argument("--page", type=int, default=1, help="Page number")
    p.add_argument("--limit", type=int, default=50, help="Rows per page")
    p.add_argument("--export", help="Export to CSV file")
    p.add_argument("--jsonl", action="store_true", help="Output JSON-lines")
    p.add_argument("--summary", action="store_true", help="Show summary stats")
    return p


async def run():
    args = build_argparser().parse_args()
    try:
        query = build_query(args)
    except ValueError as e:
        logger.error(e)
        return

    await database.connect()
    try:
        docs = await fetch_payments(query, page=args.page, limit=args.limit)

        if args.jsonl:
            for d in docs:
                print(json.dumps(d, default=str, ensure_ascii=False))
        else:
            cols = ["timestamp", "user_id", "amount", "currency", "status", "method"]
            rows = []
            for d in docs:
                rows.append({
                    "timestamp": d.get("timestamp"),
                    "user_id": d.get("user_id"),
                    "amount": d.get("amount"),
                    "currency": d.get("currency", "INR"),
                    "status": d.get("status"),
                    "method": d.get("method", "razorpay")
                })
            print_table(rows, cols)

        if args.export:
            await export_csv(docs, args.export)

        if args.summary:
            stats = await summary_stats(query)
            print("\nSummary:")
            for row in stats:
                print(f"  {row['_id']}: {row['count']} payments, total = {row['total_amount']}")

    finally:
        await database.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
