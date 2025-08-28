# keyboards/ai_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def ai_menu_kb(lang_strings: dict = None):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💬 AI Chat", callback_data="ai_chat"),
        InlineKeyboardButton("📄 Summarize", callback_data="ai_summarize"),
    )
    kb.add(
        InlineKeyboardButton("🖼 Image Gen", callback_data="ai_image"),
        InlineKeyboardButton("🎙 Text↔Voice", callback_data="ai_voice"),
    )
    kb.add(InlineKeyboardButton("🔙 Back", callback_data="open_menu"))
    return kb
