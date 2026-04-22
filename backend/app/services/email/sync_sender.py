"""
SyncEmailSender — runs blocking SMTP in a thread to avoid blocking the event
loop. Intended for tests, dev setups without Celery, or as a fallback.

For production prefer CeleryEmailSender (retries, durability, back-pressure).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from app.services.email.base import EmailSender
from app.services.email.smtp_backend import send_blocking
from app.services.email.templates import (
    render_email_change,
    render_teacher_account_created,
    render_teacher_application_notification,
    render_teacher_application_rejected,
    render_verification_email,
)


class SyncEmailSender(EmailSender):
    async def send_verification(self, to_email: str, code: str) -> None:
        rendered = render_verification_email(code)
        await asyncio.to_thread(send_blocking, to_email, rendered)

    async def send_email_change(self, to_email: str, code: str) -> None:
        rendered = render_email_change(code, to_email)
        await asyncio.to_thread(send_blocking, to_email, rendered)

    async def send_teacher_application_notification(
        self, admin_email: str, teacher_email: str, full_name: str
    ) -> None:
        rendered = render_teacher_application_notification(teacher_email, full_name)
        await asyncio.to_thread(send_blocking, admin_email, rendered)

    async def send_teacher_account_created(
        self, teacher_email: str, full_name: str, temporary_password: str
    ) -> None:
        rendered = render_teacher_account_created(full_name, teacher_email, temporary_password)
        await asyncio.to_thread(send_blocking, teacher_email, rendered)

    async def send_teacher_application_rejected(
        self,
        teacher_email: str,
        full_name: str,
        admin_comment: Optional[str] = None,
    ) -> None:
        rendered = render_teacher_application_rejected(full_name, admin_comment)
        await asyncio.to_thread(send_blocking, teacher_email, rendered)
