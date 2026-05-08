"""
Celery tasks for outbound email.

Design notes:
- Routed to dedicated queue "email" (see celery_app.py) so that long LLM
  evaluation jobs don't starve email delivery.
- task_acks_late=True — if the worker crashes mid-send, the broker redelivers.
- autoretry_for catches transient errors (smtplib.SMTPException, socket.timeout,
  ConnectionError) with exponential backoff + jitter.
- max_retries=3 keeps total delivery time bounded (~14s in worst case).
"""

from __future__ import annotations

import logging
import smtplib
import socket
from typing import Optional

from app.services.email.smtp_backend import send_blocking
from app.services.email.templates import (
    render_email_change,
    render_teacher_account_created,
    render_teacher_application_notification,
    render_teacher_application_rejected,
    render_verification_email,
)
from app.tasks.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.audit_service import audit_service
import asyncio

logger = logging.getLogger(__name__)

def run_async(coro):
    """Безопасный запуск асинхронного кода из синхронной среды Celery"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

_RETRY_EXCEPTIONS = (
    smtplib.SMTPException,
    socket.timeout,
    ConnectionError,
    OSError,
)


@celery_app.task(
    name="email.send_verification",
    bind=True,
    autoretry_for=_RETRY_EXCEPTIONS,
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    queue="email",
)
def send_verification_email_task(self, to_email: str, code: str) -> None:
    rendered = render_verification_email(code)
    
    async def _log_and_send():
        async with AsyncSessionLocal() as db:
            try:
                # В Celery у нас нет Request, поэтому используем log_event напрямую
                send_blocking(to_email, rendered)
                await audit_service.log_event(
                    db=db,
                    action="email.sent",
                    details={"email": to_email, "type": "verification"}
                )
                await db.commit()
            except Exception as e:
                await audit_service.log_event(
                    db=db,
                    action="email.failed",
                    details={"email": to_email, "type": "verification", "error": str(e)}
                )
                await db.commit()
                raise e

    run_async(_log_and_send())


@celery_app.task(
    name="email.send_email_change",
    bind=True,
    autoretry_for=_RETRY_EXCEPTIONS,
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    queue="email",
)
def send_email_change_task(self, to_email: str, code: str) -> None:
    rendered = render_email_change(code, to_email)
    
    async def _log_and_send():
        async with AsyncSessionLocal() as db:
            try:
                send_blocking(to_email, rendered)
                await audit_service.log_event(
                    db=db,
                    action="email.sent",
                    details={"email": to_email, "type": "email_change"}
                )
                await db.commit()
            except Exception as e:
                await audit_service.log_event(
                    db=db,
                    action="email.failed",
                    details={"email": to_email, "type": "email_change", "error": str(e)}
                )
                await db.commit()
                raise e

    run_async(_log_and_send())


@celery_app.task(
    name="email.send_teacher_application_notification",
    bind=True,
    autoretry_for=_RETRY_EXCEPTIONS,
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    queue="email",
)
def send_teacher_application_notification_task(
    self, admin_email: str, teacher_email: str, full_name: str
) -> None:
    rendered = render_teacher_application_notification(teacher_email, full_name)
    send_blocking(admin_email, rendered)


@celery_app.task(
    name="email.send_teacher_account_created",
    bind=True,
    autoretry_for=_RETRY_EXCEPTIONS,
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    queue="email",
)
def send_teacher_account_created_task(
    self, teacher_email: str, full_name: str, temporary_password: str
) -> None:
    rendered = render_teacher_account_created(full_name, teacher_email, temporary_password)
    send_blocking(teacher_email, rendered)


@celery_app.task(
    name="email.send_teacher_application_rejected",
    bind=True,
    autoretry_for=_RETRY_EXCEPTIONS,
    retry_backoff=2,
    retry_backoff_max=30,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    queue="email",
)
def send_teacher_application_rejected_task(
    self,
    teacher_email: str,
    full_name: str,
    admin_comment: Optional[str] = None,
) -> None:
    rendered = render_teacher_application_rejected(full_name, admin_comment)
    send_blocking(teacher_email, rendered)
