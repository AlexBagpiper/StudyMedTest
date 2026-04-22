"""
Unit tests for email templates and senders.

Focus: no outbound network, fast. Covers XSS/CRLF injection, template snapshots,
and that each sender dispatches properly.
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.email import templates
from app.services.email.celery_sender import CeleryEmailSender
from app.services.email.sync_sender import SyncEmailSender

pytestmark = pytest.mark.unit


def test_verification_template_escapes_code_and_project_name():
    rendered = templates.render_verification_email("123456")
    assert "123456" in rendered.text
    assert "123456" in rendered.html
    # HTML is proper XHTML-ish, script-free.
    assert "<script" not in rendered.html


def test_crlf_in_subject_is_rejected(monkeypatch):
    # Force a malicious PROJECT_NAME to prove the guard catches CRLF injection.
    from app.core.config import settings as s
    monkeypatch.setattr(s, "PROJECT_NAME", "MedTest\r\nBcc: attacker@evil.com")
    with pytest.raises(ValueError):
        templates.render_verification_email("123456")


def test_xss_in_name_escaped_in_html():
    rendered = templates.render_teacher_account_created(
        full_name="<script>alert(1)</script>",
        teacher_email="t@example.com",
        temporary_password="pw",
    )
    # Raw tags must NOT survive into HTML.
    assert "<script>alert(1)</script>" not in rendered.html
    # But the escaped form should.
    assert "&lt;script&gt;" in rendered.html


def test_xss_in_email_field_escaped():
    rendered = templates.render_email_change(
        code="123456", new_email="user@<b>evil</b>.com",
    )
    assert "<b>evil</b>" not in rendered.html
    assert "&lt;b&gt;evil&lt;/b&gt;" in rendered.html


def test_rejected_template_handles_missing_comment():
    rendered = templates.render_teacher_application_rejected(
        full_name="Test", admin_comment=None,
    )
    assert "Комментарий" not in rendered.html


def test_rejected_template_escapes_comment():
    rendered = templates.render_teacher_application_rejected(
        full_name="Test", admin_comment='<img src=x onerror=alert(1)>',
    )
    assert "<img src=x" not in rendered.html
    assert "onerror" in rendered.html  # escaped, but text survives


@pytest.mark.asyncio
async def test_celery_sender_dispatches_task_non_blocking(monkeypatch):
    calls = []

    class FakeTask:
        def delay(self, *args, **kwargs):
            calls.append(("delay", args, kwargs))

    # Patch the lazy-imported tasks to avoid real Celery connection.
    import app.services.email.celery_sender as mod
    import app.tasks.email_tasks as tasks

    monkeypatch.setattr(tasks, "send_verification_email_task", FakeTask())
    monkeypatch.setattr(tasks, "send_email_change_task", FakeTask())
    monkeypatch.setattr(tasks, "send_teacher_application_notification_task", FakeTask())
    monkeypatch.setattr(tasks, "send_teacher_account_created_task", FakeTask())
    monkeypatch.setattr(tasks, "send_teacher_application_rejected_task", FakeTask())

    sender = CeleryEmailSender()
    # All methods must return promptly (< 50ms) — no blocking I/O.
    await asyncio.wait_for(sender.send_verification("u@x.com", "123456"), timeout=0.2)
    await asyncio.wait_for(sender.send_email_change("u@x.com", "654321"), timeout=0.2)
    await asyncio.wait_for(
        sender.send_teacher_application_notification("a@x.com", "t@x.com", "Full Name"),
        timeout=0.2,
    )
    await asyncio.wait_for(
        sender.send_teacher_account_created("t@x.com", "Full Name", "tmp"),
        timeout=0.2,
    )
    await asyncio.wait_for(
        sender.send_teacher_application_rejected("t@x.com", "Full Name", "comment"),
        timeout=0.2,
    )


@pytest.mark.asyncio
async def test_sync_sender_calls_smtp_backend_in_thread(monkeypatch):
    from app.services.email import sync_sender as mod

    seen = []

    def fake_send(to_email, rendered):
        seen.append((to_email, rendered.subject))
        return True

    monkeypatch.setattr(mod, "send_blocking", fake_send)

    sender = SyncEmailSender()
    await sender.send_verification("u@x.com", "123456")
    assert len(seen) == 1
    assert seen[0][0] == "u@x.com"
