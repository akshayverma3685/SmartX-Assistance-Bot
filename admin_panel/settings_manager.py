#!/usr/bin/env python3
"""
admin_panel/settings_manager.py

SmartX Assistance - Admin Settings Manager

Features:
- View, set, reset bot settings stored in MongoDB
- Supports trial days, premium pricing, Razorpay keys, rate limits
- CLI tool (table or JSON output)
"""

import argparse
import asyncio
import logging
import os
import sys
import json
from typing import Any, Dict

import config
from core import database

LOG_PATH = os.path.join(os.path.dirname(__file__), "settings_manager.log")
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, "INFO"),
    format="%(asctime)s | %(levelname)8s | %(name)s : %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_PATH)],
)
logger = logging.getLogger("admin_panel.settings_manager")


# default settings (fallbacks)
DEFAULT_SETTINGS = {
    "free_trial_days": 7,
    "premium_price_inr": 199,
    "razorpay_key_id": "",
    "razorpay_key_secret": "",
    "broadcast_rate_limit": 20,  # msgs/sec
    "maintenance_mode": False,
}


async def get_all_settings() -> Dict[str, Any]:
    db = database.get_mongo_db()
    doc = await db.settings.find_one({"_id": "global"})
    if not doc:
        return DEFAULT_SETTINGS.copy()
    merged = DEFAULT_SETTINGS.copy()
    merged.update(doc.get("values", {}))
    return merged


async def set_setting(key: str, value: Any):
    if key not in DEFAULT_SETTINGS:
        raise ValueError(f"Invalid setting key: {key}")

    db = database.get_mongo_db()
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": {f"values.{key}": value}},
        upsert=True
    )


async def reset_settings():
    db = database.get_mongo_db()
    await db.settings.delete_one({"_id": "global"})


def print_table(settings: Dict[str, Any]):
    print("\n== Current Settings ==")
    max_key = max(len(k) for k in settings.keys())
    for k, v in settings.items():
        print(f"{k.ljust(max_key)} : {v}")


# ---------- CLI ----------
def build_argparser():
    p = argparse.ArgumentParser(description="Admin: Settings Manager")
    sub = p.add_subparsers(dest="command")

    # view
    sub.add_parser("view", help="View all settings")

    # set
    set_cmd = sub.add_parser("set", help="Set a setting")
    set_cmd.add_argument("key", help="Setting key")
    set_cmd.add_argument("value", help="Setting value")

    # reset
    sub.add_parser("reset", help="Reset all settings to defaults")

    p.add_argument("--json", action="store_true", help="Output JSON instead of table")

    return p


async def run():
    args = build_argparser().parse_args()

    await database.connect()
    try:
        if args.command == "view":
            settings = await get_all_settings()
            if args.json:
                print(json.dumps(settings, indent=2, ensure_ascii=False))
            else:
                print_table(settings)

        elif args.command == "set":
            key = args.key
            raw_val = args.value

            # try auto type conversion
            if raw_val.lower() in ["true", "false"]:
                val = raw_val.lower() == "true"
            else:
                try:
                    if "." in raw_val:
                        val = float(raw_val)
                    else:
                        val = int(raw_val)
                except ValueError:
                    val = raw_val  # keep as string

            await set_setting(key, val)
            logger.info(f"Setting updated: {key} = {val}")
            print(f"✅ Updated {key} = {val}")

        elif args.command == "reset":
            await reset_settings()
            logger.info("Settings reset to defaults")
            print("✅ Settings reset to defaults")

        else:
            print("No command specified. Use --help for usage.")
    finally:
        await database.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
