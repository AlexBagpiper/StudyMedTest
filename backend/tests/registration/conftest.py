"""
Fixtures shared by all registration-flow tests (unit/integration/security).

Strategy:
- Replace `app.core.redis.get_redis_client` with an async fakeredis client so
  the Lua script runs identically to production (fakeredis implements EVAL/EVALSHA).
- Reset the OTP script SHA cache and the email sender cache between tests.
- Capture outbound emails via `captured_emails` list by swapping the EmailSender
  for an in-memory test double.
- Freeze the rate limiter for unit tests (can be re-enabled where needed).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional

import fakeredis.aioredis
import pytest

from app.core import redis as redis_module
from app.core import otp as otp_module
from app.core.rate_limit import limiter
from app.services import email as email_pkg
from app.services.email.base import EmailSender
from app.services.email.factory import reset_email_sender_cache


@dataclass
class CapturedEmail:
    kind: str
    to: str
    payload: dict = field(default_factory=dict)


class InMemoryEmailSender(EmailSender):
    """Records all .send_* calls into a shared list for assertions."""

    def __init__(self, sink: List[CapturedEmail], fail_times: int = 0) -> None:
        self.sink = sink
        # For resilience tests: first N calls raise then succeed.
        self._remaining_failures = fail_times

    def _maybe_fail(self) -> None:
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise ConnectionError("simulated SMTP outage")

    async def send_verification(self, to_email: str, code: str) -> None:
        self._maybe_fail()
        self.sink.append(CapturedEmail("verification", to_email, {"code": code}))

    async def send_email_change(self, to_email: str, code: str) -> None:
        self._maybe_fail()
        self.sink.append(CapturedEmail("email_change", to_email, {"code": code}))

    async def send_teacher_application_notification(
        self, admin_email: str, teacher_email: str, full_name: str
    ) -> None:
        self.sink.append(CapturedEmail(
            "teacher_application_notification", admin_email,
            {"teacher_email": teacher_email, "full_name": full_name},
        ))

    async def send_teacher_account_created(
        self, teacher_email: str, full_name: str, temporary_password: str
    ) -> None:
        self.sink.append(CapturedEmail(
            "teacher_account_created", teacher_email,
            {"full_name": full_name, "password": temporary_password},
        ))

    async def send_teacher_application_rejected(
        self, teacher_email: str, full_name: str, admin_comment: Optional[str] = None
    ) -> None:
        self.sink.append(CapturedEmail(
            "teacher_application_rejected", teacher_email,
            {"full_name": full_name, "comment": admin_comment},
        ))


@pytest.fixture(scope="function")
async def fake_redis():
    """
    Fresh fakeredis instance per test, monkeypatched into app.core.redis.
    We force a unique FakeServer per test to avoid state leakage between tests
    (default fakeredis shares the backing storage module-wide).
    """
    import fakeredis
    server = fakeredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    original = redis_module._redis_client
    redis_module._redis_client = client

    # Invalidate cached Lua SHA so OtpService reloads on this client.
    otp_module.otp_service._verify_sha = None

    yield client

    try:
        await client.aclose()
    except Exception:
        pass
    redis_module._redis_client = original
    otp_module.otp_service._verify_sha = None


@pytest.fixture(scope="function")
def captured_emails():
    """List-shaped sink; each test gets its own."""
    return []


@pytest.fixture(scope="function")
def email_sender(captured_emails, monkeypatch):
    """
    Swap the factory-produced EmailSender with an in-memory capture.
    Patches both `app.services.email.get_email_sender` and the already-resolved
    module-level alias used by auth.py to be bullet-proof.
    """
    sender = InMemoryEmailSender(captured_emails)
    reset_email_sender_cache()
    monkeypatch.setattr(email_pkg, "get_email_sender", lambda: sender)
    import app.api.v1.auth as auth_module
    monkeypatch.setattr(auth_module, "get_email_sender", lambda: sender)
    yield sender
    reset_email_sender_cache()


@pytest.fixture(scope="function")
def flaky_email_sender(captured_emails, monkeypatch):
    """
    Returns a sender that fails the first N calls, for resilience tests.
    """
    def factory(fail_times: int) -> InMemoryEmailSender:
        sender = InMemoryEmailSender(captured_emails, fail_times=fail_times)
        import app.api.v1.auth as auth_module
        monkeypatch.setattr(email_pkg, "get_email_sender", lambda: sender)
        monkeypatch.setattr(auth_module, "get_email_sender", lambda: sender)
        return sender
    return factory


@pytest.fixture(scope="function")
def disable_rate_limit():
    """Temporarily disable slowapi for tests that focus on logic, not throttling."""
    was_enabled = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = was_enabled


@pytest.fixture(scope="function")
def enable_rate_limit():
    """Ensure rate limiter is ON and reset its storage between tests."""
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.reset()


def register_payload(**overrides):
    """Build a valid /register request body."""
    base = {
        "email": "student@example.com",
        "password": "Secret123",
        "last_name": "Иванов",
        "first_name": "Иван",
        "middle_name": "Иванович",
    }
    base.update(overrides)
    return base
