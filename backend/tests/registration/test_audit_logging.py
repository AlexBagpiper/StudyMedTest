import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.audit import AuditLog
from app.models.user import User
from tests.registration.conftest import register_payload
from app.core.config import settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]

async def test_audit_log_created_on_registration(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    # 1. Register
    payload = register_payload(email="audit_test@example.com")
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 200

    # 2. Check AuditLog for auth.register_start
    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "auth.register_start")
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    log = next(l for l in logs if l.details.get("email") == "audit_test@example.com")
    assert log.ip_address is not None
    assert log.details["email"] == "audit_test@example.com"

async def test_audit_log_created_on_verify_success(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    # 1. Register
    email = "verify_audit@example.com"
    await client.post("/api/v1/auth/register", json=register_payload(email=email))
    code = captured_emails[0].payload["code"]

    # 2. Verify
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": email, "code": code,
    })
    assert res.status_code == 200

    # 3. Check AuditLog for auth.verify_success
    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "auth.verify_success")
    )
    logs = result.scalars().all()
    log = next(l for l in logs if l.details.get("email") == email)
    assert log.user_id is not None
    
    # Verify user exists and ID matches
    user_res = await db.execute(select(User).where(User.email == email))
    user = user_res.scalar_one()
    assert log.user_id == user.id

async def test_audit_log_created_on_verify_failure(
    client: AsyncClient, db, fake_redis, email_sender, captured_emails, disable_rate_limit
):
    # 1. Register
    email = "fail_audit@example.com"
    await client.post("/api/v1/auth/register", json=register_payload(email=email))

    # 2. Verify with wrong code
    res = await client.post("/api/v1/auth/verify-email", json={
        "email": email, "code": "000000",
    })
    assert res.status_code == 400

    # 3. Check AuditLog for auth.verify_failed
    result = await db.execute(
        select(AuditLog).where(AuditLog.action == "auth.verify_failed")
    )
    logs = result.scalars().all()
    log = next(l for l in logs if l.details.get("email") == email)
    assert log.details["reason"] == "invalid_code"
    assert "attempts_left" in log.details

async def test_admin_can_search_audit_logs(
    client: AsyncClient, db, auth_headers_admin, test_user
):
    # 1. Create a dummy audit log
    from app.services.audit_service import audit_service
    email = "search_test@example.com"
    await audit_service.log_event(
        db=db,
        action="test.action",
        details={"email": email},
        ip_address="1.2.3.4"
    )
    await db.flush()

    # 2. Search via admin API
    res = await client.get(
        f"/api/v1/admin/audit-logs?search={email}",
        headers=auth_headers_admin
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(item["details"].get("email") == email for item in data["items"])

    # 3. Search by IP
    res = await client.get(
        "/api/v1/admin/audit-logs?search=1.2.3.4",
        headers=auth_headers_admin
    )
    assert res.status_code == 200
    data = res.json()
    assert any(item["ip_address"] == "1.2.3.4" for item in data["items"])
