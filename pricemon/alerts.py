"""Alert engine — notification dispatch for price alerts.

Supports:
- Console output (always)
- Email via SMTP (if configured)
- Webhook POST (if configured)
"""

import json
import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any

import requests

logger = logging.getLogger(__name__)


def dispatch_alert(alert_data: dict, target: dict | None = None) -> None:
    """Dispatch an alert through all configured channels.

    Args:
        alert_data: Dict with alert_type, severity, message, old_price, new_price, change_pct.
        target: Optional target dict for enrichment.
    """
    # Always log to console
    console_msg = (
        f"[{alert_data.get('severity', 'info').upper()}] "
        f"{alert_data.get('message', '')}"
    )
    print(console_msg)

    # Email (if configured)
    _try_email_alert(alert_data, target)

    # Webhook (if configured)
    _try_webhook_alert(alert_data, target)


def _try_email_alert(alert_data: dict, target: dict | None = None) -> None:
    """Send alert via email if SMTP is configured in .env."""
    smtp_host = os.getenv("ALERT_SMTP_HOST")
    smtp_port = os.getenv("ALERT_SMTP_PORT", "587")
    smtp_user = os.getenv("ALERT_SMTP_USER")
    smtp_pass = os.getenv("ALERT_SMTP_PASS")
    smtp_to = os.getenv("ALERT_SMTP_TO")

    if not all([smtp_host, smtp_user, smtp_pass, smtp_to]):
        return  # Not configured, skip

    try:
        subject = f"[价格告警] {alert_data.get('message', '')[:50]}"
        body = (
            f"告警类型: {alert_data.get('alert_type')}\n"
            f"严重级别: {alert_data.get('severity')}\n"
            f"消息: {alert_data.get('message')}\n"
            f"旧价格: {alert_data.get('old_price')}\n"
            f"新价格: {alert_data.get('new_price')}\n"
        )
        if target:
            body += f"商品: {target.get('name')}\nURL: {target.get('url')}\n"

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = smtp_to

        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info("Email alert sent to %s", smtp_to)
    except Exception as e:
        logger.warning("Failed to send email alert: %s", e)


def _try_webhook_alert(alert_data: dict, target: dict | None = None) -> None:
    """Send alert via webhook POST if URL is configured."""
    webhook_url = os.getenv("ALERT_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "event": "price_alert",
        "timestamp": alert_data.get("created_at", ""),
        "alert": {
            "type": alert_data.get("alert_type"),
            "severity": alert_data.get("severity"),
            "message": alert_data.get("message"),
            "old_price": alert_data.get("old_price"),
            "new_price": alert_data.get("new_price"),
            "change_pct": alert_data.get("change_pct"),
        },
    }
    if target:
        payload["target"] = {
            "id": target.get("id"),
            "name": target.get("name"),
            "url": target.get("url"),
        }

    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        logger.info("Webhook alert sent to %s (status %s)", webhook_url, resp.status_code)
    except Exception as e:
        logger.warning("Failed to send webhook alert: %s", e)
