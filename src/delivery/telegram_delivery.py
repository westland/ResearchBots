import logging

from core.config import AppConfig
from utils.http_client import http

logger = logging.getLogger(__name__)


def send(report: str, config: AppConfig):
    cfg = config.delivery
    if not cfg.telegram_enabled:
        return
    if not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        logger.warning("Telegram enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return

    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    # Telegram limit is 4096 chars per message
    chunks = [report[i : i + 4000] for i in range(0, len(report), 4000)]

    for i, chunk in enumerate(chunks):
        try:
            resp = http.post(
                url,
                json={
                    "chat_id": cfg.telegram_chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            resp.raise_for_status()
            logger.info(f"Telegram: sent part {i + 1}/{len(chunks)}")
        except Exception as exc:
            logger.error(f"Telegram delivery failed (part {i + 1}): {exc}")
