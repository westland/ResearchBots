import time
import urllib.parse

from agents.base_agent import BaseAgent
from core.config import AppConfig
from core.database import Database
from utils.http_client import http


class TrendsAgent(BaseAgent):
    name = "trends"

    def _fetch(self) -> list:
        items = []
        items.extend(self._hackernews())
        items.extend(self._google_trends())
        return items

    def _hackernews(self) -> list:
        keywords = self.config.product.keywords
        limit = self.config.agents.hn_stories
        query = " ".join(keywords[:2])

        try:
            resp = http.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": "created_at_i>1700000000",
                    "hitsPerPage": limit,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            hits = resp.json().get("hits", [])
            return [
                {
                    "source": "HackerNews",
                    "title": h.get("title", ""),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "points": h.get("points", 0),
                    "comments": h.get("num_comments", 0),
                    "excerpt": "",
                }
                for h in hits
                if h.get("title")
            ]
        except Exception as exc:
            self.logger.warning(f"HackerNews search failed: {exc}")
            return []

    def _google_trends(self) -> list:
        keywords = self.config.product.keywords[:5]
        # Cache trends for 6 hours to avoid rate-limiting
        cache_key = f"trends_cached_at"
        cached_at = self.db.get_state(cache_key)
        if cached_at:
            import json
            from datetime import datetime, timedelta
            try:
                ts = datetime.fromisoformat(cached_at)
                if datetime.utcnow() - ts < timedelta(hours=6):
                    cached = self.db.get_state("trends_data")
                    if cached:
                        return json.loads(cached)
            except Exception:
                pass

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
            time.sleep(1)  # be gentle with Google
            pytrends.build_payload(keywords, cat=0, timeframe="now 1-d", geo="US")
            interest = pytrends.interest_over_time()
            if interest.empty:
                return []
            latest = interest.tail(1).to_dict("records")[0]
            latest.pop("isPartial", None)
            items = [
                {
                    "source": "GoogleTrends",
                    "title": f"Trend: {kw}",
                    "url": "",
                    "interest_score": score,
                    "excerpt": f"Search interest score (0–100): {score}",
                }
                for kw, score in latest.items()
                if isinstance(score, (int, float))
            ]
            # Cache result
            import json
            from datetime import datetime
            self.db.set_state(cache_key, datetime.utcnow().isoformat())
            self.db.set_state("trends_data", json.dumps(items))
            return items
        except ImportError:
            self.logger.debug("pytrends not installed; skipping Google Trends")
            return []
        except Exception as exc:
            self.logger.warning(f"Google Trends failed: {exc}")
            return []
