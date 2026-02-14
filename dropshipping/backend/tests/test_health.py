"""Tests for the health check endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Verify GET /api/v1/health returns 200 with status ok.

    Confirms the API is reachable and the database connection is alive.

    Args:
        client: Async HTTP client fixture from conftest.py.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
