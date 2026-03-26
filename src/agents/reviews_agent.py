import urllib.parse

from agents.base_agent import BaseAgent
from core.config import AppConfig
from core.database import Database
from utils.http_client import http

_REDDIT_HEADERS = {
    "User-Agent": "ResearchBotArmy/1.0 (research tool)",
    "Accept": "application/json",
}


class ReviewsAgent(BaseAgent):
    name = "reviews"

    def _fetch(self) -> list:
        results = []
        results.extend(self._reddit())

        if self.config.serp_api_key:
            results.extend(self._serp_reviews())

        return results[: self.config.agents.max_reddit_posts]

    def _reddit(self) -> list:
        keywords = self.config.product.keywords
        subreddits = self.config.product.review_subreddits
        query = " OR ".join(f'"{k}"' for k in keywords[:2])

        items = []
        # Search across relevant subreddits
        for sub in subreddits[:3]:
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={urllib.parse.quote(query)}&sort=new&limit=10&t=week&restrict_sr=1"
            )
            try:
                resp = http.get(url, headers=_REDDIT_HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    d = post.get("data", {})
                    items.append({
                        "source": f"Reddit/r/{sub}",
                        "title": d.get("title", ""),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "score": d.get("score", 0),
                        "comments": d.get("num_comments", 0),
                        "excerpt": (d.get("selftext") or "")[:300],
                    })
            except Exception as exc:
                self.logger.warning(f"Reddit r/{sub} failed: {exc}")

        # Also search all of Reddit (broader)
        broad_url = (
            f"https://www.reddit.com/search.json"
            f"?q={urllib.parse.quote(query)}&sort=new&limit=10&t=week"
        )
        try:
            resp = http.get(broad_url, headers=_REDDIT_HEADERS, timeout=15)
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    d = post.get("data", {})
                    items.append({
                        "source": f"Reddit/r/{d.get('subreddit', 'all')}",
                        "title": d.get("title", ""),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "score": d.get("score", 0),
                        "comments": d.get("num_comments", 0),
                        "excerpt": (d.get("selftext") or "")[:300],
                    })
        except Exception as exc:
            self.logger.warning(f"Reddit broad search failed: {exc}")

        # Deduplicate by URL
        seen = set()
        unique = []
        for item in items:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique.append(item)
        return unique

    def _serp_reviews(self) -> list:
        product = self.config.product.name
        query = f"{product} reviews site:trustpilot.com OR site:g2.com OR site:capterra.com"
        try:
            resp = http.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self.config.serp_api_key, "num": 5},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            return [
                {
                    "source": r.get("displayed_link", "Review Site"),
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "excerpt": r.get("snippet", "")[:300],
                }
                for r in resp.json().get("organic_results", [])[:5]
            ]
        except Exception as exc:
            self.logger.warning(f"SerpAPI reviews failed: {exc}")
            return []
