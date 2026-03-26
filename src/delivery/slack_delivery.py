import logging

from core.config import AppConfig
from utils.http_client import http

logger = logging.getLogger(__name__)


def send(report: str, config: AppConfig):
    cfg = config.delivery
    if not cfg.slack_enabled:
        return
    if not cfg.slack_webhook_url:
        logger.warning("Slack enabled but SLACK_WEBHOOK_URL not set")
        return

    product_name = config.product.name
    # Slack text block limit is 3000 chars
    body_text = report[:2900] + ("…" if len(report) > 2900 else "")

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Daily Research Report: {product_name}",
                },
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": body_text},
            },
        ]
    }

    try:
        resp = http.post(cfg.slack_webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info("Slack delivery successful")
    except Exception as exc:
        logger.error(f"Slack delivery failed: {exc}")
