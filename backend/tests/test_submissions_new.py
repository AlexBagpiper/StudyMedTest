import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_submissions_unauthorized(client: AsyncClient):
    """Test getting submissions without authorization"""
    # Removed trailing slash to avoid 307 redirect
    response = await client.get("/api/v1/submissions")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_my_submissions(client: AsyncClient, auth_headers_student):
    """Test getting student's own submissions"""
    response = await client.get("/api/v1/submissions", headers=auth_headers_student)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
