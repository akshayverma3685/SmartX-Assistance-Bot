# handlers/ai.py
import logging
import asyncio
from aiogram import Router
from aiogram.types import Message
from core import database, helpers
import services.ai_service as ai_service

logger = logging.getLogger("smartx_bot.handlers.ai")
router = Router()


@router.message(commands=["chat"])
async def cmd_chat(message: Message):
    """
    /chat <prompt>
    Uses OpenAI via services.ai_service. Runs blocking call in threadpool.
    """
    prompt = message.get_args()
    if not prompt:
        await message.reply("Usage: /chat <your question>")
        return
    user_id = message.from_user.id
    # increment usage
    await helpers.increment_command_count(user_id)
    # optional: check limits
    # call AI
    try:
        # chat_completion is async wrapper already using executor, so call directly
        resp = await ai_service.chat_completion(prompt)
        await message.reply(resp)
    except Exception as e:
        logger.exception("AI chat failed: %s", e)
        await message.reply("AI service currently unavailable. Try later.")


@router.message(commands=["summarize"])
async def cmd_summarize(message: Message):
    """
    /summarize <text or url> - naive summarizer using ai_service chat_completion
    """
    text = message.get_args()
    if not text:
        await message.reply("Usage: /summarize <text or URL>")
        return
    await helpers.increment_command_count(message.from_user.id)
    prompt = f"Summarize the following text concisely:\n\n{text}"
    try:
        resp = await ai_service.chat_completion(prompt, max_tokens=400)
        await message.reply(resp)
    except Exception as e:
        logger.exception("Summarize failed: %s", e)
        await message.reply("Summarizer unavailable. Try later.")


def register(dp):
    dp.include_router(router)
