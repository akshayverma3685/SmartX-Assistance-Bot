# handlers/profile.py
import os
import json
import logging
from aiogram import Router
from aiogram.types import Message
from core import database, helpers
import config

logger = logging.getLogger("smartx_bot.handlers.profile")
router = Router()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALES_DIR = os.path.join(BASE_DIR, "locales")


def load_locale(lang: str):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.message(commands=["profile"])
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    user = await database.find_user(user_id)
    if not user:
        await message.reply("No profile found. Use /start first.")
        return
    lang = user.get("language", config.DEFAULT_LANGUAGE)
    texts = load_locale(lang)
    expiry = user.get("expiry_date") or "N/A"
    # format expiry
    try:
        expiry_fmt = helpers.format_expiry_for_display(expiry)
    except Exception:
        expiry_fmt = str(expiry)
    text = (
        f"ID: {user['user_id']}\n"
        f"Username: @{user.get('username')}\n"
        f"Plan: {user.get('plan')}\n"
        f"Expiry: {expiry_fmt}\n"
        f"Referrals: {user.get('referrals')}\n"
        f"Commands used: {user.get('commands_used', 0)}"
    )
    await message.reply(text)


def register(dp):
    dp.include_router(router)
