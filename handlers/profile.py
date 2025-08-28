# handlers/profile.py
from aiogram import Router
from aiogram.types import Message
from core import database
import config
import json, os
from datetime import datetime
router = Router()
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALES_DIR = os.path.join(BASE_DIR, "locales")

def load_locale(lang):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.message(commands=["profile"])
async def cmd_profile(message: Message):
    db = database.db
    user = await db.users.find_one({"user_id": message.from_user.id})
    if not user:
        await message.reply("No profile found. Use /start first.")
        return
    lang = user.get("language","en")
    texts = load_locale(lang)
    expiry = user.get("expiry_date") or "N/A"
    text = f"ID: {user['user_id']}\nUsername: @{user.get('username')}\nPlan: {user.get('plan')}\nExpiry: {expiry}\nReferrals: {user.get('referrals')}\nCommands used: {user.get('commands_used',0)}"
    await message.reply(text)

def register(dp):
    dp.include_router(router)
