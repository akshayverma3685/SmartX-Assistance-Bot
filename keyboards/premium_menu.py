# keyboards/premium_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def premium_menu_kb(plans_list):
    kb = InlineKeyboardMarkup(row_width=1)
    for plan in plans_list:
        kb.add(InlineKeyboardButton(f"{plan['plan_name']} — ₹{plan['price']} ({plan['duration_days']}d)", callback_data=f"buy_{plan['plan_name']}"))
    kb.add(InlineKeyboardButton("Manual Payment", callback_data="manual_pay"))
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="open_menu"))
    return kb
