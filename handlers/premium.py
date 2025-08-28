# handlers/premium.py
import logging
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from core import database
from core import helpers
import services.payment_service as payment_service
import config
from datetime import datetime

logger = logging.getLogger("smartx_bot.handlers.premium")
router = Router()

# show premium menu
@router.callback_query(lambda c: c.data == "menu_premium")
async def cb_menu_premium(cb: CallbackQuery):
    user_id = cb.from_user.id
    user = await database.find_user(user_id)
    lang = user.get("language", config.DEFAULT_LANGUAGE) if user else config.DEFAULT_LANGUAGE
    # load minimal locale
    import json, os
    base_dir = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base_dir, "locales", f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(base_dir, "locales", "en.json")
    texts = json.load(open(path, "r", encoding="utf-8"))
    text = texts.get("premium_info", "Premium plans")
    kb = InlineKeyboardMarkup(row_width=1)
    for plan in config.PREMIUM_PLANS:
        kb.add(InlineKeyboardButton(f"{plan['plan_name']} — ₹{plan['price']} ({plan['duration_days']}d)", callback_data=f"buy_{plan['plan_name']}"))
    kb.add(InlineKeyboardButton("Manual Payment", callback_data="manual_pay"))
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def cb_buy_plan(cb: CallbackQuery):
    plan_name = cb.data.split("_", 1)[1]
    plan = next((p for p in config.PREMIUM_PLANS if p["plan_name"] == plan_name), None)
    if not plan:
        await cb.answer("Plan not found", show_alert=True)
        return
    # create order via payment_service (razorpay wrapper)
    try:
        receipt = f"smartx_{cb.from_user.id}_{int(datetime.utcnow().timestamp())}"
        order = payment_service.create_order(plan["price"], receipt)
        # send order id and instructions
        text = f"Order created: {order.get('id')}\nAmount: ₹{plan['price']}\nComplete payment via Razorpay checkout (if integrated) or send manual payment proof."
        await cb.message.answer(text)
        # persist pending order in payments collection
        payment_doc = {
            "payment_id": order.get("id"),
            "user_id": cb.from_user.id,
            "amount": plan["price"],
            "currency": "INR",
            "method": "razorpay",
            "status": "created",
            "plan_duration_days": plan["duration_days"],
            "date": datetime.utcnow()
        }
        await database.add_payment(payment_doc)
        await cb.answer()
    except Exception as e:
        logger.exception("Error creating order: %s", e)
        await cb.answer("Payment failed to initialize", show_alert=True)


@router.callback_query(lambda c: c.data == "manual_pay")
async def cb_manual_pay(cb: CallbackQuery):
    text = f"Manual Payment Instructions:\nSend UPI to: {config.MANUAL_PAYMENT_UPI}\nAfter payment, send screenshot here with transaction id."
    await cb.message.answer(text)
    await cb.answer()


@router.message()
async def handle_manual_screenshots(message: Message):
    """
    Accept payment screenshot and mark payment pending for owner to verify.
    Only treat messages with photo as manual proof.
    """
    if not message.photo:
        return
    try:
        # save payment record
        pid = f"manual-{message.from_user.id}-{int(datetime.utcnow().timestamp())}"
        payment_doc = {
            "payment_id": pid,
            "user_id": message.from_user.id,
            "amount": None,
            "currency": "INR",
            "method": "manual",
            "status": "pending",
            "meta": {"caption": message.caption or None},
            "date": datetime.utcnow()
        }
        await database.add_payment(payment_doc)
        # forward image to owner + notify
        owner = getattr(config, "OWNER_ID", None)
        await message.answer("Payment proof received. Owner will verify and activate your Premium soon.")
        if owner:
            await message.forward(owner)
            await message.bot.send_message(owner, f"Manual payment proof from {message.from_user.id}. Use admin to verify.")
    except Exception as e:
        logger.exception("manual proof handling failed: %s", e)
        await message.reply("Failed to register payment proof. Try again later.")


# webhook endpoint integration note:
# Razorpay webhooks should call a FastAPI endpoint (not part of aiogram).
# But when webhook confirms payment, call helpers.extend_user_premium(user_id, plan_days) and update payment status.


def register(dp):
    dp.include_router(router)
