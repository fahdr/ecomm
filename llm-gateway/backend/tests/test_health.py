"""
Tests for the LLM Gateway health endpoint.

For Developers:
    Tests basic health check and provider health listing.

For QA Engineers:
    Verify the gateway reports healthy status and correct service name.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Health endpoint returns service name and status."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "llm-gateway"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_provider_health_empty(client):
    """Provider health returns empty list when no providers configured."""
    resp = await client.get("/api/v1/health/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["providers"] == []
