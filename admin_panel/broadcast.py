#!/usr/bin/env python3
"""
admin_panel/broadcast.py

Production-ready broadcast script for SmartX Assistance.

Features:
- Async sending using aiogram Bot (non-blocking)
- Safe: owner must pass --confirm with OWNER_ID or API_KEY check
- Dry-run mode to preview recipients without sending
- Preview mode to send to OWNER_ID only
- Rate-limited sending (messages/sec via batch_delay)
- Retry logic with exponential backoff per user (configurable tries)
- Logging of broadcast job to DB (db.broadcasts collection)
- Option to broadcast text or file (local path or direct URL)
- Chunked sending with backoff between chunks to avoid hitting Telegram limits

Usage examples:
  python broadcast.py --message "Hello users!" --confirm
  python broadcast.py --message-file msg.txt --dry-run
  python broadcast.py --message "Update" --media /path/to/file.mp4 --confirm --batch-size 30 --batch-delay 2

IMPORTANT:
- Make sure BOT_TOKEN available via config.BOT_TOKEN (or .env)
- Database must be reachable (core.database.connect called)
"""

import asyncio
import argparse
import logging
import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

# project imports (assumes project root in PYTHONPATH)
import config
from core import database
from core import helpers

from aiogram import Bot
from aiogram.types import InputFile, ParseMode
from aiogram.utils.exceptions import RetryAfter, Throttled, BotBlocked, ChatNotFound, TelegramAPIError

logger = logging.getLogger("admin_panel.broadcast")
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, "INFO"),
                    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s")


# ---------- helpers ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def fetch_recipients(filter_query: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[int]:
    """
    Fetch list of chat_ids (user_id) from DB.users collection matching filter_query.
    Default: all users.
    """
    db = database.get_mongo_db()
    q = filter_query or {}
    proj = {"user_id": 1}
    cursor = db.users.find(q, proj)
    if limit:
        cursor = cursor.limit(limit)
    ids = []
    async for doc in cursor:
        try:
            ids.append(int(doc["user_id"]))
        except Exception:
            continue
    return ids


async def record_broadcast(job_doc: Dict[str, Any]) -> Any:
    """
    Insert a broadcast job record into db.broadcasts and return inserted id.
    job_doc should include fields: owner_id, message, media, total_recipients, status, started_at, finished_at, result_summary
    """
    db = database.get_mongo_db()
    res = await db.broadcasts.insert_one(job_doc)
    return res.inserted_id


async def update_broadcast(job_id, patch: Dict[str, Any]):
    db = database.get_mongo_db()
    await db.broadcasts.update_one({"_id": job_id}, {"$set": patch})


async def safe_send_message(bot: Bot, chat_id: int, text: Optional[str] = None, parse_mode: Optional[str] = "HTML",
                            media: Optional[str] = None, disable_notification: bool = True) -> Dict[str, Any]:
    """
    Send a message or media to a chat_id. Return dict with result info.
    media: local filesystem path or remote URL (telegram supports remote by file_id/url)
    """
    result = {"ok": False, "error": None, "retry_after": None}
    try:
        if media:
            # If media is a local file path -> use InputFile
            if os.path.exists(media):
                inp = InputFile(media)
                # use send_document (video, audio, doc — telegram will auto-type)
                msg = await bot.send_document(chat_id=chat_id, document=inp, caption=text or "", disable_notification=disable_notification)
            else:
                # remote url: send as document via URL
                msg = await bot.send_document(chat_id=chat_id, document=media, caption=text or "", disable_notification=disable_notification)
        else:
            msg = await bot.send_message(chat_id, text or "", parse_mode=parse_mode, disable_notification=disable_notification)
        result["ok"] = True
        result["message_id"] = msg.message_id
        return result
    except RetryAfter as e:
        # Telegram asks to wait
        result["error"] = "retry_after"
        result["retry_after"] = int(e.timeout)
        logger.warning("RetryAfter for %s: wait %s sec", chat_id, e.timeout)
        return result
    except Throttled as e:
        result["error"] = "throttled"
        result["retry_after"] = getattr(e, "retry_after", 5)
        logger.warning("Throttled when sending to %s: %s", chat_id, e)
        return result
    except (BotBlocked, ChatNotFound) as e:
        result["error"] = type(e).__name__
        logger.debug("Bot blocked or chat not found: %s -> %s", chat_id, e)
        return result
    except TelegramAPIError as e:
        result["error"] = f"telegram_api_error: {e}"
        logger.exception("TelegramAPIError for %s: %s", chat_id, e)
        return result
    except Exception as e:
        result["error"] = f"unknown: {repr(e)}"
        logger.exception("Unknown send error for %s: %s", chat_id, e)
        return result


# ---------- broadcast logic ----------
async def broadcast_runner(
    *,
    message_text: Optional[str],
    media: Optional[str],
    recipients: List[int],
    bot_token: str,
    owner_id: int,
    dry_run: bool = False,
    preview: bool = False,
    batch_size: int = 50,
    batch_delay: float = 2.0,
    retries: int = 3,
    retry_backoff: float = 2.0,
    disable_notification: bool = True,
):
    """
    Core broadcast runner.
    - preview: will send only to owner_id as a test
    - dry_run: will not send, returns list of recipients only
    - batch_size/batch_delay: control sending rate
    """
    job = {
        "owner_id": owner_id,
        "message": message_text,
        "media": media,
        "total_recipients": len(recipients),
        "status": "running",
        "started_at": now_iso(),
        "finished_at": None,
        "result_summary": {},
    }

    # record job
    job_id = await record_broadcast(job)

    logger.info("Broadcast job %s started. Recipients: %d", job_id, len(recipients))

    if dry_run:
        await update_broadcast(job_id, {"status": "dry_run", "finished_at": now_iso(), "result_summary": {"recipients": len(recipients)}})
        return {"job_id": job_id, "dry_run": True, "recipients_count": len(recipients)}

    # if preview -> override recipients with owner only
    if preview:
        recipients = [owner_id]
        logger.info("Preview mode: sending only to owner %s", owner_id)

    bot = Bot(token=bot_token, parse_mode=ParseMode.HTML)

    sent = 0
    failed = 0
    blocked = 0
    skipped = 0
    errors = []

    try:
        total = len(recipients)
        # send in batches
        for i in range(0, total, batch_size):
            batch = recipients[i:i+batch_size]
            tasks = []
            for chat_id in batch:
                # send with retry logic per recipient
                async def send_with_retries(chat_id_local: int):
                    attempt = 0
                    while attempt <= retries:
                        res = await safe_send_message(bot, chat_id_local, text=message_text, media=media, disable_notification=disable_notification)
                        if res.get("ok"):
                            return {"chat_id": chat_id_local, "status": "ok", "message_id": res.get("message_id")}
                        # retry scenarios
                        if res.get("error") in ("retry_after", "throttled"):
                            wait = res.get("retry_after") or (retry_backoff ** attempt)
                            logger.info("Retrying %s after %s sec (attempt %d)", chat_id_local, wait, attempt+1)
                            await asyncio.sleep(wait)
                            attempt += 1
                            continue
                        # non-retryable
                        return {"chat_id": chat_id_local, "status": "error", "error": res.get("error")}
                    # if exhausted retries
                    return {"chat_id": chat_id_local, "status": "error", "error": "retries_exhausted"}

                tasks.append(send_with_retries(chat_id))

            # run batch concurrently
            results = await asyncio.gather(*tasks, return_exceptions=False)
            # process results
            for r in results:
                if r.get("status") == "ok":
                    sent += 1
                else:
                    failed += 1
                    err = r.get("error")
                    if err in ("BotBlocked", "ChatNotFound"):
                        blocked += 1
                    errors.append(r)
            # after each batch, wait a bit to reduce hitting limits
            logger.info("Batch %d..%d done. sent=%d failed=%d", i+1, min(i+batch_size, total), sent, failed)
            await asyncio.sleep(batch_delay)
    finally:
        # close bot properly
        try:
            await bot.session.close()
        except Exception:
            pass

    summary = {
        "sent": sent,
        "failed": failed,
        "blocked": blocked,
        "skipped": skipped,
        "errors_sample": errors[:10],
    }
    await update_broadcast(job_id, {"status": "finished", "finished_at": now_iso(), "result_summary": summary})
    logger.info("Broadcast job %s finished. summary=%s", job_id, summary)
    return {"job_id": job_id, "summary": summary}


# ---------- CLI / entrypoint ----------
def parse_args():
    p = argparse.ArgumentParser(prog="admin_panel/broadcast.py", description="SmartX Admin: Broadcast messages to users")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--message", "-m", type=str, help="Message text to broadcast (HTML allowed)")
    g.add_argument("--message-file", type=str, help="Path to text file containing message body")
    p.add_argument("--media", "-M", type=str, help="Local path or remote URL to media (document/photo/video)")
    p.add_argument("--filter", "-f", type=str, help="MongoDB JSON filter for recipients (e.g. '{\"plan\":\"premium\"}')", default="{}")
    p.add_argument("--limit", type=int, help="Limit number of recipients (for testing)", default=None)
    p.add_argument("--dry-run", action="store_true", help="Do not send, only list recipients and record job")
    p.add_argument("--preview", action="store_true", help="Send only to owner (preview)")
    p.add_argument("--batch-size", type=int, default=50, help="Batch size for concurrent sends")
    p.add_argument("--batch-delay", type=float, default=2.0, help="Seconds to wait after each batch")
    p.add_argument("--retries", type=int, default=3, help="Retries per recipient for transient errors")
    p.add_argument("--confirm", action="store_true", help="Confirm broadcast (safety flag). Required to actually send.")
    p.add_argument("--owner-check", action="store_true", help="Require interactive owner id confirmation (extra safety)")
    return p.parse_args()


async def main_async():
    args = parse_args()

    # load message text
    if args.message_file:
        if not os.path.exists(args.message_file):
            logger.error("Message file not found: %s", args.message_file)
            return
        with open(args.message_file, "r", encoding="utf-8") as f:
            message_text = f.read().strip()
    else:
        message_text = args.message

    # parse filter
    try:
        import json
        filter_q = json.loads(args.filter)
    except Exception as e:
        logger.error("Invalid JSON for --filter: %s", e)
        return

    # safety: require --confirm unless dry-run/preview
    if not args.dry_run and not args.preview and not args.confirm:
        logger.error("Broadcast not confirmed. Use --confirm to actually send (or use --dry-run/--preview).")
        return

    # optional owner interactive check
    if args.owner_check and not args.preview and not args.dry_run:
        owner_input = input(f"Type OWNER ID ({config.OWNER_ID}) to confirm: ").strip()
        if owner_input != str(config.OWNER_ID):
            logger.error("Owner confirmation mismatch. Aborting.")
            return

    # connect DB
    await database.connect()

    # fetch recipients
    recipients = await fetch_recipients(filter_q, limit=args.limit)
    logger.info("Recipients fetched: %d", len(recipients))

    # dry-run: show top 10
    if args.dry_run:
        logger.info("DRY RUN: first 10 recipients: %s", recipients[:10])
    # preview will send only to owner

    # job owner id (who triggers broadcast)
    owner_id = config.OWNER_ID or None
    if not owner_id:
        logger.warning("OWNER_ID not set in config.py. Preview and owner notifications will not work.")

    # run broadcast runner
    try:
        res = await broadcast_runner(
            message_text=message_text,
            media=args.media,
            recipients=recipients,
            bot_token=config.BOT_TOKEN,
            owner_id=owner_id,
            dry_run=args.dry_run,
            preview=args.preview,
            batch_size=args.batch_size,
            batch_delay=args.batch_delay,
            retries=args.retries,
            retry_backoff=2.0,
            disable_notification=True,
        )
        logger.info("Broadcast finished: %s", res)
    finally:
        await database.disconnect()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
