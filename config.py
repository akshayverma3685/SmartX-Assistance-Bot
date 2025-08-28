# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
MONGO_URI = os.getenv("MONGO_URI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

RUN_MODE = os.getenv("RUN_MODE", "polling")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LANG_DEFAULT = os.getenv("LANG_DEFAULT", "en")
FREE_TRIAL_DAYS = int(os.getenv("FREE_TRIAL_DAYS", "3"))

# Premium plans default (can be edited via admin panel stored in DB)
PREMIUM_PLANS = [
    {"plan_name": "Basic", "duration_days": 30, "price": 199},
    {"plan_name": "Pro", "duration_days": 90, "price": 499},
    {"plan_name": "Ultra", "duration_days": 365, "price": 1499},
]

# Safety checks
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in .env")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set in .env")
