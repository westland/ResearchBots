import hashlib
import re

from bs4 import BeautifulSoup

from agents.base_agent import BaseAgent
from core.config import AppConfig
from core.database import Database
from utils.http_client import http

PRICE_RE = re.compile(
    r'\$\s*[\d,]+(?:\.\d{2})?|\b[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP)\b',
    re.IGNORECASE,
)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return " ".join(text.split())


def _content_hash(text: str) -> str:
    return hashlib.sha256(text[:5000].encode()).hexdigest()


class CompetitorAgent(BaseAgent):
    name = "competitor"

    def _fetch(self) -> list:
        timeout = self.config.agents.competitor_timeout
        results = []
        for comp in self.config.product.competitors:
            result = self._scrape(comp, timeout)
            results.append(result)
        return results

    def _scrape(self, comp: dict, timeout: int) -> dict:
        name = comp.get("name", comp.get("url", "unknown"))
        url = comp.get("url", "")

        try:
            resp = http.get(url, timeout=timeout)
            resp.raise_for_status()
        except Exception as exc:
            self.logger.warning(f"Could not fetch {name}: {exc}")
            return {"name": name, "url": url, "error": str(exc), "changed": False}

        text = _extract_text(resp.text)
        content_hash = _content_hash(text)

        # Change detection
        previous = self.db.get_competitor_snapshot(name)
        changed = previous is None or previous["content_hash"] != content_hash

        # Save new snapshot
        self.db.save_competitor_snapshot(name, url, content_hash, text[:600])

        # Price extraction
        prices = list(dict.fromkeys(PRICE_RE.findall(text[:8000])))[:8]

        # Meta description
        soup = BeautifulSoup(resp.text, "lxml")
        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = (meta.get("content", "") if meta else "")[:200]
        title = (soup.title.string.strip() if soup.title else "")[:120]

        return {
            "name": name,
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "prices_found": prices,
            "content_excerpt": text[:500],
            "changed": changed,
            "error": None,
        }
