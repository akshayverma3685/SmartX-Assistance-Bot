# handlers/ai.py
from aiogram import Router
from aiogram.types import Message
from services.ai_service import chat_completion
from core import database
import logging

logger = logging.getLogger("smartx_bot.handlers.ai")
router = Router()

@router.message(commands=["chat"])
async def cmd_chat(message: Message):
    # usage: /chat Tell me a joke about programmers
    prompt = message.get_args()
    if not prompt:
        await message.reply("Usage: /chat <your question>")
        return
    # check user plan and usage (omitted here for brevity)
    response = await chat_completion(prompt)
    await message.reply(response)

def register(dp):
    dp.include_router(router)
