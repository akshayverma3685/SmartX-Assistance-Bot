# keyboards/business_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def business_menu_kb(lang_strings: dict = None):
    get = lambda k, d: (lang_strings.get(k) if lang_strings and k in lang_strings else d)
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton(get("invoice", "📑 Invoice Generator"), callback_data="biz_invoice"),
        InlineKeyboardButton(get("expense", "💰 Expense Tracker"), callback_data="biz_expense"),
        InlineKeyboardButton(get("crm", "📇 CRM"), callback_data="biz_crm"),
        InlineKeyboardButton(get("back", "🔙 Back"), callback_data="open_menu"),
    )
    return kb
