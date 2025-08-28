# admin_panel/stats_dashboard.py
import asyncio
import json
from core import database
import logging
from datetime import datetime

logger = logging.getLogger("smartx_bot.admin_stats")

async def export_stats(out_prefix="smartx_report"):
    await database.connect()
    db = database.get_mongo_db()
    total = await db.users.count_documents({})
    premium = await db.users.count_documents({"plan":"premium"})
    today = datetime.utcnow().date().isoformat()
    report = {
        "date": today,
        "total_users": total,
        "premium_users": premium,
    }
    fname = f"{out_prefix}_{today}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info("Wrote report %s", fname)
    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(export_stats())
