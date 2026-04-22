"""
Low-level blocking SMTP backend. Called from both the Celery task (where the
worker runs sync code anyway) and the SyncEmailSender (wrapped in
asyncio.to_thread so it doesn't block the API event loop).

This is the ONLY place that imports smtplib.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.services.email.templates import RenderedEmail

logger = logging.getLogger(__name__)


def _to_address_safe(to_email: str) -> str:
    # Final defensive check for CRLF injection in recipient addresses.
    if "\r" in to_email or "\n" in to_email:
        raise ValueError("Invalid characters in recipient email")
    return to_email


def send_blocking(to_email: str, rendered: RenderedEmail) -> bool:
    """
    Synchronous SMTP send. Returns True on success, False on failure.
    Raises only for programmer errors (invalid input), never for network.
    """
    to_email = _to_address_safe(to_email)

    # Dev mode: pretty-print instead of sending.
    if settings.ENVIRONMENT == "development" or not settings.SMTP_HOST:
        logger.info("[DEV EMAIL] to=%s subject=%s", to_email, rendered.subject)
        print("\n" + "=" * 50)
        print("EMAIL (dev mode — not sent)")
        print(f"To: {to_email}")
        print(f"Subject: {rendered.subject}")
        print(rendered.text)
        print("=" * 50 + "\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = rendered.subject
        msg["From"] = settings.SMTP_FROM or "no-reply@localhost"
        msg["To"] = to_email
        msg.attach(MIMEText(rendered.text, "plain", "utf-8"))
        msg.attach(MIMEText(rendered.html, "html", "utf-8"))

        smtp_class = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_PORT != 465:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                settings.SMTP_FROM or "no-reply@localhost", [to_email], msg.as_string()
            )
        logger.info("email.sent to=%s", to_email)
        return True
    except Exception as exc:  # noqa: BLE001 — we want to log and fail gracefully
        logger.error("email.failed to=%s error=%s", to_email, exc)
        raise
