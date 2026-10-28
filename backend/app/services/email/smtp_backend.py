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
from typing import Optional

from app.core.config import settings
from app.services.email.templates import RenderedEmail

logger = logging.getLogger(__name__)

# RFC 2606 / 6761 reserved names. Sending to these from prod (deploy --smoke,
# locust, agent DNS probes) hits a null MX on example.com and floods postmaster
# with DSNs. Skip at the SMTP layer so OTP/queue tests still succeed.
_RESERVED_DOMAINS = frozenset({
    "example.com",
    "example.net",
    "example.org",
    "example.edu",
    "invalid",
    "test",
    "localhost",
})


def _is_reserved_recipient(to_email: str) -> bool:
    domain = to_email.rsplit("@", 1)[-1].lower().rstrip(".")
    if domain in _RESERVED_DOMAINS:
        return True
    return any(domain.endswith("." + reserved) for reserved in _RESERVED_DOMAINS)


def _to_address_safe(to_email: str) -> str:
    # Final defensive check for CRLF injection in recipient addresses.
    if "\r" in to_email or "\n" in to_email:
        raise ValueError("Invalid characters in recipient email")
    return to_email


# Implicit TLS only. OTP must not travel plaintext SMTP (25) or HTTP APIs.
_SMTPS_PORT = 465

# Yandex Cloud allows outbound TCP/25 only to Yandex Mail MX. Direct delivery
# from this VM to Gmail/Mail.ru times out; those need Яндекс 360 SMTPS 465.
_YANDEX_MAIL_DOMAINS = frozenset({
    "yandex.ru",
    "yandex.com",
    "yandex.net",
    "ya.ru",
})


def _recipient_domain(to_email: str) -> str:
    return to_email.rsplit("@", 1)[-1].lower().rstrip(".")


def _is_yandex_mail(to_email: str) -> bool:
    domain = _recipient_domain(to_email)
    if domain in _YANDEX_MAIL_DOMAINS:
        return True
    return any(domain.endswith("." + d) for d in _YANDEX_MAIL_DOMAINS)


def _smtp_target() -> tuple[str, int, Optional[str], Optional[str]]:
    """Яндекс 360 SMTPS 465 smarthost, else local mox SMTPS 465."""
    if settings.SMTP_RELAY_HOST:
        host = settings.SMTP_RELAY_HOST
        port = int(settings.SMTP_RELAY_PORT or _SMTPS_PORT)
        user, password = settings.SMTP_RELAY_USER, settings.SMTP_RELAY_PASSWORD
    else:
        host = settings.SMTP_HOST or ""
        port = int(settings.SMTP_PORT or _SMTPS_PORT)
        user, password = settings.SMTP_USER, settings.SMTP_PASSWORD
    if port != _SMTPS_PORT:
        raise ValueError(
            f"OTP mail requires SMTPS port {_SMTPS_PORT}, not {port} (no HTTP/plain SMTP)"
        )
    return host, port, user, password


def send_blocking(to_email: str, rendered: RenderedEmail) -> bool:
    """
    Synchronous SMTP send. Returns True on success, False on failure.
    Raises only for programmer errors (invalid input), never for network.
    """
    to_email = _to_address_safe(to_email)

    if _is_reserved_recipient(to_email):
        logger.info("email.skipped reserved-domain to=%s", to_email)
        return True

    if (
        settings.SMTP_REQUIRE_RELAY
        and settings.ENVIRONMENT == "production"
        and not settings.SMTP_RELAY_HOST
        and not _is_yandex_mail(to_email)
    ):
        raise RuntimeError(
            "Yandex Cloud blocks outbound TCP/25 to this MX; "
            "set SMTP_RELAY_HOST=smtp.yandex.ru (Яндекс 360, SMTPS 465)"
        )

    # Dev mode: pretty-print instead of sending.
    if settings.ENVIRONMENT == "development" or not (
        settings.SMTP_HOST or settings.SMTP_RELAY_HOST
    ):
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

        host, port, user, password = _smtp_target()
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            if user and password:
                server.login(user, password)
            server.sendmail(
                settings.SMTP_FROM or "no-reply@localhost", [to_email], msg.as_string()
            )
        logger.info("email.sent to=%s via=%s:%s", to_email, host, port)
        return True
    except Exception as exc:  # noqa: BLE001 — we want to log and fail gracefully
        logger.error("email.failed to=%s error=%s", to_email, exc)
        raise
