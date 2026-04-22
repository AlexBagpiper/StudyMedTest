"""
Factory selects the concrete EmailSender based on settings.EMAIL_TRANSPORT.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.email.base import EmailSender


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    if settings.EMAIL_TRANSPORT == "sync":
        from app.services.email.sync_sender import SyncEmailSender

        return SyncEmailSender()

    from app.services.email.celery_sender import CeleryEmailSender

    return CeleryEmailSender()


def reset_email_sender_cache() -> None:
    """Hook for tests to force re-selection after flipping settings."""
    get_email_sender.cache_clear()
