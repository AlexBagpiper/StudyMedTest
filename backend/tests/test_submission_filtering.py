import pytest
from httpx import AsyncClient
from uuid import uuid4
from app.models.submission import SubmissionStatus

@pytest.mark.asyncio
async def test_list_submissions_filtering_status(client: AsyncClient, auth_headers_admin, auth_headers_student):
    """Test filtering submissions by status (Admin)."""
    # 1. Start a test to get a submission in_progress
    # Need a test first
    # Add a question first
    q_resp = await client.post(
        "/api/v1/questions",
        json={"type": "text", "content": f"Q {uuid4()}", "difficulty": 1},
        headers=auth_headers_admin
    )
    q_id = q_resp.json()["id"]

    test_resp = await client.post(
        "/api/v1/tests",
        json={
            "title": f"Test {uuid4()}",
            "description": "desc",
            "settings": {"time_limit": 60},
            "structure": [],
            "questions": [{"question_id": q_id, "order": 0}]
        },
        headers=auth_headers_admin
    )
    test_id = test_resp.json()["id"]
    await client.post(f"/api/v1/tests/{test_id}/publish", headers=auth_headers_admin)

    # 2. Student starts test
    start_resp = await client.post(
        f"/api/v1/tests/{test_id}/start",
        headers=auth_headers_student
    )
    assert start_resp.status_code == 200

    # 3. Admin filters by in_progress
    resp = await client.get(
        "/api/v1/submissions",
        params={"status": "in_progress"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(s["status"] == "in_progress" for s in data["items"])
    assert any(str(s["test_id"]) == str(test_id) for s in data["items"])

@pytest.mark.asyncio
async def test_list_submissions_search(client: AsyncClient, auth_headers_admin, auth_headers_student):
    """Test searching submissions by student name or test title."""
    unique_title = f"Unique Search Title {uuid4()}"
    
    # 1. Create unique test
    # Add a question first
    q_resp = await client.post(
        "/api/v1/questions",
        json={"type": "text", "content": f"Q {uuid4()}", "difficulty": 1},
        headers=auth_headers_admin
    )
    q_id = q_resp.json()["id"]

    test_resp = await client.post(
        "/api/v1/tests",
        json={
            "title": unique_title,
            "description": "desc",
            "settings": {"time_limit": 60},
            "structure": [],
            "questions": [{"question_id": q_id, "order": 0}]
        },
        headers=auth_headers_admin
    )
    test_id = test_resp.json()["id"]
    await client.post(f"/api/v1/tests/{test_id}/publish", headers=auth_headers_admin)

    # 2. Student starts test
    await client.post(
        f"/api/v1/tests/{test_id}/start",
        headers=auth_headers_student
    )

    # 3. Search by test title
    resp = await client.get(
        "/api/v1/submissions",
        params={"search": "Search Title"},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert any(unique_title in s["test_title"] for s in data["items"])

@pytest.mark.asyncio
async def test_list_submissions_pagination(client: AsyncClient, auth_headers_admin):
    """Test pagination of submissions."""
    resp = await client.get(
        "/api/v1/submissions",
        params={"skip": 0, "limit": 1},
        headers=auth_headers_admin
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 1
    assert len(data["items"]) <= 1
