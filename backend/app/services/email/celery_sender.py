"""
CeleryEmailSender — non-blocking dispatch. Every call enqueues a job and
returns immediately. Worker handles the actual SMTP send with retry/backoff.

We import task callables lazily to avoid circular imports (celery_app imports
app.core.config, which pulls settings).
"""

from __future__ import annotations

from typing import Optional

from app.services.email.base import EmailSender


class CeleryEmailSender(EmailSender):
    async def send_verification(self, to_email: str, code: str) -> None:
        from app.tasks.email_tasks import send_verification_email_task

        send_verification_email_task.delay(to_email, code)

    async def send_email_change(self, to_email: str, code: str) -> None:
        from app.tasks.email_tasks import send_email_change_task

        send_email_change_task.delay(to_email, code)

    async def send_teacher_application_notification(
        self, admin_email: str, teacher_email: str, full_name: str
    ) -> None:
        from app.tasks.email_tasks import send_teacher_application_notification_task

        send_teacher_application_notification_task.delay(admin_email, teacher_email, full_name)

    async def send_teacher_account_created(
        self, teacher_email: str, full_name: str, temporary_password: str
    ) -> None:
        from app.tasks.email_tasks import send_teacher_account_created_task

        send_teacher_account_created_task.delay(teacher_email, full_name, temporary_password)

    async def send_teacher_application_rejected(
        self,
        teacher_email: str,
        full_name: str,
        admin_comment: Optional[str] = None,
    ) -> None:
        from app.tasks.email_tasks import send_teacher_application_rejected_task

        send_teacher_application_rejected_task.delay(teacher_email, full_name, admin_comment)
