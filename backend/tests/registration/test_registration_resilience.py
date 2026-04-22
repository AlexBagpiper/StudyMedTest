"""
Fault-tolerance / resilience tests.

Covered without extra infra:
- SMTP down → register still returns 200 (error swallowed, retry handled in Celery).
- Flaky email sender triggers retries.
- Celery-eager mode runs tasks synchronously for assertion.

Scaffolds requiring `testcontainers` are included but marked xfail_missing so
CI can enable them incrementally.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.registration.conftest import register_payload

pytestmark = [pytest.mark.resilience, pytest.mark.asyncio]


async def test_smtp_outage_register_still_returns_200(
    client: AsyncClient, fake_redis, flaky_email_sender, captured_emails, disable_rate_limit
):
    """
    Email sender raises ConnectionError on first call. The register endpoint
    must not leak a 500 to the user; it accepts the registration and relies on
    Celery retry / user-triggered resend to eventually deliver.
    """
    sender = flaky_email_sender(fail_times=1)
    res = await client.post("/api/v1/auth/register", json=register_payload())
    assert res.status_code == 200
    # The failure consumed the call, so captured_emails is still empty.
    assert len(captured_emails) == 0

    # A resend attempt works because the next call doesn't fail anymore.
    # But cooldown blocks the resend — we first need to bypass it.
    import time
    from app.core.otp import _otp_key
    key = _otp_key("student@example.com")
    await fake_redis.hset(key, "last_resend_at", str(time.time() - 999))

    res = await client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
    assert res.status_code == 200
    assert len(captured_emails) == 1


async def test_celery_task_autoretry_on_smtp_failure(monkeypatch):
    """
    The verification task is wired with autoretry_for=(SMTPException, ...).
    We simulate failure and ensure Celery would retry. Runs in eager mode to
    keep the test self-contained.
    """
    import smtplib
    from celery import Celery

    from app.tasks import email_tasks

    calls = {"n": 0}

    def flaky_send(to_email, rendered):
        calls["n"] += 1
        if calls["n"] < 3:
            raise smtplib.SMTPException("boom")
        return True

    monkeypatch.setattr(email_tasks, "send_blocking", flaky_send)

    # Run in eager mode: task body executed synchronously in the caller.
    email_tasks.celery_app.conf.task_always_eager = True
    email_tasks.celery_app.conf.task_eager_propagates = False
    try:
        result = email_tasks.send_verification_email_task.apply(args=["u@x.com", "123456"])
        # After retries, final outcome either SUCCESS or FAILURE — we only care
        # that the task invoked send_blocking more than once (retry fired).
        assert calls["n"] >= 2
    finally:
        email_tasks.celery_app.conf.task_always_eager = False


@pytest.mark.skip(reason="requires testcontainers for real Redis/Postgres")
async def test_redis_restart_preserves_rate_limit_counters():
    """
    Start a real Redis container, hit /register N times, stop+start Redis
    with AOF persistence, verify counters survived.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="requires testcontainers + running Celery worker")
async def test_worker_crash_redelivers_task_with_acks_late():
    """
    Spawn a Celery worker, dispatch a task that hangs, SIGKILL the worker,
    restart, expect broker to redeliver (acks_late=True).
    """
    raise NotImplementedError


@pytest.mark.skip(reason="requires running backend + MailHog container")
async def test_queue_backpressure_does_not_block_api():
    """
    Push 1000 email tasks into the queue, measure /register latency — must
    remain < 100ms at p95.
    """
    raise NotImplementedError
