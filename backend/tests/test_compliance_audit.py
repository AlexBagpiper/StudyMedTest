"""
Тесты compliance: маскирование audit details, ротация логов, read-audit, экспорт CSV.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.user import User
from app.services.audit_service import AuditService, audit_service
from app.tasks import maintenance_tasks
from app.tasks.maintenance_tasks import rotate_audit_logs_task


@pytest.mark.unit
def test_mask_sensitive_data_recursively():
    raw = {
        "email": "u@example.com",
        "password": "secret",
        "nested": {"api_key": "k", "ok": 1},
        "list": [{"token": "t"}, {"a": 2}],
    }
    masked = AuditService._mask_sensitive_data(raw)
    assert masked["email"] == "u@example.com"
    assert masked["password"] == "***MASKED***"
    assert masked["nested"]["api_key"] == "***MASKED***"
    assert masked["nested"]["ok"] == 1
    assert masked["list"][0]["token"] == "***MASKED***"
    assert masked["list"][1]["a"] == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_log_event_masks_before_flush(db):
    await audit_service.log_event(
        db=db,
        action="compliance.mask_test",
        details={"password": "x", "plain": "y"},
    )
    await db.flush()
    res = await db.execute(select(AuditLog).where(AuditLog.action == "compliance.mask_test"))
    row = res.scalar_one()
    assert row.details["password"] == "***MASKED***"
    assert row.details["plain"] == "y"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_get_user_writes_read_audit(
    client: AsyncClient,
    db,
    auth_headers_admin: dict,
    test_user: User,
):
    res = await client.get(
        f"/api/v1/admin/users/{test_user.id}",
        headers=auth_headers_admin,
    )
    assert res.status_code == 200

    q = await db.execute(
        select(AuditLog).where(
            AuditLog.action == "admin.user_read",
            AuditLog.resource_id == test_user.id,
        )
    )
    logs = q.scalars().all()
    assert len(logs) >= 1
    assert logs[0].details.get("email") == test_user.email


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_export_audit_logs_csv(
    client: AsyncClient,
    db,
    auth_headers_admin: dict,
    test_admin: User,
):
    mark = f"export_{uuid.uuid4().hex[:8]}@example.com"
    await audit_service.log_event(
        db=db,
        action="compliance.export_probe",
        user_id=test_admin.id,
        details={"email": mark},
        ip_address="10.0.0.1",
    )
    await db.commit()

    res = await client.get(
        "/api/v1/admin/audit-logs/export",
        headers=auth_headers_admin,
        params={"search": mark},
    )
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("text/csv")
    body = res.text
    assert body.startswith("\ufeff")
    lines = [ln for ln in body.strip().splitlines() if ln.strip()]
    assert "Timestamp" in lines[0]
    assert mark in body
    assert "compliance.export_probe" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_audit_logs_forbidden_for_student(
    client: AsyncClient,
    auth_headers_student: dict,
):
    res = await client.get(
        "/api/v1/admin/audit-logs/export",
        headers=auth_headers_student,
    )
    assert res.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rotate_audit_logs_removes_only_expired(
    db,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "AUDIT_LOG_RETENTION_DAYS", 30)

    old = AuditLog(
        action="compliance.old",
        timestamp=datetime.utcnow() - timedelta(days=60),
    )
    new = AuditLog(
        action="compliance.new",
        timestamp=datetime.utcnow(),
    )
    db.add_all([old, new])
    await db.flush()
    old_id, new_id = old.id, new.id

    @asynccontextmanager
    async def _fake_session():
        yield db

    monkeypatch.setattr(
        maintenance_tasks,
        "AsyncSessionLocal",
        lambda: _fake_session(),
    )

    rotate_audit_logs_task()

    cnt_old = await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.id == old_id))
    cnt_new = await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.id == new_id))
    assert cnt_old == 0
    assert cnt_new == 1
