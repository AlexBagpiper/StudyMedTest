"""
Atomic OTP service for email verification.

Design (SRP): one module is responsible only for generating, storing, comparing
and consuming one-time passwords. Business logic (user creation, email dispatch)
lives elsewhere.

Storage schema (Redis):

    reg:otp:{email}  -> HASH {
        code_hash:   hex sha256-hmac(SECRET_KEY, code),
        attempts:    int,
        resend_count: int,
        last_resend_at: unix ts (float seconds),
        issued_at:   unix ts (float seconds)
    }
    reg:otp:{email}  TTL = settings.OTP_TTL_SECONDS (but reset on new code)

All critical ops (verify + consume + attempts++ + lockout) are performed via a
single Lua EVAL to guarantee atomicity and eliminate TOCTOU (audit §2.6).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class OtpResult(str, Enum):
    OK = "ok"
    INVALID_CODE = "invalid_code"
    TOO_MANY_ATTEMPTS = "too_many_attempts"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class OtpVerifyOutcome:
    result: OtpResult
    attempts_left: int = 0


@dataclass(frozen=True)
class OtpIssueOutcome:
    code: Optional[str]  # None if reused existing (we never expose the old code)
    resend_after: int    # seconds until next resend is allowed; 0 = can resend now
    reused: bool         # True if an active OTP already existed
    limited: bool        # True if resend_count exceeded hourly cap


# Lua script: atomic verify + consume.
#
# KEYS[1] = otp key (reg:otp:{email})
# ARGV[1] = submitted code hash (hex)
# ARGV[2] = max attempts
#
# Returns one of:
#   {"ok"}                      -> correct, key deleted
#   {"invalid", attempts_left}  -> wrong, attempts incremented
#   {"locked"}                  -> attempts limit exceeded, key deleted
#   {"not_found"}               -> key absent (expired or never issued)
_VERIFY_CONSUME_LUA = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return {'not_found'}
end
local stored = redis.call('HGET', KEYS[1], 'code_hash')
local attempts = tonumber(redis.call('HGET', KEYS[1], 'attempts') or '0')
local max_attempts = tonumber(ARGV[2])
if stored == ARGV[1] then
    redis.call('DEL', KEYS[1])
    return {'ok'}
end
attempts = attempts + 1
if attempts >= max_attempts then
    redis.call('DEL', KEYS[1])
    return {'locked'}
end
redis.call('HSET', KEYS[1], 'attempts', attempts)
return {'invalid', tostring(max_attempts - attempts)}
"""


def _digits_code(length: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def _hash_code(code: str) -> str:
    """HMAC-SHA256 with SECRET_KEY; resists rainbow tables and Redis leak."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _otp_key(email: str) -> str:
    # Normalize email: case-insensitive + trim, to prevent rate-limit bypass
    # via case variation (audit §attack tests).
    return f"reg:otp:{email.strip().lower()}"


class OtpService:
    """
    Thin coordinator around Redis. Stateless aside from a cached Lua sha.
    """

    def __init__(self) -> None:
        self._verify_sha: Optional[str] = None

    async def _ensure_script(self) -> str:
        if self._verify_sha:
            return self._verify_sha
        client = await get_redis_client()
        self._verify_sha = await client.script_load(_VERIFY_CONSUME_LUA)
        return self._verify_sha

    async def issue(
        self,
        email: str,
        *,
        ttl: Optional[int] = None,
        cooldown: Optional[int] = None,
        max_per_hour: Optional[int] = None,
        length: Optional[int] = None,
    ) -> OtpIssueOutcome:
        """
        Generate and store a new OTP or, if an active one is within cooldown,
        return it as reused. Implements resend-cooldown (§2.4) and hourly cap.
        """
        ttl = ttl or settings.OTP_TTL_SECONDS
        cooldown = cooldown or settings.OTP_RESEND_COOLDOWN_SECONDS
        max_per_hour = max_per_hour or settings.OTP_MAX_RESENDS_PER_HOUR
        length = length or settings.OTP_LENGTH

        key = _otp_key(email)
        client = await get_redis_client()

        now = time.time()
        existing = await client.hgetall(key)

        if existing:
            last_resend_at = float(existing.get("last_resend_at") or 0)
            resend_count = int(existing.get("resend_count") or 0)
            elapsed = now - last_resend_at

            # Hourly cap: if >=max_per_hour resends in last hour, block.
            if resend_count >= max_per_hour:
                issued_at = float(existing.get("issued_at") or now)
                if now - issued_at < 3600:
                    ttl_left = await client.ttl(key)
                    return OtpIssueOutcome(
                        code=None,
                        resend_after=max(ttl_left, 60),
                        reused=True,
                        limited=True,
                    )

            # Cooldown not passed — return existing, tell client how long to wait.
            if elapsed < cooldown:
                return OtpIssueOutcome(
                    code=None,
                    resend_after=int(cooldown - elapsed) + 1,
                    reused=True,
                    limited=False,
                )

        # Issue a fresh code (either first time or cooldown elapsed).
        code = _digits_code(length)
        code_hash = _hash_code(code)

        pipe = client.pipeline()
        pipe.hset(
            key,
            mapping={
                "code_hash": code_hash,
                "attempts": "0",
                "resend_count": str(int(existing.get("resend_count", 0)) + 1 if existing else 1),
                "last_resend_at": str(now),
                "issued_at": existing.get("issued_at", str(now)) if existing else str(now),
            },
        )
        pipe.expire(key, ttl)
        await pipe.execute()

        return OtpIssueOutcome(
            code=code,
            resend_after=cooldown,
            reused=False,
            limited=False,
        )

    async def verify_and_consume(
        self,
        email: str,
        code: str,
        *,
        max_attempts: Optional[int] = None,
    ) -> OtpVerifyOutcome:
        """
        Atomic verify. Uses Lua to avoid race conditions under concurrent
        requests (audit §2.6).
        """
        max_attempts = max_attempts or settings.OTP_MAX_ATTEMPTS
        if not code or not code.isdigit() or len(code) != settings.OTP_LENGTH:
            # Do not even call Redis for malformed input — but still bump attempts
            # to thwart timing-based enumeration? We pick a safer option: treat as
            # invalid_code but without increment (avoids lockout by empty payload).
            # Real brute-force is shaped through verify below.
            return OtpVerifyOutcome(OtpResult.INVALID_CODE, attempts_left=max_attempts)

        key = _otp_key(email)
        code_hash = _hash_code(code)
        client = await get_redis_client()

        sha = await self._ensure_script()
        try:
            raw = await client.evalsha(sha, 1, key, code_hash, str(max_attempts))
        except Exception:
            # If script was evicted, reload and retry once.
            self._verify_sha = None
            sha = await self._ensure_script()
            raw = await client.evalsha(sha, 1, key, code_hash, str(max_attempts))

        tag = raw[0] if isinstance(raw, (list, tuple)) else raw
        if isinstance(tag, bytes):
            tag = tag.decode()

        if tag == "ok":
            return OtpVerifyOutcome(OtpResult.OK, attempts_left=max_attempts)
        if tag == "locked":
            return OtpVerifyOutcome(OtpResult.TOO_MANY_ATTEMPTS, attempts_left=0)
        if tag == "not_found":
            return OtpVerifyOutcome(OtpResult.NOT_FOUND, attempts_left=0)

        left = raw[1]
        if isinstance(left, bytes):
            left = left.decode()
        return OtpVerifyOutcome(OtpResult.INVALID_CODE, attempts_left=int(left))

    async def invalidate(self, email: str) -> None:
        client = await get_redis_client()
        await client.delete(_otp_key(email))

    async def ttl(self, email: str) -> int:
        client = await get_redis_client()
        return int(await client.ttl(_otp_key(email)))


# Singleton
otp_service = OtpService()
