"""
Concurrency/race-condition tests for registration.

These exercise the critical guarantees:
- Idempotent register under parallel requests (§2.2).
- Atomic verify — exactly one success (§2.6).
- No 5xx under contention.
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.user import User
from tests.registration.conftest import register_payload

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_parallel_register_same_email_one_email_dispatched(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    results = await asyncio.gather(*[
        client.post("/api/v1/auth/register", json=register_payload())
        for _ in range(20)
    ])
    for r in results:
        assert r.status_code == 200

    # Only the very first request wins the "issue new code" branch.
    # The rest are within cooldown → no additional dispatches.
    assert len(captured_emails) == 1


async def test_parallel_verify_correct_code_exactly_one_user_created(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())
    code = captured_emails[0].payload["code"]

    results = await asyncio.gather(*[
        client.post("/api/v1/auth/verify-email", json={
            "email": "student@example.com", "code": code,
        })
        for _ in range(30)
    ])

    statuses = [r.status_code for r in results]
    assert 500 not in statuses, f"server crashed under concurrent verify: {statuses}"
    # Every response should be 200 (either first-wins OK or already-verified).
    assert all(s == 200 for s in statuses), f"unexpected statuses: {statuses}"

    count = (await db.execute(
        select(func.count()).select_from(User).where(User.email == "student@example.com")
    )).scalar_one()
    assert count == 1


async def test_parallel_wrong_code_does_not_exceed_attempts_cap(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    from app.core.config import settings

    await client.post("/api/v1/auth/register", json=register_payload())

    results = await asyncio.gather(*[
        client.post("/api/v1/auth/verify-email", json={
            "email": "student@example.com", "code": "000000",
        })
        for _ in range(50)
    ])

    codes = [r.status_code for r in results]
    assert 500 not in codes
    num_400 = codes.count(400)
    num_429 = codes.count(429)
    num_410 = codes.count(410)
    # Never more than OTP_MAX_ATTEMPTS invalid-code responses, and at least one
    # 429 (lockout) must have occurred.
    assert num_400 <= settings.OTP_MAX_ATTEMPTS
    assert num_429 + num_410 >= 1
    assert num_400 + num_429 + num_410 == 50


async def test_parallel_resend_under_cooldown_no_extra_emails(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())
    before = len(captured_emails)

    results = await asyncio.gather(*[
        client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
        for _ in range(10)
    ])
    for r in results:
        assert r.status_code == 200

    # Cooldown prevented any additional dispatch.
    assert len(captured_emails) == before
