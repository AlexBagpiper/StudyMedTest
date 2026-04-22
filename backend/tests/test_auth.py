"""
Tests for authentication endpoints
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_register_student(client: AsyncClient):
    """Test student registration — returns 200 with generic OTP-dispatched response.

    Note: contract changed in the registration overhaul (see docs/REGISTRATION.md).
    The new endpoint never creates a user synchronously — it issues an OTP.
    The `role` field is rejected by StudentRegisterSchema (extra=forbid).
    """
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newstudent@example.com",
            "password": "password123",
            "last_name": "Студентов",
            "first_name": "Новый",
            "middle_name": "Студентович",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newstudent@example.com"
    assert "message" in data
    assert "resend_after" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Duplicate email returns a uniform 200 (user enumeration defence)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "password123",
            "last_name": "Дубликатов",
            "first_name": "Дублик",
        },
    )
    assert response.status_code == 200
    # Same response shape as for a fresh email — no "already registered" leak.
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password"""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user, auth_headers_student):
    """Test get current user endpoint"""
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers_student,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["role"] == "student"

