# handlers/admin.py
import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from core import database, helpers
from core.middleware import owner_only
from datetime import datetime

logger = logging.getLogger("smartx_bot.handlers.admin")
router = Router()


@router.message(commands=["admin"])
@owner_only
async def cmd_admin(message: Message):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Users", callback_data="admin_users"),
           InlineKeyboardButton("Payments", callback_data="admin_payments"))
    kb.add(InlineKeyboardButton("Broadcast", callback_data="admin_broadcast"),
           InlineKeyboardButton("Stats", callback_data="admin_stats"))
    await message.reply("Admin Panel:", reply_markup=kb)


@router.callback_query(lambda c: c.data == "admin_users")
@owner_only
async def cb_admin_users(cb: CallbackQuery):
    db = database.get_mongo_db() if getattr(config, "DB_TYPE", "mongo") == "mongo" else None
    total = await db.users.count_documents({}) if db else "n/a"
    premium = await db.users.count_documents({"plan": "premium"}) if db else "n/a"
    await cb.message.answer(f"Total users: {total}\nPremium users: {premium}")
    await cb.answer()


@router.callback_query(lambda c: c.data == "admin_payments")
@owner_only
async def cb_admin_payments(cb: CallbackQuery):
    db = database.get_mongo_db()
    res = db.payments.find().sort("date", -1).limit(20)
    text_lines = ["Recent Payments:"]
    async for p in res:
        text_lines.append(f"{p.get('payment_id')} | {p.get('status')} | {p.get('user_id')} | ₹{p.get('amount')}")
    await cb.message.answer("\n".join(text_lines))
    await cb.answer()


@router.callback_query(lambda c: c.data == "admin_broadcast")
@owner_only
async def cb_admin_broadcast(cb: CallbackQuery):
    await cb.message.answer("Send the broadcast message text now (it will be sent to all users).")
    await cb.answer()


@router.message()
@owner_only
async def handle_admin_broadcast(message: Message):
    # expects owner to send text to broadcast after clicking broadcast
    if not message.text:
        await message.reply("Please send text to broadcast.")
        return
    db = database.get_mongo_db()
    cursor = db.users.find({}, {"user_id": 1})
    count = 0
    async for u in cursor:
        try:
            await message.bot.send_message(u["user_id"], message.text)
            count += 1
        except Exception:
            continue
    await message.reply(f"Broadcast sent to approx {count} users.")


def register(dp):
    dp.include_router(router)
