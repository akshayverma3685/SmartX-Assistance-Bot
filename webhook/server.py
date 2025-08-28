# webhook/server.py
from fastapi import FastAPI, Request, Header, HTTPException
import services.payment_service as payment_service
from core import database, helpers
import logging
import config
from datetime import datetime

logger = logging.getLogger("smartx_bot.webhook")
app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()
    logger.info("Webhook service connected to DB")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
    logger.info("Webhook service disconnected from DB")

@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: str = Header(None)):
    body = await request.body()
    try:
        if config.RAZORPAY_KEY_SECRET and x_razorpay_signature:
            ok = payment_service.verify_signature(body, x_razorpay_signature, config.RAZORPAY_KEY_SECRET)
            if not ok:
                logger.warning("Invalid Razorpay webhook signature")
                raise HTTPException(status_code=400, detail="Invalid signature")

        payload = await request.json()
        event = payload.get("event")
        logger.info("Razorpay webhook event received: %s", event)

        if event == "payment.captured":
            # Extract payment and order info
            payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            payment_id = payment_entity.get("id")
            order_id = payment_entity.get("order_id")
            amount = payment_entity.get("amount")  # in paise

            db = database.get_mongo_db()
            # Try to find pending by order_id first, then by payment_id
            pending = None
            if order_id:
                pending = await db.payments.find_one({"payment_id": order_id})
            if not pending:
                pending = await db.payments.find_one({"payment_id": payment_id})
            if pending:
                user_id = pending.get("user_id")
                plan_days = pending.get("plan_duration_days") or config.DEFAULT_PREMIUM_DAYS
                # update payment doc
                await db.payments.update_one({"_id": pending["_id"]}, {"$set": {"status": "success", "payment_id": payment_id, "meta": payment_entity}})
                # activate premium
                await helpers.extend_user_premium(user_id, int(plan_days))
                # notify user
                try:
                    from aiogram import Bot
                    bot = Bot(token=config.BOT_TOKEN)
                    await bot.send_message(user_id, f"Payment received — Premium active for {plan_days} days. Thanks!")
                    await bot.session.close()
                except Exception:
                    logger.debug("Failed to notify user after webhook")
            else:
                logger.warning("No matching pending payment found for order_id=%s payment_id=%s", order_id, payment_id)

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing Razorpay webhook: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")
