# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb(lang_strings):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(text=lang_strings.get("menu_ai","AI Assistant"), callback_data="menu_ai"),
        InlineKeyboardButton(text=lang_strings.get("menu_downloader","Downloader"), callback_data="menu_downloader"),
    )
    kb.add(
        InlineKeyboardButton(text=lang_strings.get("menu_tools","Tools"), callback_data="menu_tools"),
        InlineKeyboardButton(text=lang_strings.get("menu_business","Business"), callback_data="menu_business"),
    )
    kb.add(
        InlineKeyboardButton(text=lang_strings.get("menu_ent","Entertainment"), callback_data="menu_ent"),
        InlineKeyboardButton(text=lang_strings.get("menu_premium","Premium"), callback_data="menu_premium"),
    )
    return kb
