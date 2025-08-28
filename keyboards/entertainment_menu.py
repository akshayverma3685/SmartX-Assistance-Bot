# keyboards/entertainment_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def entertainment_menu_kb(lang_strings: dict = None):
    get = lambda k, d: (lang_strings.get(k) if lang_strings and k in lang_strings else d)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(get("games", "🧩 Games"), callback_data="ent_games"),
        InlineKeyboardButton(get("jokes", "😂 Jokes"), callback_data="ent_jokes"),
    )
    kb.add(
        InlineKeyboardButton(get("music", "🎧 Music Player"), callback_data="ent_music"),
        InlineKeyboardButton(get("back", "🔙 Back"), callback_data="open_menu"),
    )
    return kb
