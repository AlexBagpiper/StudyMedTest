"""
Integration tests for the registration flow.

Uses the FastAPI test client from `tests/conftest.py` plus fakeredis from
`registration/conftest.py`. Rate limiting is disabled per-test to avoid
interference across parametrizations.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.otp import _otp_key, otp_service
from app.models.user import User
from tests.registration.conftest import register_payload

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


async def test_register_returns_200_and_dispatches_email(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    res = await client.post("/api/v1/auth/register", json=register_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "student@example.com"
    assert body["resend_after"] > 0
    assert "verification" in body["message"].lower() or "код" in body["message"].lower()

    assert len(captured_emails) == 1
    assert captured_emails[0].kind == "verification"
    assert captured_emails[0].to == "student@example.com"
    assert captured_emails[0].payload["code"].isdigit()


async def test_verify_correct_code_creates_user(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())
    code = captured_emails[0].payload["code"]

    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": code,
    })
    assert res.status_code == 200

    # User should now exist in the DB.
    found = (await db.execute(select(User).where(User.email == "student@example.com"))).scalar_one_or_none()
    assert found is not None
    assert found.is_verified is True
    assert found.role.value == "student"

    # OTP key is gone.
    assert await fake_redis.exists(_otp_key("student@example.com")) == 0


async def test_register_idempotent_same_password(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """Second register with same email+password reuses the existing code."""
    await client.post("/api/v1/auth/register", json=register_payload())
    first_code = captured_emails[0].payload["code"]

    # Second call within cooldown: no new email dispatched.
    res = await client.post("/api/v1/auth/register", json=register_payload())
    assert res.status_code == 200
    assert res.json()["resend_after"] > 0
    assert len(captured_emails) == 1  # no duplicate

    # Verify using the ORIGINAL code still works.
    verify = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": first_code,
    })
    assert verify.status_code == 200


async def test_register_with_conflicting_password_does_not_overwrite_draft(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """
    Account hijacking defense (audit §2.2): attacker cannot overwrite the
    victim's draft with their own password.
    """
    await client.post("/api/v1/auth/register", json=register_payload(password="Legit123"))
    first_code = captured_emails[0].payload["code"]

    # Attacker submits a different password.
    res = await client.post(
        "/api/v1/auth/register", json=register_payload(password="Hijacker456")
    )
    assert res.status_code == 200  # uniform response
    # No new email sent (we silently ignore the attacker).
    assert len(captured_emails) == 1

    # Original code still works.
    verify = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": first_code,
    })
    assert verify.status_code == 200


async def test_register_for_already_registered_email_generic_response(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """User enumeration defense (audit §2.5)."""
    # Pre-create a user
    from app.core.security import get_password_hash
    from app.models.user import Role, User as UserModel
    user = UserModel(
        email="student@example.com",
        password_hash=get_password_hash("existing"),
        last_name="X", first_name="Y", middle_name=None,
        role=Role.STUDENT, is_verified=True, is_active=True,
    )
    db.add(user)
    await db.flush()

    res = await client.post("/api/v1/auth/register", json=register_payload())
    assert res.status_code == 200  # not 400
    assert len(captured_emails) == 0  # no email sent


async def test_verify_wrong_code_shows_attempts_left(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())

    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": "000000",
    })
    assert res.status_code == 400
    assert str(settings.OTP_MAX_ATTEMPTS - 1) in res.json()["detail"]


async def test_verify_lockout_after_max_attempts(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())

    # Exhaust all attempts.
    for _ in range(settings.OTP_MAX_ATTEMPTS - 1):
        res = await client.post("/api/v1/auth/verify-email", json={
            "email": "student@example.com", "code": "000000",
        })
        assert res.status_code == 400

    # Final attempt: 429 (too many attempts), draft + OTP purged.
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": "000000",
    })
    assert res.status_code == 429


async def test_verify_with_expired_otp_returns_410(
    client: AsyncClient, fake_redis, email_sender, disable_rate_limit
):
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "nobody@example.com", "code": "123456",
    })
    assert res.status_code == 410


async def test_resend_within_cooldown_uses_same_code(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())

    res = await client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
    assert res.status_code == 200
    assert res.json()["resend_after"] > 0
    # Cooldown → no new email.
    assert len(captured_emails) == 1


async def test_resend_after_cooldown_sends_new_code(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())
    first_code = captured_emails[0].payload["code"]

    # Backdate last_resend_at to simulate cooldown elapsed.
    import time
    key = _otp_key("student@example.com")
    await fake_redis.hset(key, "last_resend_at", str(time.time() - 999))

    res = await client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
    assert res.status_code == 200
    assert len(captured_emails) == 2
    new_code = captured_emails[1].payload["code"]
    assert new_code != first_code

    # OLD code is now invalid (§2.2 avoided: not by overwriting on register, but
    # resend explicitly rotates).
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": first_code,
    })
    assert res.status_code == 400  # wrong code, attempts incremented


async def test_resend_for_already_registered_uniform_response(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    from app.core.security import get_password_hash
    from app.models.user import Role, User as UserModel
    user = UserModel(
        email="student@example.com",
        password_hash=get_password_hash("existing"),
        last_name="X", first_name="Y", middle_name=None,
        role=Role.STUDENT, is_verified=True, is_active=True,
    )
    db.add(user)
    await db.flush()

    res = await client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
    assert res.status_code == 200
    assert len(captured_emails) == 0


async def test_register_rejects_role_field(
    client: AsyncClient, fake_redis, email_sender, disable_rate_limit
):
    """StudentRegisterSchema has extra=forbid — passing role yields 422."""
    payload = register_payload()
    payload["role"] = "admin"
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


async def test_register_password_too_short(client: AsyncClient, fake_redis, email_sender, disable_rate_limit):
    payload = register_payload(password="abc")
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


async def test_register_invalid_email(client: AsyncClient, fake_redis, email_sender, disable_rate_limit):
    payload = register_payload(email="not-an-email")
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


async def test_verify_when_user_already_exists_returns_success(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """
    Simulates the race from audit §2.6: between verify-email start and commit,
    the user has already been created by a parallel request. The response must
    be 200, not 500.
    """
    await client.post("/api/v1/auth/register", json=register_payload())
    code = captured_emails[0].payload["code"]

    # Pre-create the user "manually" (as if another request finished first).
    from app.core.security import get_password_hash
    from app.models.user import Role, User as UserModel
    user = UserModel(
        email="student@example.com",
        password_hash=get_password_hash("Secret123"),
        last_name="Иванов", first_name="Иван", middle_name="Иванович",
        role=Role.STUDENT, is_verified=True, is_active=True,
    )
    db.add(user)
    await db.flush()

    # Even though the OTP exists in Redis, the endpoint should short-circuit.
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": code,
    })
    assert res.status_code == 200
    # Message is localized (RU) — check for the canonical word.
    assert "подтвержд" in res.json()["message"].lower()


async def test_login_after_verify_works(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    await client.post("/api/v1/auth/register", json=register_payload())
    code = captured_emails[0].payload["code"]

    await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": code,
    })

    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "student@example.com", "password": "Secret123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
