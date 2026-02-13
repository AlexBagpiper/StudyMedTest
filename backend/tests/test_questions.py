"""
Tests for questions endpoints
"""

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_question_as_teacher(client: AsyncClient, auth_headers_teacher):
    """Test creating question as teacher"""
    response = await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "What is the human heart?",
            "difficulty": 1,
            "reference_data": {
                "reference_answer": "The heart is a muscular organ..."
            },
            "scoring_criteria": {
                "factual_correctness": 40,
                "completeness": 30,
                "terminology": 20,
                "structure": 10,
            },
        },
        headers=auth_headers_teacher,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "What is the human heart?"
    assert data["type"] == "text"


@pytest.mark.asyncio
async def test_create_question_as_student_forbidden(client: AsyncClient, auth_headers_student):
    """Test that students cannot create questions"""
    response = await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "Test content",
            "difficulty": 1
        },
        headers=auth_headers_student,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_questions_as_teacher(client: AsyncClient, auth_headers_teacher):
    """Test listing questions as teacher"""
    # Create a question first
    await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "Content 1",
            "difficulty": 1
        },
        headers=auth_headers_teacher,
    )
    
    response = await client.get(
        "/api/v1/questions",
        headers=auth_headers_teacher,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
