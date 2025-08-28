# keyboards/admin_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu_kb(lang_strings: dict = None):
    get = lambda k, d: (lang_strings.get(k) if lang_strings and k in lang_strings else d)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(get("users", "👥 Users"), callback_data="admin_users"),
        InlineKeyboardButton(get("payments", "💳 Payments"), callback_data="admin_payments"),
    )
    kb.add(
        InlineKeyboardButton(get("broadcast", "📢 Broadcast"), callback_data="admin_broadcast"),
        InlineKeyboardButton(get("stats", "📊 Stats"), callback_data="admin_stats"),
    )
    kb.add(InlineKeyboardButton(get("back", "🔙 Back"), callback_data="open_menu"))
    return kb
