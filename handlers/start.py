# handlers/start.py
import os
import json
import logging
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from core import database
from core import helpers
import config

logger = logging.getLogger("smartx_bot.handlers.start")
router = Router()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALES_DIR = os.path.join(BASE_DIR, "locales")


def load_locale(lang: str):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.message(commands=["start"])
async def cmd_start(message: Message):
    """
    /start handler:
    - ensures user record
    - gives FREE trial if first time (config.FREE_TRIAL_DAYS)
    - shows language select + open menu
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        # ensure record exists
        user = await helpers.ensure_user_record(user_id, username=username)
        # if first time and trial not used -> grant trial
        if not user.get("trial_used", False):
            days = int(getattr(config, "FREE_TRIAL_DAYS", 3))
            await helpers.extend_user_premium(user_id, days)
            # mark trial_used true
            if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
                db = database.get_mongo_db()
                await db.users.update_one({"user_id": user_id}, {"$set": {"trial_used": True}})
            else:
                user["trial_used"] = True
                await database.create_or_update_user(user)
            lang = user.get("language", config.DEFAULT_LANGUAGE)
            texts = load_locale(lang)
            text = texts.get("welcome", "Welcome!").format(days=days)
        else:
            lang = user.get("language", config.DEFAULT_LANGUAGE)
            texts = load_locale(lang)
            text = texts.get("start_help", "Use commands from menu.")

        # language buttons + open menu
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
            InlineKeyboardButton("🇮🇳 हिंदी", callback_data="setlang_hi"),
        )
        kb.add(InlineKeyboardButton("Open Menu", callback_data="open_menu"))
        await message.answer(text, reply_markup=kb)
    except Exception as e:
        logger.exception("Error in /start: %s", e)
        await message.reply("Kuch error hogaya. Try /start again.")


@router.callback_query(lambda c: c.data and c.data.startswith("setlang_"))
async def cb_setlang(cb: CallbackQuery):
    lang = cb.data.split("_", 1)[1]
    user_id = cb.from_user.id
    try:
        # update DB
        if getattr(config, "DB_TYPE", "mongo").lower() == "mongo":
            db = database.get_mongo_db()
            await db.users.update_one({"user_id": user_id}, {"$set": {"language": lang}})
        else:
            user = await database.find_user(user_id) or {}
            user["language"] = lang
            await database.create_or_update_user(user)
        await cb.answer("Language set ✅")
        # show main menu
        from handlers.menu import show_main_menu
        # call show_main_menu with message object
        await show_main_menu(cb.message, lang=lang)
    except Exception as e:
        logger.exception("setlang error: %s", e)
        await cb.answer("Failed to set language", show_alert=True)


def register(dp):
    dp.include_router(router)
