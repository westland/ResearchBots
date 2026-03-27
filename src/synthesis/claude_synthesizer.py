import logging
from datetime import datetime

import anthropic

from core.config import AppConfig

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a sharp market intelligence analyst writing a daily briefing for a founder or product manager.
Be specific and insightful. Avoid generic statements. Flag anything actionable or surprising.
Write in clean markdown. Be concise — founders are busy."""

_USER_TEMPLATE = """\
Product: {product_name} ({product_category})
{product_description}{objectives}
Date: {date}

== NEWS & INDUSTRY ==
{news}

== COMPETITOR MONITORING ==
{competitors}

== COMMUNITY & REVIEWS ==
{reviews}

== TRENDS & SOCIAL ==
{trends}

---
Write a daily briefing with these sections:

**Executive Summary** — 2–3 sentences: what matters most today.

**News & Industry** — top 3–5 stories with key takeaways for this product/market.

**Competitor Watch** — pricing or site changes detected; note any "CHANGED" entries specifically. If nothing changed, say so briefly.

**Community Pulse** — what people are actually saying. Surface complaints, questions, or praise about this space.

**Trends** — notable search trends or HackerNews signals. Skip if data is thin.

**Today's Action Items** — 1–3 concrete things worth acting on based on today's data only.

Keep the total under 600 words. Use bullet points. Skip sections with truly no data."""


def _fmt_news(items: list) -> str:
    if not items:
        return "No news data collected."
    lines = []
    for a in items[:8]:
        title = a.get("title", "")
        source = a.get("source", "")
        summary = a.get("summary", "")[:180]
        lines.append(f"- [{source}] {title} — {summary}")
    return "\n".join(lines)


def _fmt_competitors(items: list) -> str:
    if not items:
        return "No competitors configured."
    lines = []
    for c in items:
        if c.get("error"):
            lines.append(f"- {c['name']}: fetch failed ({c['error'][:80]})")
            continue
        status = "**CHANGED**" if c.get("changed") else "no change"
        prices = ", ".join(c.get("prices_found", [])[:5]) or "none detected"
        desc = c.get("meta_description", "")[:120]
        lines.append(f"- {c['name']} [{status}] | prices: {prices} | {desc}")
    return "\n".join(lines)


def _fmt_reviews(items: list) -> str:
    if not items:
        return "No community data collected."
    lines = []
    for r in items[:8]:
        source = r.get("source", "")
        title = r.get("title", "")
        excerpt = r.get("excerpt", "")[:150]
        score = r.get("score", "")
        line = f"- [{source}] {title}"
        if score:
            line += f" (score: {score})"
        if excerpt:
            line += f" — {excerpt}"
        lines.append(line)
    return "\n".join(lines)


def _fmt_trends(items: list) -> str:
    if not items:
        return "No trends data collected."
    lines = []
    for t in items[:8]:
        source = t.get("source", "")
        title = t.get("title", "")
        excerpt = t.get("excerpt", "")[:120]
        pts = t.get("points", "")
        line = f"- [{source}] {title}"
        if pts:
            line += f" ({pts} pts)"
        if excerpt:
            line += f" — {excerpt}"
        lines.append(line)
    return "\n".join(lines)


def synthesize(config: AppConfig, agent_data: dict, objectives: list | None = None) -> tuple[str, int]:
    """Generate the daily briefing. Returns (markdown_text, token_count)."""
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    product = config.product

    news_items = agent_data.get("news", {}).get("data", [])
    comp_items = agent_data.get("competitor", {}).get("data", [])
    review_items = agent_data.get("reviews", {}).get("data", [])
    trend_items = agent_data.get("trends", {}).get("data", [])

    obj_section = ""
    if objectives:
        obj_lines = "\n".join(f"- {o}" for o in objectives)
        obj_section = f"\nResearch objectives for this run:\n{obj_lines}\n"

    user_msg = _USER_TEMPLATE.format(
        product_name=product.name,
        product_category=product.category,
        product_description=f"Description: {product.description}" if product.description else "",
        objectives=obj_section,
        date=datetime.utcnow().strftime("%B %d, %Y"),
        news=_fmt_news(news_items),
        competitors=_fmt_competitors(comp_items),
        reviews=_fmt_reviews(review_items),
        trends=_fmt_trends(trend_items),
    )

    logger.info("Calling Claude to synthesize report...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    report = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    logger.info(f"Report generated: {len(report)} chars, {tokens} tokens")
    return report, tokens
