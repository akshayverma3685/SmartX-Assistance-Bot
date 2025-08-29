"""
news_service.py
Service for fetching latest news for SmartX Assistance Bot.
Features:
- Fetch news by category and language
- Cache results to reduce API load
- Handle API errors gracefully
"""

import os
import requests
from typing import Optional, List, Dict
from core.cache import cache_result
from logs.bot_logger import get_bot_logger

logger = get_bot_logger()

# NewsAPI (or similar API) configuration
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "your_api_key_here")
BASE_URL = "https://newsapi.org/v2/top-headlines"

SUPPORTED_LANGUAGES = ["en", "hi"]
SUPPORTED_CATEGORIES = ["general", "technology", "business", "sports", "science", "health", "entertainment"]

class NewsService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or NEWS_API_KEY

    @cache_result(ttl=300)  # cache for 5 minutes
    def get_top_news(self, category: str = "general", language: str = "en", limit: int = 5) -> List[Dict]:
        """
        Fetch latest news articles by category & language.
        Returns a list of dicts with {title, url, source}.
        """
        if language not in SUPPORTED_LANGUAGES:
            language = "en"

        if category not in SUPPORTED_CATEGORIES:
            category = "general"

        params = {
            "apiKey": self.api_key,
            "category": category,
            "language": language,
            "pageSize": limit,
            "country": "in" if language == "hi" else None
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            articles = [
                {
                    "title": art["title"],
                    "url": art["url"],
                    "source": art["source"]["name"]
                }
                for art in data.get("articles", [])
                if art.get("title") and art.get("url")
            ]

            logger.info("Fetched news articles",
                        extra={"source": "news_service.get_top_news",
                               "meta": {"category": category, "language": language, "count": len(articles)}})

            return articles

        except Exception as e:
            logger.exception("Failed to fetch news",
                             extra={"source": "news_service.get_top_news",
                                    "meta": {"category": category, "language": language}})
            return []

    def format_news_for_user(self, articles: List[Dict]) -> str:
        """
        Convert news list into user-friendly text for Telegram message.
        """
        if not articles:
            return "⚠️ Koi fresh news nahi mil paayi."

        lines = []
        for i, art in enumerate(articles, 1):
            lines.append(f"{i}. [{art['title']}]({art['url']}) - {art['source']}")

        return "\n".join(lines)
