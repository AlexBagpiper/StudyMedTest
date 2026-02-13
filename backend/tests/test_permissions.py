import pytest
from httpx import AsyncClient
from uuid import UUID

@pytest.mark.asyncio
async def test_student_cannot_create_questions(client: AsyncClient, auth_headers_student):
    """Студент не может создавать вопросы"""
    # Передаем корректные данные, чтобы пройти валидацию схемы, но застрять на правах
    response = await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "test",
            "difficulty": 1,
            "topic_id": None
        },
        headers=auth_headers_student
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_teacher_can_create_questions(client: AsyncClient, auth_headers_teacher):
    """Учитель может создавать вопросы"""
    # Сначала создаем тему
    topic_res = await client.post(
        "/api/v1/topics",
        json={"name": "P_Topic", "description": "desc"},
        headers=auth_headers_teacher
    )
    assert topic_res.status_code == 201
    topic_id = topic_res.json()["id"]
    
    response = await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "test",
            "topic_id": topic_id,
            "difficulty": 1
        },
        headers=auth_headers_teacher
    )
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_admin_can_manage_users(client: AsyncClient, auth_headers_admin):
    """Админ имеет доступ к списку пользователей"""
    response = await client.get("/api/v1/users", headers=auth_headers_admin)
    assert response.status_code == 200
