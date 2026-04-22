"""
Security tests for registration: brute-force, timing, log hygiene, input sanitization.
"""

from __future__ import annotations

import logging

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.registration.conftest import register_payload

pytestmark = [pytest.mark.security, pytest.mark.asyncio]


async def test_brute_force_6digit_blocked_at_max_attempts(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())

    responses = []
    for i in range(settings.OTP_MAX_ATTEMPTS + 2):
        responses.append(await client.post("/api/v1/auth/verify-email", json={
            "email": "student@example.com",
            "code": f"{(i + 1) * 111 % 1000000:06d}",
        }))

    # First OTP_MAX_ATTEMPTS-1 are 400, then 429 (lockout), rest are 410 (gone).
    statuses = [r.status_code for r in responses]
    assert statuses.count(400) <= settings.OTP_MAX_ATTEMPTS - 1
    assert 429 in statuses


async def test_response_identical_for_new_and_existing_email(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """User enumeration defense: same status + same shape."""
    from app.core.security import get_password_hash
    from app.models.user import Role, User as UserModel
    existing = UserModel(
        email="known@example.com",
        password_hash=get_password_hash("pw"),
        last_name="X", first_name="Y", middle_name=None,
        role=Role.STUDENT, is_verified=True, is_active=True,
    )
    db.add(existing)
    await db.flush()

    r_new = await client.post("/api/v1/auth/register", json=register_payload(email="fresh@example.com"))
    r_existing = await client.post("/api/v1/auth/register", json=register_payload(email="known@example.com"))

    assert r_new.status_code == r_existing.status_code == 200
    assert set(r_new.json().keys()) == set(r_existing.json().keys())
    assert r_new.json()["message"] == r_existing.json()["message"]


async def test_otp_not_logged_in_production(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit,
    monkeypatch, caplog,
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
    with caplog.at_level(logging.INFO):
        await client.post("/api/v1/auth/register", json=register_payload())

    code = captured_emails[0].payload["code"]
    # Code must not appear anywhere in log messages.
    for record in caplog.records:
        assert code not in record.getMessage()
    # "dev_code" marker should not appear either.
    assert not any("dev_code" in r.getMessage() for r in caplog.records)


async def test_dev_code_absent_in_response_in_production(
    client: AsyncClient, fake_redis, email_sender, disable_rate_limit, monkeypatch
):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production", raising=False)
    res = await client.post("/api/v1/auth/register", json=register_payload())
    assert "dev_code" not in res.json()
    res2 = await client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
    assert "dev_code" not in res2.json()


async def test_password_hash_never_in_response(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    res = await client.post("/api/v1/auth/register", json=register_payload())
    body = res.text
    assert "password_hash" not in body
    assert "$2b$" not in body  # bcrypt signature


async def test_email_case_and_whitespace_dedup(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """Bypass defense: `User@X.com` must map to the same OTP as `user@x.com`."""
    await client.post("/api/v1/auth/register", json=register_payload(email="Student@Example.com"))
    code = captured_emails[0].payload["code"]

    # Verify with differently cased email must still succeed.
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": code,
    })
    assert res.status_code == 200


async def test_empty_code_is_rejected(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": "",
    })
    # Pydantic min_length=6 → 422 before reaching the service.
    assert res.status_code == 422


async def test_code_with_letters_rejected_without_consuming_attempt(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """Malformed code returns invalid without bumping the Redis counter."""
    await client.post("/api/v1/auth/register", json=register_payload())
    # Pydantic schema allows min=6 max=6 chars but not digit-only; our service
    # short-circuits with INVALID_CODE without incrementing attempts.
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": "abcdef",
    })
    assert res.status_code == 400

    from app.core.otp import _otp_key
    attempts = await fake_redis.hget(_otp_key("student@example.com"), "attempts")
    assert attempts == "0"
