# web/admin_api.py
from fastapi import FastAPI, Header, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
import io, csv, json
import logging
import config
from core import database, helpers
from typing import Optional
import asyncio
import os

logger = logging.getLogger("smartx_bot.admin_api")
app = FastAPI(title="SmartX Admin API")

def require_api_key(x_api_key: Optional[str] = Header(None)):
    key = os.getenv("ADMIN_API_KEY", None)
    if not key or x_api_key != key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/health")
async def health():
    stat = await database.healthcheck()
    return stat

@app.get("/stats", dependencies=[Depends(require_api_key)])
async def stats():
    db = database.get_mongo_db()
    total = await db.users.count_documents({})
    premium = await db.users.count_documents({"plan":"premium"})
    return {"total_users": total, "premium_users": premium}

@app.get("/export/users.csv", dependencies=[Depends(require_api_key)])
async def export_users_csv():
    db = database.get_mongo_db()
    cursor = db.users.find({})
    def gen():
        buff = io.StringIO()
        writer = csv.writer(buff)
        writer.writerow(["user_id", "username", "plan", "expiry_date", "joined_date", "referrals", "commands_used"])
        yield buff.getvalue()
        buff.seek(0)
        buff.truncate(0)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def iterate():
            async for u in cursor:
                writer.writerow([
                    u.get("user_id"),
                    u.get("username"),
                    u.get("plan"),
                    u.get("expiry_date"),
                    u.get("joined_date"),
                    u.get("referrals",0),
                    u.get("commands_used",0)
                ])
                yield buff.getvalue()
                buff.seek(0); buff.truncate(0)
        for chunk in loop.run_until_complete(iterate()):
            yield chunk
    return StreamingResponse(gen(), media_type="text/csv", headers={"Content-Disposition":"attachment; filename=users.csv"})

@app.post("/broadcast", dependencies=[Depends(require_api_key)])
async def api_broadcast(message: str, background: BackgroundTasks):
    # schedule background broadcast (simple approach)
    async def send_all(msg):
        db = database.get_mongo_db()
        cursor = db.users.find({}, {"user_id":1})
        from aiogram import Bot
        bot = Bot(token=config.BOT_TOKEN)
        async for u in cursor:
            try:
                await bot.send_message(u["user_id"], msg)
            except Exception:
                continue
        await bot.session.close()
    background.add_task(asyncio.create_task, send_all(message))
    return {"status":"scheduled"}
