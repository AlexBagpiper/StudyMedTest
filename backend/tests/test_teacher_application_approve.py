"""Approve flow: admin comment → DB + outbound email."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.teacher_applications import normalize_optional_comment
from app.models.teacher_application import ApplicationStatus, TeacherApplication
from app.models.user import User
from app.services.email import templates

pytest_plugins = ("tests.registration.conftest",)


async def _pending_application(db: AsyncSession) -> TeacherApplication:
    application = TeacherApplication(
        email=f"teacher_app_{uuid.uuid4().hex[:8]}@example.com",
        last_name="Петров",
        first_name="Пётр",
        middle_name="Петрович",
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.flush()
    return application


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("  Привет  ", "Привет"),
    ],
)
def test_normalize_optional_comment(raw, expected):
    assert normalize_optional_comment(raw) == expected


def test_teacher_account_created_escapes_admin_comment_html():
    rendered = templates.render_teacher_account_created(
        full_name="Test",
        teacher_email="t@example.com",
        temporary_password="pw",
        admin_comment='<img src=x onerror=alert(1)>',
    )
    assert "<img src=x" not in rendered.html
    assert "onerror" in rendered.html


@pytest.mark.asyncio
async def test_approve_passes_admin_comment_to_email(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    captured_emails,
    email_sender,
):
    application = await _pending_application(db_session)
    comment = "Добро пожаловать в команду!"

    response = await async_client.post(
        f"/api/v1/teacher-applications/{application.id}/approve",
        json={"admin_comment": comment},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["admin_comment"] == comment
    assert data["status"] == "approved"

    account_emails = [e for e in captured_emails if e.kind == "teacher_account_created"]
    assert len(account_emails) == 1
    assert account_emails[0].to == application.email
    assert account_emails[0].payload["admin_comment"] == comment
    assert account_emails[0].payload["password"]

    result = await db_session.execute(select(User).where(User.email == application.email))
    teacher = result.scalar_one()
    assert teacher.role.value == "teacher"


@pytest.mark.asyncio
async def test_approve_omits_blank_admin_comment_from_email(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    captured_emails,
    email_sender,
):
    application = await _pending_application(db_session)

    response = await async_client.post(
        f"/api/v1/teacher-applications/{application.id}/approve",
        json={"admin_comment": "   "},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["admin_comment"] is None

    account_emails = [e for e in captured_emails if e.kind == "teacher_account_created"]
    assert len(account_emails) == 1
    assert account_emails[0].payload["admin_comment"] is None


@pytest.mark.asyncio
async def test_approve_without_comment_body(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
    captured_emails,
    email_sender,
):
    application = await _pending_application(db_session)

    response = await async_client.post(
        f"/api/v1/teacher-applications/{application.id}/approve",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert response.json()["admin_comment"] is None
    assert captured_emails[-1].payload.get("admin_comment") is None
