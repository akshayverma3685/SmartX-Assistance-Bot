# handlers/start.py
from aiogram import Router, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import F
from core import database
from models.user_model import UserModel
import config
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger("smartx_bot.handlers.start")
router = Router()

# load locales
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALES_DIR = os.path.join(BASE_DIR, "locales")
def load_locale(lang):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.message(commands=["start"])
async def cmd_start(message: Message):
    user_id = message.from_user.id
    # check user exists
    db = database.db
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        # create user and give trial
        trial_days = config.FREE_TRIAL_DAYS
        expiry = datetime.utcnow() + timedelta(days=trial_days)
        user_doc = {
            "user_id": user_id,
            "username": message.from_user.username,
            "plan": "premium",
            "expiry_date": expiry,
            "trial_used": True,
            "joined_date": datetime.utcnow(),
            "referrals": 0,
            "commands_used": 0,
            "language": config.LANG_DEFAULT
        }
        await db.users.insert_one(user_doc)
        lang_strings = load_locale(user_doc["language"])
        text = lang_strings["welcome"].format(days=trial_days)
    else:
        lang_strings = load_locale(user.get("language", config.LANG_DEFAULT))
        if user.get("plan") == "premium":
            expiry = user.get("expiry_date")
            text = lang_strings["premium_active"].format(expiry=expiry)
        else:
            text = lang_strings["welcome"].format(days=0) if "welcome" in lang_strings else "Welcome"

    # language choose buttons
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
           InlineKeyboardButton("🇮🇳 हिंदी", callback_data="setlang_hi"))
    kb.add(InlineKeyboardButton("Open Menu", callback_data="open_menu"))
    await message.answer(text, reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("setlang_"))
async def set_language(cb: CallbackQuery):
    lang = cb.data.split("_",1)[1]
    user_id = cb.from_user.id
    db = database.db
    await db.users.update_one({"user_id": user_id}, {"$set": {"language": lang}}, upsert=True)
    # respond
    from handlers.menu import show_main_menu
    await cb.answer("Language set!")
    # call main menu
    await show_main_menu(cb.message or cb.inline_message_id, lang=lang)

# export register function to be used by bot.py dynamic loader
def register(dp):
    dp.include_router(router)
