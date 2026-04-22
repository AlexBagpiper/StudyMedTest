"""
EmailSender abstract interface (DIP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class EmailSender(ABC):
    """
    All outbound mail must go through this interface. Concrete transports
    (Celery, sync SMTP) implement these methods.
    """

    @abstractmethod
    async def send_verification(self, to_email: str, code: str) -> None:
        """Send registration-verification code."""

    @abstractmethod
    async def send_email_change(self, to_email: str, code: str) -> None:
        """Send email-change confirmation code."""

    @abstractmethod
    async def send_teacher_application_notification(
        self, admin_email: str, teacher_email: str, full_name: str
    ) -> None:
        ...

    @abstractmethod
    async def send_teacher_account_created(
        self, teacher_email: str, full_name: str, temporary_password: str
    ) -> None:
        ...

    @abstractmethod
    async def send_teacher_application_rejected(
        self,
        teacher_email: str,
        full_name: str,
        admin_comment: Optional[str] = None,
    ) -> None:
        ...
