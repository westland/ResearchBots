import urllib.parse
from datetime import datetime, timedelta

import feedparser

from agents.base_agent import BaseAgent
from core.config import AppConfig
from core.database import Database
from utils.http_client import http


class NewsAgent(BaseAgent):
    name = "news"

    def _fetch(self) -> list:
        keywords = self.config.product.keywords
        api_key = self.config.news_api_key
        limit = self.config.agents.max_articles

        articles = []
        if api_key:
            articles = self._newsapi(keywords, api_key, limit)

        if not articles:
            articles = self._google_news_rss(keywords, limit)

        return articles[:limit]

    def _newsapi(self, keywords: list, api_key: str, limit: int) -> list:
        query = " OR ".join(f'"{k}"' for k in keywords[:4])
        since = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        resp = http.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": min(limit, 20),
                "from": since,
                "apiKey": api_key,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            self.logger.warning(f"NewsAPI returned {resp.status_code}")
            return []
        return [
            {
                "title": a["title"],
                "source": a["source"]["name"],
                "url": a["url"],
                "summary": (a.get("description") or "")[:250],
                "published": a.get("publishedAt", ""),
            }
            for a in resp.json().get("articles", [])
            if a.get("title") and "[Removed]" not in a.get("title", "")
        ]

    def _google_news_rss(self, keywords: list, limit: int) -> list:
        query = urllib.parse.quote(" ".join(keywords[:3]))
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url)
        return [
            {
                "title": e.get("title", ""),
                "source": e.get("source", {}).get("title", "Google News"),
                "url": e.get("link", ""),
                "summary": (e.get("summary") or "")[:250],
                "published": e.get("published", ""),
            }
            for e in feed.entries[:limit]
            if e.get("title")
        ]
