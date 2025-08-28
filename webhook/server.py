# webhook/server.py
from fastapi import FastAPI, Request, Header, HTTPException
import services.payment_service as payment_service
from core import database
from core import helpers
import logging
import json
import config
from datetime import datetime

logger = logging.getLogger("smartx_bot.webhook")
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await database.connect()
    logger.info("Webhook app connected to DB")

@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    body = await request.body()
    try:
        # optional signature verify if you set webhook secret in Razorpay dashboard
        secret = config.RAZORPAY_KEY_SECRET
        if secret and x_razorpay_signature:
            ok = payment_service.verify_signature(body, x_razorpay_signature, secret)
            if not ok:
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=400, detail="Invalid signature")
        payload = await request.json()
        event = payload.get("event")
        logger.info("Razorpay webhook event: %s", event)
        if event == "payment.captured":
            # Payment captured - fetch payment details, match order -> update DB and activate premium
            payment_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
            # fetch payment
            info = payment_service.fetch_payment(payment_id)
            # payment meta (if you stored receipt containing user_id)
            # We'll try to get receipt by fetching order id:
            order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
            # find pending payment in DB
            db = database.get_mongo_db()
            pending = await db.payments.find_one({"payment_id": order_id})
            if not pending:
                # sometimes payment id stored; try finding by payment_id
                pending = await db.payments.find_one({"payment_id": payment_id})
            if pending:
                user_id = pending.get("user_id")
                plan_days = pending.get("plan_duration_days") or config.DEFAULT_PREMIUM_DAYS
                # mark payment success
                await db.payments.update_one({"_id": pending["_id"]}, {"$set": {"status":"success", "payment_id": payment_id, "meta": info}})
                # activate premium
                await helpers.extend_user_premium(user_id, int(plan_days))
                # notify user
                try:
                    from aiogram import Bot
                    bot = Bot(token=config.BOT_TOKEN)
                    await bot.send_message(user_id, f"Payment successful! Premium activated for {plan_days} days.")
                    await bot.session.close()
                except Exception:
                    logger.debug("Failed to notify user after payment webhook.")
            else:
                logger.warning("No pending payment found for order_id=%s payment_id=%s", order_id, payment_id)
        return {"status":"ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Webhook handler error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")
