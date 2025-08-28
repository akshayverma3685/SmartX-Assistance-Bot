# keyboards/downloader_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def downloader_menu_kb(lang_strings: dict = None):
    # lang_strings optional: expects keys 'yt', 'ig', 'music', 'files', 'back'
    get = lambda k, d: (lang_strings.get(k) if lang_strings and k in lang_strings else d)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(get("yt", "🎬 YouTube"), callback_data="dl_youtube"),
        InlineKeyboardButton(get("ig", "📸 Instagram"), callback_data="dl_instagram"),
    )
    kb.add(
        InlineKeyboardButton(get("tt", "🎵 TikTok"), callback_data="dl_tiktok"),
        InlineKeyboardButton(get("music", "🎧 Music"), callback_data="dl_music"),
    )
    kb.add(
        InlineKeyboardButton(get("files", "📁 Documents"), callback_data="dl_files"),
        InlineKeyboardButton(get("back", "🔙 Back"), callback_data="open_menu"),
    )
    return kb
