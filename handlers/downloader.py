# handlers/downloader.py
from aiogram import Router
from aiogram.types import Message
from services.download_service import download_video
import os
import logging

logger = logging.getLogger("smartx_bot.handlers.downloader")
router = Router()

@router.message(commands=["download"])
async def cmd_download(message: Message):
    url = message.get_args()
    if not url:
        await message.reply("Usage: /download <video_url>")
        return
    await message.reply("Downloading... please wait.")
    res = download_video(url)
    if res.get("status") == "success":
        filepath = res["filepath"]
        try:
            await message.reply_video(open(filepath, "rb"))
        except Exception as e:
            await message.reply("Downloaded but failed to send (file big).")
        finally:
            try:
                os.remove(filepath)
            except:
                pass
    else:
        await message.reply("Download failed: " + res.get("error","unknown"))

def register(dp):
    dp.include_router(router)
