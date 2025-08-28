# handlers/menu.py
from aiogram import Router, types
from aiogram.types import Message, CallbackQuery
import json, os
from keyboards.main_menu import main_menu_kb
from core import database
import config

router = Router()
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALES_DIR = os.path.join(BASE_DIR, "locales")

def load_locale(lang):
    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(path):
        path = os.path.join(LOCALES_DIR, "en.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

async def show_main_menu(msg_obj, lang=None):
    # msg_obj can be message or chat id - here we assume message object
    if hasattr(msg_obj, "chat"):
        chat = msg_obj.chat
        user_id = msg_obj.from_user.id
    else:
        # fallback if called with chat id
        return

    db = database.db
    user = await db.users.find_one({"user_id": user_id})
    lang = lang or (user.get("language") if user else config.LANG_DEFAULT)
    texts = load_locale(lang)
    kb = main_menu_kb({
        "menu_ai": "🧠 AI Assistant",
        "menu_downloader": "📥 Downloader",
        "menu_tools": "📂 Tools",
        "menu_business": "💼 Business",
        "menu_ent": "🎉 Entertainment",
        "menu_premium": "⭐ Premium"
    })
    await msg_obj.reply(texts.get("main_menu","Choose a feature below:"), reply_markup=kb)

@router.callback_query(lambda c: c.data == "open_menu")
async def cb_open_menu(cb: CallbackQuery):
    user_id = cb.from_user.id
    db = database.db
    user = await db.users.find_one({"user_id": user_id})
    lang = user.get("language") if user else config.LANG_DEFAULT
    texts = load_locale(lang)
    kb = main_menu_kb({})
    await cb.message.edit_text(texts.get("main_menu"), reply_markup=kb)
    await cb.answer()

def register(dp):
    dp.include_router(router)
