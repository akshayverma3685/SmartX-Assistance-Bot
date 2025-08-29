# webhook/server.py
"""
Webhook server for SmartX Assistance

Endpoints:
- POST /telegram/update           -- Telegram webhook receiver (expects X-Telegram-Bot-Api-Secret-Token if configured)
- POST /razorpay/webhook          -- Razorpay webhook receiver (verifies signature)
- GET  /health                    -- Basic healthcheck
- GET  /metrics                   -- Expose prometheus metrics if enabled (optional)

Notes:
- Telegram updates are stored in DB and a Celery task is enqueued for processing. This keeps webhook fast.
- Razorpay webhook is verified using HMAC (core.security.verify_hmac_signature).
- DB collections used: telegram_updates, payments
- Requires env vars: BOT_TOKEN, RAZORPAY_KEY_SECRET (for verification), TELEGRAM_WEBHOOK_SECRET (optional),
  ADMIN_API_KEY (optional for protected endpoints), etc.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, Header, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
import httpx

import config
from core import database, security
from core.logs import log_info, log_error, log_payment
from worker.tasks import download_upload_notify  # example of Celery task import for worker processing
from core.cache import get_redis  # optionally publish to redis
from services.s3_service import generate_presigned_url

logger = logging.getLogger("webhook.server")
app = FastAPI(title="SmartX Webhook Server")

# Configs (env or config)
TELEGRAM_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", getattr(config, "TELEGRAM_WEBHOOK_SECRET", None))
BOT_TOKEN = os.getenv("BOT_TOKEN", getattr(config, "BOT_TOKEN", None))
RAZORPAY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", getattr(config, "RAZORPAY_KEY_SECRET", None))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", getattr(config, "ADMIN_API_KEY", None))

# Helper to notify via Telegram HTTP API (sync, short)
TELEGRAM_API_URL = "https://api.telegram.org"

async def notify_user_via_http(chat_id: int, text: str):
    """Send message via Telegram HTTP API (used in background)."""
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not configured; cannot notify user")
        return False
    url = f"{TELEGRAM_API_URL}/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": text})
            r.raise_for_status()
            return True
    except Exception as e:
        logger.exception("Failed to notify user via Telegram HTTP API: %s", e)
        return False

# Minimal pydantic model for Razorpay payload typing (we'll parse generically)
class RazorpayEvent(BaseModel):
    entity: dict
    event: str

# ---------------------------
# Startup / Shutdown events
# ---------------------------
@app.on_event("startup")
async def startup():
    # connect to database
    try:
        await database.connect()
        log_info("Webhook server startup", source="webhook.startup")
    except Exception as e:
        logger.exception("DB connect on startup failed: %s", e)
        raise

@app.on_event("shutdown")
async def shutdown():
    try:
        await database.disconnect()
    except Exception:
        logger.exception("DB disconnect error")
    log_info("Webhook server shutdown", source="webhook.shutdown")


# ---------------------------
# Helpers
# ---------------------------
def _verify_telegram_secret(headers: Dict[str, str]) -> bool:
    """
    Telegram sends header 'X-Telegram-Bot-Api-Secret-Token' if you set secret when setting webhook.
    We verify if TELEGRAM_SECRET is configured.
    """
    if not TELEGRAM_SECRET:
        # no verification configured
        return True
    token = headers.get("x-telegram-bot-api-secret-token") or headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not token:
        logger.warning("Telegram webhook missing secret token header")
        return False
    return security.is_valid_admin_apikey(token) if False else (token == TELEGRAM_SECRET)  # simple compare

async def _store_telegram_update(update_json: dict) -> Any:
    """
    Write incoming Telegram update to DB collection 'telegram_updates'.
    Returns inserted id.
    """
    try:
        db = database.get_mongo_db()
        res = await db.telegram_updates.insert_one({"update": update_json, "received_at": __now_iso(), "processed": False})
        return res.inserted_id
    except Exception:
        logger.exception("Failed to insert telegram update into DB")
        return None

def __now_iso():
    from datetime import datetime, timezone
    return datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

# ---------------------------
# Telegram webhook endpoint
# ---------------------------
@app.post("/telegram/update", status_code=200)
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks, x_telegram_secret_token: Optional[str] = Header(None)):
    """
    Receives Telegram updates. Configure your webhook with:
      setWebhook(URL + '/telegram/update', secret_token=TELEGRAM_WEBHOOK_SECRET)
    """
    try:
        # verify secret token (if configured)
        headers = {k.lower(): v for k, v in request.headers.items()}
        if TELEGRAM_SECRET:
            token_ok = _verify_telegram_secret(headers)
            if not token_ok:
                log_error("Invalid telegram webhook secret", source="webhook.telegram", meta={"ip": request.client.host})
                raise HTTPException(status_code=403, detail="Invalid webhook secret")

        # read body quickly
        raw = await request.body()
        if not raw:
            return PlainTextResponse("empty", status_code=400)
        try:
            update_json = await request.json()
        except Exception:
            # fallback parse
            update_json = json.loads(raw.decode("utf-8", errors="ignore"))

        # store update to DB
        inserted_id = await _store_telegram_update(update_json)
        log_info("Telegram update received", source="webhook.telegram", meta={"_id": str(inserted_id)})

        # enqueue background Celery task to process update (non-blocking)
        # Worker should implement task 'process_telegram_update' to pop & handle DB updates, or accept raw update
        try:
            # Prefer sending DB id to worker for reliable processing
            from worker.celery_app import celery_app  # ensure celery loaded
            # call a task named 'worker.tasks.process_telegram_update' if it exists
            # to keep decoupling, we try to call by import; fallback to publishing on redis if needed
            try:
                from worker.tasks import process_telegram_update
                # schedule with DB id
                process_telegram_update.delay(str(inserted_id))
            except Exception:
                # fallback: push raw update to Redis channel for workers
                try:
                    r = await get_redis()
                    await r.publish("telegram_updates", raw.decode("utf-8", errors="ignore"))
                except Exception:
                    logger.exception("Failed to publish telegram update to redis fallback")
        except Exception:
            logger.exception("Failed to enqueue telegram update for background processing")

        return JSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in telegram_webhook: %s", e)
        # still return 200 to avoid repeated webhook retries? Better to return 200 after logging.
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=200)


# ---------------------------
# Razorpay webhook endpoint
# ---------------------------
@app.post("/razorpay/webhook", status_code=200)
async def razorpay_webhook(request: Request, background_tasks: BackgroundTasks, x_razorpay_signature: Optional[str] = Header(None)):
    """
    Razorpay will POST events here.
    Verify signature using RAZORPAY_SECRET and header 'X-Razorpay-Signature'.
    """
    try:
        body_bytes = await request.body()
        signature = x_razorpay_signature or request.headers.get("X-Razorpay-Signature")
        if not RAZORPAY_SECRET:
            log_error("Razorpay secret not configured", source="webhook.razorpay")
            raise HTTPException(status_code=500, detail="Razorpay secret not configured")

        # verify signature
        ok = security.verify_hmac_signature(RAZORPAY_SECRET, body_bytes, signature, algo="sha256")
        if not ok:
            log_error("Razorpay signature verification failed", source="webhook.razorpay", meta={"sig": signature})
            raise HTTPException(status_code=403, detail="Invalid signature")

        # parse event
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        event = payload.get("event") or payload.get("payload", {}).get("event", None)
        # store raw webhook to payments collection for audit
        try:
            db = database.get_mongo_db()
            audit_doc = {"raw": payload, "received_at": __now_iso()}
            await db.razorpay_webhooks.insert_one(audit_doc)
        except Exception:
            logger.exception("Failed to store razorpay webhook audit")

        # handle known events
        # example: payment.captured or payment.failed
        event_type = payload.get("event") or ""
        log_info("Razorpay webhook received", source="webhook.razorpay", meta={"event": event_type})

        # process in background to return quickly
        background_tasks.add_task(_process_razorpay_event, payload)
        return JSONResponse({"ok": True})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in razorpay_webhook: %s", e)
        return JSONResponse({"ok": False, "error": "server_error"}, status_code=200)


async def _process_razorpay_event(payload: Dict[str, Any]):
    """
    Background processor for Razorpay events.
    - Extract payment info
    - Update payments collection
    - Activate premium if applicable (based on metadata -> user_id)
    - Notify user via Telegram HTTP API
    """
    try:
        db = database.get_mongo_db()
        # payload structure: { "entity": {...}, "event": "payment.captured", ... } or { "payload": {"payment": {"entity": {...}}}}
        # try to support common variants
        event = payload.get("event") or ""
        entity = None
        if "payload" in payload:
            # drill down
            # look for payment entity
            payload_obj = payload.get("payload", {})
            # flatten: may contain 'payment', 'order', etc.
            for key in ("payment", "order", "invoice"):
                if key in payload_obj and payload_obj[key] and isinstance(payload_obj[key], dict):
                    entity = payload_obj[key].get("entity") or payload_obj[key]
                    break
        if entity is None:
            entity = payload.get("entity") or payload.get("payload", {}).get("payment", {}).get("entity", None)

        if not entity:
            log_error("Razorpay payload missing entity", source="webhook.razorpay", meta={"payload": payload})
            return

        # Typical payment fields
        payment_id = entity.get("id") or entity.get("payment_id") or entity.get("order_id")
        order_id = entity.get("order_id")
        amount = entity.get("amount") or entity.get("amount_paid") or entity.get("amount_paid")
        # Razorpay amount is in paise (INR*100)
        try:
            amount_value = int(amount) / 100.0 if amount is not None else None
        except Exception:
            amount_value = None

        # user mapping: try metadata -> entity['notes'] or entity['metadata']
        user_id = None
        notes = entity.get("notes") or entity.get("metadata") or {}
        # common pattern: notes.user_id or metadata.user_id
        if isinstance(notes, dict):
            user_id = notes.get("user_id") or notes.get("uid") or notes.get("telegram_id")
        # if still string numeric -> int
        try:
            if user_id:
                user_id = int(user_id)
        except Exception:
            user_id = None

        # save to payments collection
        payment_doc = {
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": amount_value,
            "currency": entity.get("currency", "INR"),
            "status": "captured" if "captured" in (event or "") or entity.get("status") == "captured" else entity.get("status", "unknown"),
            "raw": entity,
            "received_at": __now_iso(),
            "source_event": event,
            "user_id": user_id,
        }

        try:
            await db.payments.insert_one(payment_doc)
            log_payment("Razorpay payment recorded", user_id=user_id, source="webhook.razorpay", meta={"payment_id": payment_id, "amount": amount_value})
        except Exception:
            logger.exception("Failed to insert payment record")

        # business logic: if captured and user_id present -> activate premium
        status_lower = (payment_doc.get("status") or "").lower()
        if status_lower in ("captured", "paid", "successful"):
            if user_id:
                # mark user's plan premium and set expiry (e.g., using settings or fixed days)
                try:
                    # fetch settings for premium days
                    settings_doc = await db.settings.find_one({"_id": "global"}) or {}
                    premium_days = settings_doc.get("values", {}).get("free_trial_days") or getattr(config, "FREE_TRIAL_DAYS", None)
                    # default: set premium for a configured number of days (or use explicit metadata)
                    # here we simply set to premium for 365 days if not configured — adapt as needed
                    import datetime
                    from core import helpers
                    days = notes.get("premium_days") or premium_days or getattr(config, "PREMIUM_DEFAULT_DAYS", 365)
                    try:
                        days = int(days)
                    except Exception:
                        days = int(days) if isinstance(days, int) else 365
                    # use helper to set user plan (helpers.set_user_plan or extend_user_premium)
                    # prefer extend_user_premium if exists
                    if hasattr(helpers, "extend_user_premium"):
                        await helpers.extend_user_premium(user_id, days)
                    elif hasattr(helpers, "set_user_plan"):
                        await helpers.set_user_plan(user_id, "premium", expiry_days=days)
                    # notify user
                    text = f"💳 Payment received! Your premium has been activated for {days} days."
                    await notify_user_via_http(user_id, text)
                except Exception:
                    logger.exception("Failed to activate premium after payment")
        else:
            # not captured (failed) -> notify admin or user optionally
            if user_id:
                await notify_user_via_http(user_id, f"Payment status: {payment_doc.get('status')}. If this is unexpected contact support.")
    except Exception:
        logger.exception("Error processing Razorpay event")

# ---------------------------
# Health & metrics endpoints
# ---------------------------
@app.get("/health")
async def health():
    try:
        # quick DB ping
        db = database.get_mongo_db()
        # simple command to check server
        await db.command({"ping": 1})
        return {"ok": True, "db": "ok"}
    except Exception as e:
        logger.exception("Healthcheck DB failed: %s", e)
        return JSONResponse({"ok": False, "db": "error"}, status_code=500)

@app.get("/metrics")
async def metrics():
    # if you integrated prometheus earlier, you can expose metrics here (monitoring.metrics.metrics_response)
    try:
        from monitoring.metrics import PROMETHEUS_ENABLED, metrics_response
        if not PROMETHEUS_ENABLED:
            raise RuntimeError("Metrics disabled")
        from fastapi import Response
        return Response(metrics_response(), media_type="text/plain; version=0.0.4")
    except Exception:
        return JSONResponse({"ok": False, "error": "metrics_unavailable"}, status_code=404)


# ---------------------------
# Run with: uvicorn webhook.server:app --host 0.0.0.0 --port 8080
# ---------------------------
