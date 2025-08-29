#!/usr/bin/env python3
"""
scripts/log_shipper.py

Tail local log file(s) and write structured entries into MongoDB collection `logs`.

Use-cases:
- Centralize logs into DB for admin_panel/logs_viewer and analytics
- Add fields: type (info/error/payment/usage), timestamp, raw_line, parsed (if JSON)

Run as:
  python scripts/log_shipper.py --file logs/bot.log --type bot --follow
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
import re
import json
from datetime import datetime, timezone

import config
from core import database

DEFAULT_COLLECTION = "logs"

def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help="Path to log file")
    p.add_argument("--type", required=True, help="Type tag for log entries (bot/errors/payments/usage)")
    p.add_argument("--follow", action="store_true", help="Follow mode (tail -f)")
    p.add_argument("--batch-interval", type=float, default=2.0, help="Batch flush interval seconds")
    return p

async def tail_and_ship(path: Path, type_tag: str, follow: bool = True, batch_interval: float = 2.0):
    await database.connect()
    db = database.get_mongo_db()
    batch = []
    def flush():
        nonlocal batch
        if not batch:
            return
        try:
            db[DEFAULT_COLLECTION].insert_many(batch)
        except Exception:
            # as this function may run in event loop, spike on exception but continue
            pass
        batch = []

    # open file and optionally seek to end
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        if follow:
            fh.seek(0, os.SEEK_END)
        try:
            while True:
                line = fh.readline()
                if not line:
                    # flush batch periodically
                    if batch:
                        flush()
                    if not follow:
                        break
                    await asyncio.sleep(batch_interval)
                    continue
                # try to parse timestamp if present at start e.g., "2025-08-..."
                ts = None
                m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
                if m:
                    try:
                        ts = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
                    except Exception:
                        ts = datetime.utcnow().replace(tzinfo=timezone.utc)
                else:
                    ts = datetime.utcnow().replace(tzinfo=timezone.utc)
                entry = {
                    "timestamp": ts,
                    "type": type_tag,
                    "raw": line.strip(),
                }
                # if line is JSON-like, try to decode and attach
                try:
                    if (line.lstrip().startswith("{") and line.rstrip().endswith("}")) or line.lstrip().startswith("["):
                        entry["parsed"] = json.loads(line)
                except Exception:
                    entry["parsed_error"] = True
                batch.append(entry)
                # flush if batched big
                if len(batch) >= 100:
                    flush()
        except asyncio.CancelledError:
            flush()
        finally:
            flush()
            await database.disconnect()

async def main():
    args = build_parser().parse_args()
    path = Path(args.file)
    if not path.exists():
        print("File not found:", path)
        return
    await tail_and_ship(path, args.type, follow=args.follow, batch_interval=args.batch_interval)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
