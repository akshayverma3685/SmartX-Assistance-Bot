# handlers/entertainment.py
import logging
import random
from aiogram import Router
from aiogram.types import Message

logger = logging.getLogger("smartx_bot.handlers.entertainment")
router = Router()

JOKES = [
    "Programmer joke: Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and it said 'No problem — I'll go to sleep.'",
    "Why did the developer go broke? Because he used up all his cache."
]


@router.message(commands=["joke"])
async def cmd_joke(message: Message):
    await message.reply(random.choice(JOKES))


@router.message(commands=["roll"])
async def cmd_roll(message: Message):
    args = message.get_args()
    sides = 6
    try:
        if args:
            sides = int(args)
    except:
        sides = 6
    await message.reply(f"You rolled: {random.randint(1, sides)}")


def register(dp):
    dp.include_router(router)
