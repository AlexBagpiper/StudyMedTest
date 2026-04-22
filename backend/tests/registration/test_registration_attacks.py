"""
Attack-scenario tests: email bombing, rate-limit bypass, header injection.

Requires the slowapi limiter to be ON (via the `enable_rate_limit` fixture).
"""

from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.registration.conftest import register_payload

pytestmark = [pytest.mark.security, pytest.mark.asyncio]


async def test_email_bombing_blocked_by_cooldown(
    client: AsyncClient, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """
    100 resend calls in quick succession → cooldown prevents dispatch;
    only the initial register email is sent.
    """
    await client.post("/api/v1/auth/register", json=register_payload())
    initial = len(captured_emails)

    results = await asyncio.gather(*[
        client.post("/api/v1/auth/resend-verification", json={"email": "student@example.com"})
        for _ in range(100)
    ])
    assert all(r.status_code == 200 for r in results)
    assert len(captured_emails) == initial, "cooldown bypass detected"


async def test_register_rate_limit_per_ip_triggers_429(
    client: AsyncClient, fake_redis, email_sender, captured_emails, enable_rate_limit
):
    """
    Register is limited to REGISTER_RATE_LIMIT_PER_IP (e.g. 10/hour).
    The 11th request from the same IP must be 429.
    """
    # Send 12 distinct emails so we don't also trigger the per-email path.
    emails = [f"flood{i}@example.com" for i in range(12)]
    responses = []
    for em in emails:
        responses.append(await client.post("/api/v1/auth/register", json=register_payload(email=em)))

    statuses = [r.status_code for r in responses]
    # At least one 429 should fire within the first 12 requests.
    assert 429 in statuses
    # But the first few must succeed (policy is > 0 per window).
    assert 200 in statuses


async def test_verify_rate_limit_triggers_429(
    client: AsyncClient, fake_redis, email_sender, captured_emails, enable_rate_limit
):
    """Verify is rate-limited per IP to prevent distributed code guessing."""
    await client.post("/api/v1/auth/register", json=register_payload())

    # Hammer 40 requests — should include at least one 429 given
    # VERIFY_RATE_LIMIT_PER_IP default of "30/minute".
    statuses = []
    for _ in range(40):
        r = await client.post("/api/v1/auth/verify-email", json={
            "email": "student@example.com", "code": "000000",
        })
        statuses.append(r.status_code)

    assert 429 in statuses


async def test_header_injection_in_email_rejected(
    client: AsyncClient, fake_redis, email_sender, disable_rate_limit
):
    """CRLF in email is rejected by EmailStr validator before reaching SMTP."""
    payload = register_payload(email="user@example.com\r\nBcc: victim@x.com")
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 422


async def test_account_hijack_via_draft_overwrite_is_prevented(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    """
    Victim starts a registration. Attacker tries to hijack by re-registering
    with the same email but a different password. The victim's code still
    works; the attacker's password is not persisted.
    """
    await client.post(
        "/api/v1/auth/register", json=register_payload(password="VictimPw1")
    )
    victim_code = captured_emails[0].payload["code"]

    # Attacker attempts hijack.
    await client.post(
        "/api/v1/auth/register", json=register_payload(password="AttackerPw1")
    )

    # Victim verifies.
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": "student@example.com", "code": victim_code,
    })
    assert res.status_code == 200

    # Only the victim's password should work for login.
    victim_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "student@example.com", "password": "VictimPw1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert victim_login.status_code == 200

    attacker_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "student@example.com", "password": "AttackerPw1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert attacker_login.status_code == 401


async def test_xff_header_cannot_bypass_rate_limit(
    client: AsyncClient, fake_redis, email_sender, captured_emails, enable_rate_limit
):
    """
    The limiter is keyed by direct client IP (request.client.host), not by
    X-Forwarded-For. Attacker rotating XFF cannot get more quota.
    """
    hits_200 = 0
    hits_429 = 0
    for i in range(40):
        res = await client.post(
            "/api/v1/auth/register",
            json=register_payload(email=f"xff{i}@example.com"),
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        )
        if res.status_code == 200:
            hits_200 += 1
        elif res.status_code == 429:
            hits_429 += 1

    assert hits_429 >= 1, "XFF rotation bypassed rate limit"
