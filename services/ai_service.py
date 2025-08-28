# services/ai_service.py
import openai
import config
import logging
openai.api_key = config.OPENAI_API_KEY
logger = logging.getLogger("smartx_bot.ai_service")

async def chat_completion(prompt: str, max_tokens: int = 512, model: str = "gpt-4o-mini"):
    # OpenAI python client is blocking - for production use run in executor or use an async client
    import asyncio
    loop = asyncio.get_event_loop()
    def call_openai():
        res = openai.ChatCompletion.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            max_tokens=max_tokens,
        )
        return res
    try:
        res = await loop.run_in_executor(None, call_openai)
        text = res.choices[0].message.content
        return text
    except Exception as e:
        logger.exception("OpenAI call failed: %s", e)
        return "Sorry, AI service unavailable right now."
