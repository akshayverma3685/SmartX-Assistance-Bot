# handlers/tools.py
import logging
from aiogram import Router
from aiogram.types import Message, InputFile
from services.utils_service import generate_qr, shorten_url
from core import helpers

logger = logging.getLogger("smartx_bot.handlers.tools")
router = Router()


@router.message(commands=["qr"])
async def cmd_qr(message: Message):
    """
    /qr <text/url> -> returns QR image
    """
    text = message.get_args()
    if not text:
        await message.reply("Usage: /qr <text_or_url>")
        return
    bio = generate_qr(text)
    await message.reply_photo(photo=InputFile(bio), caption="QR generated.")


@router.message(commands=["shorten"])
async def cmd_shorten(message: Message):
    url = message.get_args()
    if not url:
        await message.reply("Usage: /shorten <url>")
        return
    short = shorten_url(url)
    await message.reply(f"Short URL: {short}")


@router.message(commands=["note"])
async def cmd_note(message: Message):
    """
    /note add <text>   -> add note
    /note list         -> list notes
    Simple impl: store in user doc under 'notes' array (Mongo). For Postgres, leave for later.
    """
    args = message.get_args().strip()
    user_id = message.from_user.id
    if not args:
        await message.reply("Usage: /note add <text> | /note list")
        return
    parts = args.split(" ", 1)
    action = parts[0].lower()
    db = None
    if getattr(config, "DB_TYPE", "mongo") == "mongo":
        db = database.get_mongo_db()
    if action == "add" and len(parts) == 2:
        text = parts[1].strip()
        if db:
            await db.users.update_one({"user_id": user_id}, {"$push": {"notes": {"text": text, "created": helpers.now_utc()}}}, upsert=True)
            await message.reply("Note saved.")
        else:
            await message.reply("Notes not supported for Postgres mode yet.")
    elif action == "list":
        if db:
            user = await db.users.find_one({"user_id": user_id}, {"notes": 1})
            notes = user.get("notes", []) if user else []
            if not notes:
                await message.reply("No notes found.")
            else:
                out = "\n".join([f"{i+1}. {n['text']}" for i, n in enumerate(notes)])
                await message.reply(out)
        else:
            await message.reply("Notes not supported for Postgres mode yet.")
    else:
        await message.reply("Unknown note command. Use add/list.")


def register(dp):
    dp.include_router(router)
