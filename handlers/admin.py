# handlers/admin.py
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from core import database
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("smartx_bot.handlers.admin")
router = Router()

def owner_only(func):
    async def wrapper(event, data):
        user_id = None
        if hasattr(event, "from_user"):
            user_id = event.from_user.id
        if user_id != config.OWNER_ID:
            try:
                await event.answer("Unauthorized", show_alert=True)
            except:
                pass
            return
        return await func(event, data)
    return wrapper

@router.message(commands=["admin"])
async def cmd_admin(message: Message):
    if message.from_user.id != config.OWNER_ID:
        await message.reply("Unauthorized")
        return
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Users", callback_data="admin_users"),
           InlineKeyboardButton("Payments", callback_data="admin_payments"))
    kb.add(InlineKeyboardButton("Broadcast", callback_data="admin_broadcast"),
           InlineKeyboardButton("Stats", callback_data="admin_stats"))
    await message.reply("Admin Panel:", reply_markup=kb)

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(cb: CallbackQuery):
    if cb.from_user.id != config.OWNER_ID:
        await cb.answer("Unauthorized", show_alert=True)
        return
    # show summary
    db = database.db
    total = await db.users.count_documents({})
    premium = await db.users.count_documents({"plan":"premium"})
    await cb.message.answer(f"Total users: {total}\nPremium users: {premium}")
    await cb.answer()

@router.callback_query(lambda c: c.data == "admin_payments")
async def admin_payments(cb: CallbackQuery):
    if cb.from_user.id != config.OWNER_ID:
        await cb.answer("Unauthorized", show_alert=True)
        return
    db = database.db
    recent = db.payments.find().sort("date",-1).limit(10)
    text = "Recent Payments:\n"
    async for p in recent:
        text += f"{p.get('payment_id')} - {p.get('status')} - {p.get('user_id')}\n"
    await cb.message.answer(text)
    await cb.answer()

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(cb: CallbackQuery):
    if cb.from_user.id != config.OWNER_ID:
        await cb.answer("Unauthorized", show_alert=True)
        return
    await cb.message.answer("Send the broadcast message now (text only).")
    await cb.answer()

@router.message()
async def handle_broadcast(message: Message):
    # This will receive the message after admin clicked broadcast
    if message.from_user.id != config.OWNER_ID:
        return
    text = message.text
    db = database.db
    cursor = db.users.find({}, {"user_id":1})
    count = 0
    async for u in cursor:
        try:
            await message.bot.send_message(u["user_id"], text)
            count += 1
        except Exception:
            continue
    await message.reply(f"Broadcast sent to approx {count} users.")

def register(dp):
    dp.include_router(router)
