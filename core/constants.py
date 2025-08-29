"""
core/constants.py

Centralized constants and reusable messages for SmartX Assistance Bot.
Supports multi-language (English & Hindi).
"""

from typing import Dict

# ---------------------------
# General Constants
# ---------------------------

BOT_NAME = "🤖 SmartX Assistance"
FREE_TRIAL_DAYS = 7
PREMIUM_PRICE_INR = 199
MAX_FILE_SIZE_MB = 2000  # 2GB Telegram Bot API Limit
DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES = ["en", "hi"]

# Admin Panel
ADMIN_ACTIONS = [
    "Broadcast",
    "View Logs",
    "View Payments",
    "User Management",
    "Stats Dashboard",
    "Error Monitor",
    "Settings Manager",
]

# ---------------------------
# Emojis
# ---------------------------
EMOJI = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "star": "⭐",
    "fire": "🔥",
    "money": "💰",
    "lock": "🔒",
    "unlock": "🔓",
    "rocket": "🚀",
    "gift": "🎁",
    "crown": "👑",
}

# ---------------------------
# Language Messages
# ---------------------------

MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "start": f"Welcome to {BOT_NAME}! {EMOJI['rocket']}\n\n"
                 "Your all-in-one Telegram Assistant with Free & Premium features.\n\n"
                 "Use /help to see available commands.",
        "help": "Here are the available commands:\n"
                "/start - Start the bot\n"
                "/help - Show help\n"
                "/upgrade - Upgrade to Premium\n"
                "/profile - View your profile\n"
                "/settings - Manage your settings",
        "trial_activated": f"{EMOJI['gift']} Free trial activated for {FREE_TRIAL_DAYS} days!",
        "premium_required": f"{EMOJI['lock']} This feature is only for Premium users.",
        "premium_activated": f"{EMOJI['crown']} Premium activated successfully!",
        "payment_pending": f"{EMOJI['warning']} Your payment is pending confirmation.",
        "payment_success": f"{EMOJI['money']} Payment received! Premium enabled.",
        "error_generic": f"{EMOJI['error']} Oops! Something went wrong. Please try again later.",
        "lang_changed": f"{EMOJI['success']} Language updated successfully.",
        "profile": f"{EMOJI['info']} Your Profile:",
        "broadcast_done": f"{EMOJI['success']} Broadcast completed successfully.",
        "maintenance_mode": f"{EMOJI['warning']} Bot is under maintenance, please try again later.",
    },
    "hi": {
        "start": f"{BOT_NAME} me aapka swagat hai! {EMOJI['rocket']}\n\n"
                 "Ye ek All-in-One Telegram Assistant hai jisme Free & Premium features available hain.\n\n"
                 "Commands dekhne ke liye /help type karein.",
        "help": "Ye commands available hain:\n"
                "/start - Bot shuru karein\n"
                "/help - Madad lein\n"
                "/upgrade - Premium lein\n"
                "/profile - Apna profile dekhein\n"
                "/settings - Apne settings badlein",
        "trial_activated": f"{EMOJI['gift']} Free trial {FREE_TRIAL_DAYS} din ke liye activate ho gaya!",
        "premium_required": f"{EMOJI['lock']} Ye feature sirf Premium users ke liye hai.",
        "premium_activated": f"{EMOJI['crown']} Premium safaltapurvak activate ho gaya!",
        "payment_pending": f"{EMOJI['warning']} Aapka payment abhi pending hai.",
        "payment_success": f"{EMOJI['money']} Payment received! Premium active ho gaya.",
        "error_generic": f"{EMOJI['error']} Oops! Kuch galat ho gaya. Baad me try karein.",
        "lang_changed": f"{EMOJI['success']} Language safaltapurvak update ho gayi.",
        "profile": f"{EMOJI['info']} Aapka Profile:",
        "broadcast_done": f"{EMOJI['success']} Broadcast safaltapurvak complete ho gaya.",
        "maintenance_mode": f"{EMOJI['warning']} Bot abhi maintenance me hai, baad me try karein.",
    }
}

# ---------------------------
# Helper Function
# ---------------------------

def t(lang: str, key: str) -> str:
    """Fetch translated message with fallback"""
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return MESSAGES.get(lang, MESSAGES[DEFAULT_LANGUAGE]).get(key, f"[missing:{key}]")
