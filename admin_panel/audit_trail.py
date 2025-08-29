#!/usr/bin/env python3
"""
admin_panel/audit_trail.py

Admin CLI for audit trail management.

Collection: admin_actions (documents written by admin scripts for audit)

Features:
- filter by action, actor, target_user, date range
- pagination (--page, --limit)
- follow mode (--follow) to stream new audit entries
- export page (--export) or export all (--export-all) to CSV
- purge older than N days (--purge-days) (requires --confirm)
- JSON-lines output (--jsonl)
- logs to admin_panel/audit_trail.log
"""

import argparse
import asyncio
import logging
import os
import sys
import csv
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

# project imports
import config
from core import database

# logging
LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_trail.log")
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH)],
)
logger = logging.getLogger("admin_panel.audit_trail")


# ---------------- helpers ----------------
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
            # try YYYY-MM-DD
            dt = datetime.strptime(val, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            raise ValueError("Invalid date format. Use ISO or YYYY-MM-DD.")


def build_query(args: argparse.Namespace) -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    if args.action:
        q["action"] = {"$regex": args.action, "$options": "i"}
    if args.actor:
        try:
            q["actor"] = int(args.actor)
        except Exception:
            q["actor"] = args.actor
    if args.target:
        try:
            q["target_user"] = int(args.target)
        except Exception:
            q["target_user"] = args.target
    # date range
    date_q = {}
    if args.from_date:
        date_q["$gte"] = parse_date(args.from_date)
    if args.to_date:
        date_q["$lte"] = parse_date(args.to_date)
    if date_q:
        q["timestamp"] = date_q
    return q


def print_table(rows: List[Dict[str, Any]], columns: List[str]):
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
        line = " | ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns)
        print(line)


# ---------------- DB operations ----------------
async def fetch_audits(query: Dict[str, Any], page: int = 1, limit: int = 50, sort_desc: bool = True) -> List[Dict[str, Any]]:
    db = database.get_mongo_db()
    skip = (page - 1) * limit
    sort_order = [("timestamp", -1 if sort_desc else 1)]
    cursor = db.admin_actions.find(query).sort(sort_order).skip(skip).limit(limit)
    docs = []
    async for doc in cursor:
        docs.append(doc)
    return docs


async def count_audits(query: Dict[str, Any]) -> int:
    db = database.get_mongo_db()
    return await db.admin_actions.count_documents(query)


async def export_csv(docs: List[Dict[str, Any]], path: str):
    if not docs:
        logger.info("No records to export.")
        return
    # union keys and prefer certain order
    keys = set()
    for d in docs:
        keys.update(d.keys())
    preferred = ["timestamp", "action", "actor", "target_user", "details"]
    headers = [k for k in preferred if k in keys] + [k for k in sorted(keys) if k not in preferred]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for d in docs:
            row = {}
            for h in headers:
                v = d.get(h, "")
                if isinstance(v, (dict, list)):
                    row[h] = json.dumps(v, default=str, ensure_ascii=False)
                else:
                    row[h] = str(v) if v is not None else ""
            writer.writerow(row)
    logger.info("Exported %d audit records to %s", len(docs), path)


async def export_all_to_csv(query: Dict[str, Any], path: str, batch_size: int = 1000):
    db = database.get_mongo_db()
    cursor = db.admin_actions.find(query).sort("timestamp", 1)
    # write streamingly
    first = True
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = None
        batch = []
        async for doc in cursor:
            batch.append(doc)
            if len(batch) >= batch_size:
                if first:
                    # compute headers
                    keys = set()
                    for d in batch:
                        keys.update(d.keys())
                    preferred = ["timestamp", "action", "actor", "target_user", "details"]
                    headers = [k for k in preferred if k in keys] + [k for k in sorted(keys) if k not in preferred]
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    first = False
                for d in batch:
                    row = {}
                    for h in writer.fieldnames:
                        v = d.get(h, "")
                        if isinstance(v, (dict, list)):
                            row[h] = json.dumps(v, default=str, ensure_ascii=False)
                        else:
                            row[h] = str(v) if v is not None else ""
                    writer.writerow(row)
                batch = []
        # final flush
        if batch:
            if first:
                keys = set()
                for d in batch:
                    keys.update(d.keys())
                preferred = ["timestamp", "action", "actor", "target_user", "details"]
                headers = [k for k in preferred if k in keys] + [k for k in sorted(keys) if k not in preferred]
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
            for d in batch:
                row = {}
                for h in writer.fieldnames:
                    v = d.get(h, "")
                    if isinstance(v, (dict, list)):
                        row[h] = json.dumps(v, default=str, ensure_ascii=False)
                    else:
                        row[h] = str(v) if v is not None else ""
                writer.writerow(row)
    logger.info("Exported all matching audit records to %s", path)


async def tail_audits(query: Dict[str, Any], poll_interval: float = 1.5):
    db = database.get_mongo_db()
    last_ts = datetime.now(timezone.utc)
    logger.info("Starting tail mode from ts=%s", last_ts.isoformat())
    try:
        while True:
            q = query.copy()
            q["timestamp"] = {"$gt": last_ts}
            cursor = db.admin_actions.find(q).sort("timestamp", 1)
            found = 0
            async for doc in cursor:
                found += 1
                last_ts = doc.get("timestamp") or last_ts
                print(json.dumps(doc, default=str, ensure_ascii=False))
            if found == 0:
                await asyncio.sleep(poll_interval)
    except asyncio.CancelledError:
        logger.info("Tail cancelled")
        return


async def purge_older_than(days: int) -> int:
    """
    Delete (hard delete) records older than given days.
    Returns number deleted.
    Use with caution: require --confirm at CLI.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db = database.get_mongo_db()
    res = await db.admin_actions.delete_many({"timestamp": {"$lt": cutoff}})
    return res.deleted_count


# ---------------- CLI ----------------
def build_argparser():
    p = argparse.ArgumentParser(description="Admin: Audit Trail Viewer & Manager")
    p.add_argument("--action", help="Filter by action (regex, case-insensitive)")
    p.add_argument("--actor", help="Filter by actor id")
    p.add_argument("--target", help="Filter by target_user id")
    p.add_argument("--from", dest="from_date", help="From date (ISO or YYYY-MM-DD)")
    p.add_argument("--to", dest="to_date", help="To date (ISO or YYYY-MM-DD)")
    p.add_argument("--page", type=int, default=1, help="Page number")
    p.add_argument("--limit", type=int, default=50, help="Page size")
    p.add_argument("--follow", action="store_true", help="Tail new audit entries (polling)")
    p.add_argument("--export", help="Export current page results to CSV")
    p.add_argument("--export-all", help="Export ALL matching records to CSV (streaming)")
    p.add_argument("--export-batch", type=int, default=1000, help="Batch size for export-all")
    p.add_argument("--jsonl", action="store_true", help="Output JSON-lines")
    p.add_argument("--quiet", action="store_true", help="Minimal output")
    p.add_argument("--purge-days", type=int, help="Purge audit records older than N days (requires --confirm)")
    p.add_argument("--confirm", action="store_true", help="Confirm destructive operations (purge)")
    return p


async def run():
    parser = build_argparser()
    args = parser.parse_args()

    # build query
    try:
        query = build_query(args)
    except Exception as e:
        logger.error("Error building query: %s", e)
        return

    # connect db
    try:
        await database.connect()
    except Exception as e:
        logger.exception("DB connect failed: %s", e)
        return

    try:
        # PURGE
        if args.purge_days:
            if not args.confirm:
                logger.error("Purge is destructive. Use --confirm to proceed.")
                return
            n = args.purge_days
            logger.info("Purging records older than %d days...", n)
            deleted = await purge_older_than(n)
            logger.info("Purge complete. Deleted %d records.", deleted)
            return

        # FOLLOW / TAIL
        if args.follow:
            logger.info("Starting follow mode with query: %s", query)
            await tail_audits(query)
            return

        # normal fetch page
        docs = await fetch_audits(query, page=args.page, limit=args.limit)
        total = await count_audits(query)
        if args.jsonl:
            for d in docs:
                print(json.dumps(d, default=str, ensure_ascii=False))
        else:
            if not args.quiet:
                print(f"Showing page {args.page} (limit {args.limit}) — total matching: {total}")
            # format rows for table
            rows = []
            for d in docs:
                rows.append({
                    "timestamp": d.get("timestamp"),
                    "action": d.get("action"),
                    "actor": d.get("actor"),
                    "target_user": d.get("target_user"),
                    "details": (json.dumps(d.get("details"), ensure_ascii=False)[:80] + ("..." if d.get("details") and len(json.dumps(d.get("details"))) > 80 else "")) if d.get("details") else ""
                })
            cols = ["timestamp", "action", "actor", "target_user", "details"]
            if not args.jsonl and not args.quiet:
                print_table(rows, cols)

        # export current page
        if args.export:
            await export_csv(docs, args.export)

        # export all matching
        if args.export_all:
            logger.info("Streaming export-all to %s (batch %d)...", args.export_all, args.export_batch)
            await export_all_to_csv(query, args.export_all, batch_size=args.export_batch)

    finally:
        try:
            await database.disconnect()
        except Exception:
            logger.debug("DB disconnect error (continuing)")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
