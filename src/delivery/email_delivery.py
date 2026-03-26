import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown as md

from core.config import AppConfig

logger = logging.getLogger(__name__)


def send(report: str, config: AppConfig):
    cfg = config.delivery
    if not cfg.email_enabled:
        return
    if not cfg.email_from or not cfg.email_to or not cfg.email_password:
        logger.warning("Email enabled but EMAIL_ADDRESS, EMAIL_PASSWORD, or to_addresses not set")
        return

    product_name = config.product.name
    date_str = datetime.utcnow().strftime("%B %d, %Y")
    subject = f"Daily Research Report: {product_name} — {date_str}"

    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; padding: 20px;">
    <h2 style="color: #333;">Daily Research Report: {product_name}</h2>
    <p style="color: #666; font-size: 13px;">{date_str}</p>
    <hr style="border: none; border-top: 1px solid #eee;">
    {md.markdown(report)}
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.email_from
    msg["To"] = ", ".join(cfg.email_to)
    msg.attach(MIMEText(report, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(cfg.email_smtp_host, cfg.email_smtp_port, timeout=20) as server:
            server.starttls()
            server.login(cfg.email_from, cfg.email_password)
            server.sendmail(cfg.email_from, cfg.email_to, msg.as_string())
        logger.info(f"Email sent to {cfg.email_to}")
    except Exception as exc:
        logger.error(f"Email delivery failed: {exc}")
