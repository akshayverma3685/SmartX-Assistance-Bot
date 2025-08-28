# handlers/menu.py
import os
import json
import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from keyboards.main_menu import main_menu_kb
from core import database
import config

logger = logging.getLogger("smartx_bot.handlers.menu")
router = Router()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALES_DIR = os.path.join(BASE_DIR, "locales")


def load_locale(lang: str):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def show_main_menu(msg_obj, lang: str = None):
    """
    Re-usable function to show main menu. msg_obj is message object.
    """
    user_id = msg_obj.from_user.id
    db = database.get_mongo_db() if getattr(config, "DB_TYPE", "mongo") == "mongo" else None
    user = await database.find_user(user_id)
    lang = lang or (user.get("language") if user else config.DEFAULT_LANGUAGE)
    texts = load_locale(lang)
    kb = main_menu_kb({
        "menu_ai": texts.get("menu_ai", "AI Assistant"),
        "menu_downloader": texts.get("menu_downloader", "Downloader"),
        "menu_tools": texts.get("menu_tools", "Tools"),
        "menu_business": texts.get("menu_business", "Business"),
        "menu_ent": texts.get("menu_ent", "Entertainment"),
        "menu_premium": texts.get("menu_premium", "Premium"),
    })
    await msg_obj.reply(texts.get("main_menu", "Choose a feature below:"), reply_markup=kb)


@router.callback_query(lambda c: c.data == "open_menu")
async def cb_open_menu(cb: CallbackQuery):
    await show_main_menu(cb.message)
    await cb.answer()


def register(dp):
    dp.include_router(router)
