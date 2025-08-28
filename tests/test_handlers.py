# tests/test_handlers.py
import pytest
from aiogram import Bot
import config

@pytest.mark.asyncio
async def test_bot_token_present():
    assert config.BOT_TOKEN, "BOT_TOKEN must be set for tests"
