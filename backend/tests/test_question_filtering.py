import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_list_questions_filtering_topic(client: AsyncClient, auth_headers_teacher):
    """Test filtering questions by topic_id."""
    # 1. Create a topic first
    topic_response = await client.post(
        "/api/v1/topics",
        json={"name": f"Topic {uuid4()}", "description": "Test Topic"},
        headers=auth_headers_teacher
    )
    assert topic_response.status_code == 201
    topic_id = topic_response.json()["id"]

    # 2. Create questions: one with topic, one without
    await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "Question with topic",
            "difficulty": 1,
            "topic_id": topic_id
        },
        headers=auth_headers_teacher
    )
    await client.post(
        "/api/v1/questions",
        json={
            "type": "text",
            "content": "Question without topic",
            "difficulty": 1,
            "topic_id": None
        },
        headers=auth_headers_teacher
    )

    # 3. List questions with topic filter
    response = await client.get(
        "/api/v1/questions",
        params={"topic_id": topic_id},
        headers=auth_headers_teacher
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["content"] == "Question with topic"
    assert data["items"][0]["topic_id"] == topic_id

@pytest.mark.asyncio
async def test_list_questions_filtering_search(client: AsyncClient, auth_headers_teacher):
    """Test filtering questions by search query."""
    unique_suffix = str(uuid4())[:8]
    content_match = f"Unique question {unique_suffix}"
    content_mismatch = f"Another question {uuid4()}"

    await client.post(
        "/api/v1/questions",
        json={"type": "text", "content": content_match, "difficulty": 1},
        headers=auth_headers_teacher
    )
    await client.post(
        "/api/v1/questions",
        json={"type": "text", "content": content_mismatch, "difficulty": 1},
        headers=auth_headers_teacher
    )

    # Search for the unique part
    response = await client.get(
        "/api/v1/questions",
        params={"search": unique_suffix},
        headers=auth_headers_teacher
    )
    assert response.status_code == 200
    data = response.json()
    # It might be more than 1 if other tests created similar content, but at least 1
    assert data["total"] >= 1
    assert any(q["content"] == content_match for q in data["items"])
    assert all(unique_suffix.lower() in q["content"].lower() for q in data["items"])

@pytest.mark.asyncio
async def test_list_questions_combined_filtering(client: AsyncClient, auth_headers_teacher):
    """Test combining multiple filters and pagination."""
    # Create a unique topic
    topic_resp = await client.post(
        "/api/v1/topics",
        json={"name": f"Combined {uuid4()}", "description": "desc"},
        headers=auth_headers_teacher
    )
    topic_id = topic_resp.json()["id"]

    # Create 3 questions for this topic
    for i in range(3):
        await client.post(
            "/api/v1/questions",
            json={
                "type": "text",
                "content": f"Match {i} text",
                "difficulty": 1,
                "topic_id": topic_id
            },
            headers=auth_headers_teacher
        )

    # 1. Filter by topic only
    resp = await client.get(
        "/api/v1/questions",
        params={"topic_id": topic_id},
        headers=auth_headers_teacher
    )
    assert resp.json()["total"] == 3

    # 2. Filter by topic and search
    resp = await client.get(
        "/api/v1/questions",
        params={"topic_id": topic_id, "search": "Match 1"},
        headers=auth_headers_teacher
    )
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["content"] == "Match 1 text"

    # 3. Test pagination with filters
    resp = await client.get(
        "/api/v1/questions",
        params={"topic_id": topic_id, "limit": 2, "skip": 0},
        headers=auth_headers_teacher
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2

    resp = await client.get(
        "/api/v1/questions",
        params={"topic_id": topic_id, "limit": 2, "skip": 2},
        headers=auth_headers_teacher
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 1

@pytest.mark.asyncio
async def test_search_reset_functionality(client: AsyncClient, auth_headers_teacher):
    """Test that clearing search returns all results (simulating frontend reset)."""
    unique_mark = f"reset_test_{uuid4()}"
    await client.post(
        "/api/v1/questions",
        json={"type": "text", "content": f"Test {unique_mark} 1", "difficulty": 1},
        headers=auth_headers_teacher
    )
    await client.post(
        "/api/v1/questions",
        json={"type": "text", "content": f"Test {unique_mark} 2", "difficulty": 1},
        headers=auth_headers_teacher
    )

    # 1. Search for specific one
    resp = await client.get(
        "/api/v1/questions",
        params={"search": "1"},
        headers=auth_headers_teacher
    )
    # Filter might match other questions, but should include at least our specific one
    assert any(unique_mark in q["content"] for q in resp.json()["items"])

    # 2. Reset search (empty string)
    resp = await client.get(
        "/api/v1/questions",
        params={"search": ""}, # Simulation of clear button
        headers=auth_headers_teacher
    )
    data = resp.json()
    # Should see both
    count_ours = sum(1 for q in data["items"] if unique_mark in q["content"])
    assert count_ours == 2

