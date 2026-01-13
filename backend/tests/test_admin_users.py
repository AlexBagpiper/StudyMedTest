"""
Тесты для admin endpoints управления пользователями
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_create_teacher_by_admin(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession
):
    """Тест создания преподавателя администратором"""
    teacher_data = {
        "email": "teacher@test.com",
        "password": "teacher123",
        "last_name": "Преподавателев",
        "first_name": "Преподаватель",
        "middle_name": "Преподавателевич",
        "role": "teacher",
        "is_active": True,
        "is_verified": True,
    }
    
    response = await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["email"] == teacher_data["email"]
    assert data["last_name"] == teacher_data["last_name"]
    assert data["first_name"] == teacher_data["first_name"]
    assert data["middle_name"] == teacher_data["middle_name"]
    assert data["role"] == "teacher"
    assert data["is_active"] == True
    assert data["is_verified"] == True
    assert "id" in data
    
    # Проверяем что пользователь действительно создан в БД
    result = await db_session.execute(
        select(User).where(User.email == teacher_data["email"])
    )
    user = result.scalar_one_or_none()
    
    assert user is not None
    assert user.role == Role.TEACHER


@pytest.mark.asyncio
async def test_create_teacher_duplicate_email(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession
):
    """Тест создания преподавателя с существующим email"""
    # Создаем первого преподавателя
    teacher_data = {
        "email": "duplicate@test.com",
        "password": "password123",
        "last_name": "Иванов",
        "first_name": "Иван",
        "role": "teacher",
        "is_active": True,
        "is_verified": True,
    }
    
    response = await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    
    # Пытаемся создать второго с тем же email
    response = await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_teacher_by_non_admin(
    async_client: AsyncClient,
    teacher_token: str
):
    """Тест что не-администратор не может создать преподавателя"""
    teacher_data = {
        "email": "newteacher@test.com",
        "password": "password123",
        "last_name": "Петров",
        "first_name": "Петр",
        "role": "teacher",
        "is_active": True,
        "is_verified": True,
    }
    
    response = await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {teacher_token}"}
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_by_admin(
    async_client: AsyncClient,
    admin_token: str
):
    """Тест получения списка пользователей"""
    response = await async_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_filter_users_by_role(
    async_client: AsyncClient,
    admin_token: str
):
    """Тест фильтрации пользователей по роли"""
    response = await async_client.get(
        "/api/v1/admin/users?role=teacher",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем что все пользователи - преподаватели
    for user in data["items"]:
        assert user["role"] == "teacher"


@pytest.mark.asyncio
async def test_search_users(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession
):
    """Тест поиска пользователей"""
    # Создаем пользователя с уникальным именем
    unique_name = "УникальныйПреподаватель"
    teacher_data = {
        "email": "searchtest@test.com",
        "password": "password123",
        "last_name": unique_name,
        "first_name": "Тест",
        "role": "teacher",
        "is_active": True,
        "is_verified": True,
    }
    
    await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Ищем по фамилии
    response = await async_client.get(
        f"/api/v1/admin/users?search={unique_name}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["items"]) > 0
    assert any(user["last_name"] == unique_name for user in data["items"])


@pytest.mark.asyncio
async def test_update_teacher(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession
):
    """Тест обновления преподавателя"""
    # Создаем преподавателя
    teacher_data = {
        "email": "updatetest@test.com",
        "password": "password123",
        "last_name": "Старов",
        "first_name": "Старый",
        "role": "teacher",
        "is_active": True,
        "is_verified": True,
    }
    
    create_response = await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = create_response.json()["id"]
    
    # Обновляем
    update_data = {
        "last_name": "Новов",
        "first_name": "Новый",
    }
    
    response = await async_client.put(
        f"/api/v1/admin/users/{user_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["last_name"] == "Новов"
    assert data["first_name"] == "Новый"
    assert data["email"] == teacher_data["email"]  # Email не изменился


@pytest.mark.asyncio
async def test_delete_teacher(
    async_client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession
):
    """Тест удаления преподавателя"""
    # Создаем преподавателя
    teacher_data = {
        "email": "deletetest@test.com",
        "password": "password123",
        "last_name": "Удаляев",
        "first_name": "Удаляемый",
        "role": "teacher",
        "is_active": True,
        "is_verified": True,
    }
    
    create_response = await async_client.post(
        "/api/v1/admin/users",
        json=teacher_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    user_id = create_response.json()["id"]
    
    # Удаляем
    response = await async_client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 204
    
    # Проверяем что пользователь удален
    result = await db_session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    assert user is None


@pytest.mark.asyncio
async def test_get_admin_stats(
    async_client: AsyncClient,
    admin_token: str
):
    """Тест получения статистики"""
    response = await async_client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "users" in data
    assert "total" in data["users"]
    assert "students" in data["users"]
    assert "teachers" in data["users"]
    assert "admins" in data["users"]
    assert "questions_count" in data
    assert "tests_count" in data


@pytest.mark.asyncio
async def test_admin_cannot_delete_himself(
    async_client: AsyncClient,
    admin_token: str,
    admin_user: User
):
    """Тест что администратор не может удалить сам себя"""
    response = await async_client.delete(
        f"/api/v1/admin/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 400
    assert "cannot delete yourself" in response.json()["detail"].lower()
