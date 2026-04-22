"""
Unit tests for OtpService. Uses fakeredis so the Lua verify_and_consume script
runs end-to-end (fakeredis implements EVAL/EVALSHA).
"""

from __future__ import annotations

import asyncio
import time

import pytest

from app.core.config import settings
from app.core.otp import (
    OtpResult,
    OtpService,
    _hash_code,
    _otp_key,
    otp_service,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


async def test_issue_creates_key_with_hash_and_ttl(fake_redis):
    outcome = await otp_service.issue("user@example.com")

    assert outcome.code is not None
    assert len(outcome.code) == settings.OTP_LENGTH
    assert outcome.code.isdigit()
    assert outcome.reused is False

    stored = await fake_redis.hgetall(_otp_key("user@example.com"))
    # The plaintext code is NEVER stored.
    assert "code" not in stored
    assert stored["code_hash"] == _hash_code(outcome.code)

    ttl = await fake_redis.ttl(_otp_key("user@example.com"))
    assert settings.OTP_TTL_SECONDS - 2 <= ttl <= settings.OTP_TTL_SECONDS


async def test_issue_within_cooldown_returns_reused(fake_redis):
    first = await otp_service.issue("user@example.com")
    second = await otp_service.issue("user@example.com")

    assert first.code is not None
    assert second.code is None  # we never expose the active code twice
    assert second.reused is True
    assert second.resend_after > 0


async def test_issue_after_cooldown_generates_new_code(fake_redis):
    first = await otp_service.issue("user@example.com")
    # Manually backdate last_resend_at so cooldown appears expired
    key = _otp_key("user@example.com")
    await fake_redis.hset(key, "last_resend_at", str(time.time() - 999))

    second = await otp_service.issue("user@example.com")
    assert second.code is not None
    assert second.code != first.code
    assert second.reused is False


async def test_issue_hourly_cap_blocks_further_resends(fake_redis):
    email = "user@example.com"
    # Manually seed resend_count to cap while keeping issued_at inside the last hour.
    await otp_service.issue(email)
    key = _otp_key(email)
    await fake_redis.hset(key, mapping={
        "resend_count": str(settings.OTP_MAX_RESENDS_PER_HOUR),
        "issued_at": str(time.time() - 60),
        "last_resend_at": str(time.time() - 999),
    })

    outcome = await otp_service.issue(email)
    assert outcome.limited is True
    assert outcome.code is None


async def test_verify_correct_code_consumes_key(fake_redis):
    issued = await otp_service.issue("user@example.com")
    outcome = await otp_service.verify_and_consume("user@example.com", issued.code)

    assert outcome.result is OtpResult.OK
    stored = await fake_redis.hgetall(_otp_key("user@example.com"))
    assert stored == {}  # key deleted


async def test_verify_wrong_code_increments_attempts(fake_redis):
    await otp_service.issue("user@example.com")
    outcome = await otp_service.verify_and_consume("user@example.com", "000000")

    assert outcome.result is OtpResult.INVALID_CODE
    assert outcome.attempts_left == settings.OTP_MAX_ATTEMPTS - 1

    attempts = await fake_redis.hget(_otp_key("user@example.com"), "attempts")
    assert attempts == "1"


async def test_verify_locks_out_at_max_attempts(fake_redis):
    await otp_service.issue("user@example.com")

    for i in range(settings.OTP_MAX_ATTEMPTS - 1):
        result = await otp_service.verify_and_consume("user@example.com", "000000")
        assert result.result is OtpResult.INVALID_CODE
        assert result.attempts_left == settings.OTP_MAX_ATTEMPTS - 1 - i

    final = await otp_service.verify_and_consume("user@example.com", "000000")
    assert final.result is OtpResult.TOO_MANY_ATTEMPTS
    assert final.attempts_left == 0

    # Key removed — even the correct code now fails.
    stored = await fake_redis.exists(_otp_key("user@example.com"))
    assert stored == 0


async def test_verify_expired_or_missing_returns_not_found(fake_redis):
    outcome = await otp_service.verify_and_consume("nobody@example.com", "123456")
    assert outcome.result is OtpResult.NOT_FOUND


async def test_verify_malformed_code_is_invalid_without_incrementing(fake_redis):
    await otp_service.issue("user@example.com")

    outcome = await otp_service.verify_and_consume("user@example.com", "abc")
    assert outcome.result is OtpResult.INVALID_CODE
    # Redis counter NOT touched (we short-circuited).
    attempts = await fake_redis.hget(_otp_key("user@example.com"), "attempts")
    assert attempts == "0"


async def test_code_not_stored_plaintext(fake_redis):
    issued = await otp_service.issue("user@example.com")
    raw = await fake_redis.hgetall(_otp_key("user@example.com"))
    assert issued.code not in raw.values()


async def test_hmac_binds_code_to_secret_key(monkeypatch, fake_redis):
    issued = await otp_service.issue("user@example.com")

    # Simulate SECRET_KEY rotation — old hash must no longer match.
    monkeypatch.setattr(settings, "SECRET_KEY", "rotated-secret", raising=False)
    # Force a new service instance so any cached state is gone (not strictly
    # needed since the service holds only SHA cache, but keeps intent clear).
    svc = OtpService()
    outcome = await svc.verify_and_consume("user@example.com", issued.code)
    assert outcome.result is OtpResult.INVALID_CODE


async def test_email_case_and_whitespace_normalized(fake_redis):
    await otp_service.issue("User@Example.com")
    key = _otp_key(" USER@example.com ")
    assert await fake_redis.exists(key) == 1


async def test_concurrent_verify_exactly_one_success(fake_redis):
    """
    50 parallel verify calls with the CORRECT code: Lua guarantees only one OK.
    """
    issued = await otp_service.issue("user@example.com")
    results = await asyncio.gather(
        *[otp_service.verify_and_consume("user@example.com", issued.code) for _ in range(50)],
        return_exceptions=True,
    )
    oks = [r for r in results if not isinstance(r, Exception) and r.result is OtpResult.OK]
    nots = [r for r in results if not isinstance(r, Exception) and r.result is OtpResult.NOT_FOUND]

    assert len(oks) == 1
    assert len(oks) + len(nots) == 50


async def test_concurrent_wrong_verify_does_not_exceed_max_attempts(fake_redis):
    """
    Under concurrent wrong-code bombardment the attempts counter stays bounded:
    first 5 get INVALID_CODE, the 6th onwards return TOO_MANY_ATTEMPTS or NOT_FOUND.
    """
    await otp_service.issue("user@example.com")
    results = await asyncio.gather(
        *[otp_service.verify_and_consume("user@example.com", "000000") for _ in range(50)]
    )
    invalid = [r for r in results if r.result is OtpResult.INVALID_CODE]
    locked = [r for r in results if r.result is OtpResult.TOO_MANY_ATTEMPTS]
    not_found = [r for r in results if r.result is OtpResult.NOT_FOUND]

    assert len(invalid) <= settings.OTP_MAX_ATTEMPTS
    assert len(locked) >= 1
    assert len(invalid) + len(locked) + len(not_found) == 50


async def test_invalidate_removes_key(fake_redis):
    await otp_service.issue("user@example.com")
    await otp_service.invalidate("user@example.com")
    assert await fake_redis.exists(_otp_key("user@example.com")) == 0
