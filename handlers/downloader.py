# handlers/downloader.py
import logging
import os
import asyncio
from aiogram import Router
from aiogram.types import Message
from services.download_service import download_video
from core import helpers

logger = logging.getLogger("smartx_bot.handlers.downloader")
router = Router()


@router.message(commands=["download"])
async def cmd_download(message: Message):
    """
    /download <url>
    Downloads video via yt-dlp and sends back if file size reasonable.
    For big files, send as document with caption and cleanup.
    """
    url = message.get_args()
    if not url:
        await message.reply("Usage: /download <video_url>")
        return
    await message.reply("Downloading... this may take some time.")
    # run blocking downloader in executor (download_video is blocking)
    loop = asyncio.get_event_loop()
    try:
        res = await loop.run_in_executor(None, download_video, url)
        if res.get("status") == "success":
            filepath = res["filepath"]
            filesize = os.path.getsize(filepath)
            # Telegram limit ~50MB for bot without special file API; keep simple check
            try:
                if filesize < 45 * 1024 * 1024:
                    await message.reply_video(open(filepath, "rb"))
                else:
                    await message.reply_document(open(filepath, "rb"))
            except Exception:
                await message.reply("Downloaded but failed to send due to size or network.")
            finally:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        else:
            await message.reply(f"Download failed: {res.get('error','unknown')}")
    except Exception as e:
        logger.exception("Download handler failed: %s", e)
        await message.reply("Download failed due to server error.")


def register(dp):
    dp.include_router(router)
