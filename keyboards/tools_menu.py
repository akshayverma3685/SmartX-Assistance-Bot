# keyboards/tools_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def tools_menu_kb(lang_strings: dict = None):
    get = lambda k, d: (lang_strings.get(k) if lang_strings and k in lang_strings else d)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(get("notes", "📝 Notes"), callback_data="tool_notes"),
        InlineKeyboardButton(get("currency", "📊 Currency"), callback_data="tool_currency"),
    )
    kb.add(
        InlineKeyboardButton(get("weather", "🌦 Weather"), callback_data="tool_weather"),
        InlineKeyboardButton(get("shorten", "🔗 URL Shortener"), callback_data="tool_shorten"),
    )
    kb.add(
        InlineKeyboardButton(get("qr", "🖼 QR Generator"), callback_data="tool_qr"),
        InlineKeyboardButton(get("back", "🔙 Back"), callback_data="open_menu"),
    )
    return kb
