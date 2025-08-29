#!/usr/bin/env python3
"""
admin_panel/logs_viewer.py

Async admin CLI to view & export bot logs stored in MongoDB (collection: logs).

Features:
- filter by type, user_id, action, date range
- pagination: --page, --limit
- follow mode (--follow) to tail incoming logs
- export to CSV
- output in JSON-lines or pretty table
- safe DB connect/disconnect via core.database

Usage examples:
  python logs_viewer.py --type error --limit 50
  python logs_viewer.py --user 123456 --from "2025-01-01" --to "2025-02-01" --export out.csv
  python logs_viewer.py --follow --type system
"""

import argparse
import asyncio
import logging
import os
import sys
import csv
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# project imports (ensure project root in PYTHONPATH)
import config
from core import database

# logging setup for this script
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs_viewer.log")
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH),
    ],
)
logger = logging.getLogger("admin_panel.logs_viewer")


# ----------------- helpers -----------------
def parse_iso_or_date(val: Optional[str]) -> Optional[datetime]:
    """Accept ISO datetime or plain YYYY-MM-DD and return timezone-aware UTC datetime."""
    if not val:
        return None
    try:
        # try full ISO first
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        # try YYYY-MM-DD
        try:
            dt = datetime.strptime(val, "%Y-%m-%d")
            dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            raise ValueError(f"Invalid date format: {val}. Use ISO or YYYY-MM-DD.")


def build_query(args: argparse.Namespace) -> Dict[str, Any]:
    """Construct MongoDB query dict from CLI args."""
    q: Dict[str, Any] = {}
    if args.type:
        q["type"] = args.type
    if args.user:
        # store as int in DB typically
        try:
            q["user_id"] = int(args.user)
        except Exception:
            q["user_id"] = args.user
    if args.action:
        # partial match using regex
        q["action"] = {"$regex": args.action, "$options": "i"}
    # date range
    date_query = {}
    if args.from_date:
        date_query["$gte"] = parse_iso_or_date(args.from_date)
    if args.to_date:
        # include entire day if YYYY-MM-DD used — parse already returns midnight UTC; user can provide iso
        to_dt = parse_iso_or_date(args.to_date)
        date_query["$lte"] = to_dt
    if date_query:
        q["timestamp"] = date_query
    return q


def print_table(rows: list, columns: list):
    """Simple pretty table printer (no external deps)."""
    if not rows:
        print("(no rows)")
        return
    # compute column widths
    col_widths = {c: len(c) for c in columns}
    for r in rows:
        for c in columns:
            s = str(r.get(c, ""))
            col_widths[c] = max(col_widths[c], len(s))
    # header
    hdr = " | ".join(c.ljust(col_widths[c]) for c in columns)
    sep = "-+-".join("-" * col_widths[c] for c in columns)
    print(hdr)
    print(sep)
    for r in rows:
        line = " | ".join(str(r.get(c, "")).ljust(col_widths[c]) for c in columns)
        print(line)


# ----------------- main DB functions -----------------
async def fetch_logs(
    query: Dict[str, Any],
    page: int = 1,
    limit: int = 50,
    sort_desc: bool = True,
):
    """
    Fetch logs from DB with pagination.
    Returns list of documents.
    """
    db = database.get_mongo_db()
    skip = (page - 1) * limit
    sort_order = [("timestamp", -1 if sort_desc else 1)]
    cursor = db.logs.find(query).sort(sort_order).skip(skip).limit(limit)
    docs = []
    async for doc in cursor:
        # ensure timestamp serialization
        if isinstance(doc.get("timestamp"), str):
            # keep as-is
            pass
        docs.append(doc)
    return docs


async def export_csv(docs, path: str):
    """Export list of log docs to CSV."""
    if not docs:
        logger.info("No documents to export.")
        return
    # open file
    with open(path, "w", newline="", encoding="utf-8") as f:
        # gather headers from union of keys
        keys = set()
        for d in docs:
            keys.update(d.keys())
        # prefer common order
        preferred = ["timestamp", "type", "user_id", "action", "details"]
        headers = [k for k in preferred if k in keys] + [k for k in sorted(keys) if k not in preferred]
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for d in docs:
            # convert non-serializable to JSON string
            row = {}
            for h in headers:
                val = d.get(h, "")
                if isinstance(val, (dict, list)):
                    row[h] = json.dumps(val, default=str, ensure_ascii=False)
                else:
                    row[h] = str(val) if val is not None else ""
            writer.writerow(row)
    logger.info("Exported %d logs to %s", len(docs), path)


async def tail_logs(query: Dict[str, Any], poll_interval: float = 1.5):
    """
    Tail new logs matching query. This function polls DB for new entries.
    Note: for high-volume systems use capped collection + tailable cursor.
    """
    db = database.get_mongo_db()
    last_ts = datetime.now(timezone.utc)
    try:
        while True:
            q = query.copy()
            q["timestamp"] = {"$gt": last_ts}
            cursor = db.logs.find(q).sort("timestamp", 1)
            new_count = 0
            async for doc in cursor:
                new_count += 1
                last_ts = doc.get("timestamp") or last_ts
                print(json.dumps(doc, default=str, ensure_ascii=False))
            if new_count == 0:
                await asyncio.sleep(poll_interval)
            # loop continues
    except asyncio.CancelledError:
        logger.info("Tail cancelled")
        return


# ----------------- CLI entrypoint -----------------
def build_argparser():
    p = argparse.ArgumentParser(prog="logs_viewer.py", description="View & export bot logs (admin)")
    p.add_argument("--type", help="Log type filter (e.g. error, payment, system)")
    p.add_argument("--user", help="Filter by user id")
    p.add_argument("--action", help="Filter by action substring (regex, case-insensitive)")
    p.add_argument("--from", dest="from_date", help="From date (ISO or YYYY-MM-DD)")
    p.add_argument("--to", dest="to_date", help="To date (ISO or YYYY-MM-DD)")
    p.add_argument("--page", type=int, default=1, help="Page number (1-based)")
    p.add_argument("--limit", type=int, default=50, help="Documents per page")
    p.add_argument("--follow", action="store_true", help="Tail new logs (like tail -f)")
    p.add_argument("--export", help="Export current page results to CSV file path")
    p.add_argument("--jsonl", action="store_true", help="Output in json-lines format instead of table")
    p.add_argument("--quiet", action="store_true", help="Minimal output (only JSON lines/exports)")
    return p


async def run():
    parser = build_argparser()
    args = parser.parse_args()

    # build query
    try:
        query = build_query(args)
    except ValueError as e:
        logger.error("Invalid input: %s", e)
        return

    # connect DB
    try:
        await database.connect()
    except Exception as e:
        logger.exception("DB connect failed: %s", e)
        return

    try:
        # follow mode (tailing)
        if args.follow:
            logger.info("Starting tail mode with query: %s", query)
            await tail_logs(query)
            return

        # normal fetch
        docs = await fetch_logs(query, page=args.page, limit=args.limit)
        if args.jsonl:
            for d in docs:
                print(json.dumps(d, default=str, ensure_ascii=False))
        else:
            if not args.quiet:
                # show table with selected columns
                columns = ["timestamp", "type", "user_id", "action", "details"]
                # prepare rows
                rows = []
                for d in docs:
                    # stringify details to short summary if needed
                    det = d.get("details", "")
                    if isinstance(det, (dict, list)):
                        try:
                            det_str = json.dumps(det, ensure_ascii=False)
                        except Exception:
                            det_str = str(det)
                    else:
                        det_str = str(det)
                    rows.append({
                        "timestamp": d.get("timestamp", ""),
                        "type": d.get("type", ""),
                        "user_id": d.get("user_id", ""),
                        "action": d.get("action", ""),
                        "details": det_str[:80] + ("..." if len(det_str) > 80 else "")
                    })
                print(f"Showing page {args.page} (limit {args.limit}) — matched {len(rows)} rows\n")
                print_table(rows, columns)

        # export if requested
        if args.export:
            await export_csv(docs, args.export)

    finally:
        # disconnect DB
        try:
            await database.disconnect()
        except Exception:
            logger.debug("DB disconnect failed (continuing)")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
