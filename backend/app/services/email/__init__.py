"""
Email subsystem.

Public API:
    get_email_sender() -> EmailSender (selected by settings.EMAIL_TRANSPORT)

Senders are Strategy pattern (DIP): auth endpoints depend on the abstract
EmailSender, never on smtplib or Celery directly.
"""

from app.services.email.base import EmailSender
from app.services.email.factory import get_email_sender

__all__ = ["EmailSender", "get_email_sender"]
