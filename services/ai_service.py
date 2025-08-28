# services/ai_service.py
import openai
import config
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("smartx_bot.ai_service")
openai.api_key = config.OPENAI_API_KEY

# helper to run blocking openai in executor
async def _run_in_executor(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))

def _openai_chat_sync(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 512):
    # sync call (blocking)
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.exception("OpenAI sync call failed: %s", e)
        raise

async def chat_completion(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 512) -> str:
    if not config.ENABLE_AI:
        return "AI feature currently disabled by owner."
    try:
        text = await _run_in_executor(_openai_chat_sync, prompt, model, max_tokens)
        return text
    except Exception as e:
        logger.exception("chat_completion error: %s", e)
        return "Sorry, AI service unavailable right now."
