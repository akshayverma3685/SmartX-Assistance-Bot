# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(lang_strings: dict = None):
    # lang_strings optional dict; fallback labels used if not provided
    def g(k, fallback):
        return (lang_strings.get(k) if lang_strings and k in lang_strings else fallback)

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(g("menu_ai", "🧠 AI Assistant"), callback_data="menu_ai"),
        InlineKeyboardButton(g("menu_downloader", "📥 Downloader"), callback_data="menu_downloader"),
    )
    kb.add(
        InlineKeyboardButton(g("menu_tools", "📂 Tools"), callback_data="menu_tools"),
        InlineKeyboardButton(g("menu_business", "💼 Business"), callback_data="menu_business"),
    )
    kb.add(
        InlineKeyboardButton(g("menu_ent", "🎉 Entertainment"), callback_data="menu_ent"),
        InlineKeyboardButton(g("menu_premium", "⭐ Premium"), callback_data="menu_premium"),
    )
    return kb
