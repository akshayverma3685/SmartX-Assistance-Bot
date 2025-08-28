"""
config.py - Centralized configuration management for SmartX Assistance Bot

Loads settings from environment variables (.env file) using python-dotenv.
Provides strongly typed config values with sane defaults.
"""

import os
from dotenv import load_dotenv

# load .env file
load_dotenv()

# === Telegram Bot ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
RUN_MODE = os.getenv("RUN_MODE", "polling")  # "polling" or "webhook"

# === Webhook Settings (if RUN_MODE = webhook) ===
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8080"))

# === Database Settings ===
DB_TYPE = os.getenv("DB_TYPE", "mongo")  # "mongo" or "postgres"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/smartx")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "smartx")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "smartx")

# === Logging ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# === Payments ===
# Razorpay keys (for auto gateway integration)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

# Manual payment settings
MANUAL_PAYMENT_UPI = os.getenv("MANUAL_PAYMENT_UPI", "owner@upi")
MANUAL_PAYMENT_NUMBER = os.getenv("MANUAL_PAYMENT_NUMBER", "")

# === Plans & Trial ===
FREE_TRIAL_DAYS = int(os.getenv("FREE_TRIAL_DAYS", "3"))
DEFAULT_PREMIUM_DAYS = int(os.getenv("DEFAULT_PREMIUM_DAYS", "30"))
PLAN_BASIC_LIMIT = int(os.getenv("PLAN_BASIC_LIMIT", "50"))     # messages/downloads
PLAN_PREMIUM_LIMIT = int(os.getenv("PLAN_PREMIUM_LIMIT", "500"))

# === Features Toggles ===
ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
ENABLE_DOWNLOADS = os.getenv("ENABLE_DOWNLOADS", "true").lower() == "true"
ENABLE_BUSINESS = os.getenv("ENABLE_BUSINESS", "true").lower() == "true"
ENABLE_ENTERTAINMENT = os.getenv("ENABLE_ENTERTAINMENT", "true").lower() == "true"

# === Third-party APIs ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
URL_SHORTENER_API = os.getenv("URL_SHORTENER_API", "")

# === Localization ===
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = ["en", "hi"]

# === Security ===
ALLOWED_UPDATES = ["message", "callback_query"]  # reduce load
ANTI_FLOOD_LIMIT = int(os.getenv("ANTI_FLOOD_LIMIT", "3"))  # messages/sec/user
ANTI_SPAM_BAN_TIME = int(os.getenv("ANTI_SPAM_BAN_TIME", "3600"))  # sec

# === Owner Links (will show in About/Follow Section) ===
OWNER_NAME = os.getenv("OWNER_NAME", "SmartX Dev")
OWNER_TELEGRAM = os.getenv("OWNER_TELEGRAM", "https://t.me/yourusername")
OWNER_INSTAGRAM = os.getenv("OWNER_INSTAGRAM", "")
OWNER_TWITTER = os.getenv("OWNER_TWITTER", "")
OWNER_GITHUB = os.getenv("OWNER_GITHUB", "")
OWNER_WEBSITE = os.getenv("OWNER_WEBSITE", "")

# === Misc ===
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # cache time in seconds
SESSION_NAME = os.getenv("SESSION_NAME", "smartx_bot")
