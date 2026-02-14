"""
Health check endpoint tests.

For QA Engineers:
    Verifies the health endpoint returns 200 with correct service metadata.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /api/v1/health returns service status."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "timestamp" in data
