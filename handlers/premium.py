# handlers/premium.py
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from core import database
import config
import razorpay
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("smartx_bot.handlers.premium")
router = Router()

client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

@router.callback_query(lambda c: c.data == "menu_premium")
async def show_premium(cb: CallbackQuery):
    user_id = cb.from_user.id
    db = database.db
    user = await db.users.find_one({"user_id": user_id})
    expiry = user.get("expiry_date") if user else None
    text = "⭐ Premium plans:\nChoose plan to buy."
    kb = InlineKeyboardMarkup(row_width=1)
    for plan in config.PREMIUM_PLANS:
        kb.add(InlineKeyboardButton(f"{plan['plan_name']} - ₹{plan['price']} ({plan['duration_days']} days)", callback_data=f"buy_{plan['plan_name']}"))
    kb.add(InlineKeyboardButton("Manual Payment", callback_data="manual_pay"))
    await cb.message.answer(text, reply_markup=kb)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def buy_plan(cb: CallbackQuery):
    plan_name = cb.data.split("_",1)[1]
    plan = next((p for p in config.PREMIUM_PLANS if p["plan_name"]==plan_name), None)
    if not plan:
        await cb.answer("Plan not found", show_alert=True)
        return
    # Create razorpay order
    amount_paise = int(plan["price"]*100)
    receipt = f"smartx-{cb.from_user.id}-{int(datetime.utcnow().timestamp())}"
    order = client.order.create(dict(amount=amount_paise, currency="INR", receipt=receipt, payment_capture=1))
    # send order info to user with instructions (client key handled in frontend if web; here we provide payment link)
    # Razorpay doesn't provide direct immediate link; easiest: generate a payment link via Payment Links API or ask user to pay using UPI or manual.
    # We'll give a minimal flow: share order id and ask user to complete using App with order id (developer can implement frontend)
    text = f"Order created: {order['id']}\nAmount: ₹{plan['price']}\nAfter successful payment, bot will auto-activate (webhook)."
    await cb.message.answer(text)
    await cb.answer()

@router.callback_query(lambda c: c.data == "manual_pay")
async def manual_pay(cb: CallbackQuery):
    # show UPI / manual instructions
    text = "Manual Payment Instructions:\n1) Send payment to UPI: example@upi\n2) Send screenshot here with TXN id.\nOwner will verify and activate your premium."
    await cb.message.answer(text)
    await cb.answer()

@router.message()
async def handle_manual_proof(message: Message):
    # handle screenshot with caption containing txn id
    # Only accept images: save in payments collection with status pending and notify owner
    if not message.photo:
        return
    # store pending payment
    db = database.db
    payment = {
        "payment_id": f"manual-{message.from_user.id}-{int(datetime.utcnow().timestamp())}",
        "user_id": message.from_user.id,
        "amount": None,
        "currency": "INR",
        "method": "manual",
        "status": "pending",
        "plan_duration_days": None,
        "date": datetime.utcnow()
    }
    await db.payments.insert_one(payment)
    # notify owner
    owner_id = config.OWNER_ID
    await message.answer("Payment proof received. Owner will verify and activate your Premium soon.")
    if owner_id:
        await message.forward(owner_id)
        await message.bot.send_message(owner_id, f"Manual payment from user {message.from_user.id}. Use /admin to verify.")

def register(dp):
    dp.include_router(router)
