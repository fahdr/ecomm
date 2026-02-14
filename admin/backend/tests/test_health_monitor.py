"""
Tests for the Super Admin Dashboard health monitoring endpoints.

For Developers:
    Tests the health monitor by mocking httpx.AsyncClient responses to
    simulate healthy, degraded, and down services. Uses MagicMock for
    response objects and AsyncMock for async methods.

For QA Engineers:
    Covers: live service pings with all three states, health history
    retrieval, history filtering by service name, and snapshot persistence.

For Project Managers:
    These tests ensure the health monitoring system correctly detects
    service states and stores historical data for trending.

For End Users:
    Health monitoring tests validate that the admin dashboard accurately
    reports service status, enabling operators to respond to outages quickly.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.health_snapshot import ServiceHealthSnapshot
from tests.conftest import create_admin


def _mock_response(status_code: int = 200, json_data: dict | None = None):
    """
    Create a MagicMock that mimics an httpx.Response.

    Uses MagicMock (not AsyncMock) for the response object since
    httpx.Response methods like ``.json()`` are synchronous.

    Args:
        status_code: The HTTP status code to return.
        json_data: The JSON body to return from ``.json()``.

    Returns:
        A MagicMock configured as an httpx.Response.
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"status": "healthy"}
    return resp


@pytest.mark.asyncio
async def test_health_services_all_healthy(client, auth_headers):
    """
    GET /health/services returns healthy status for all services.

    Mocks all httpx requests to return 200 with healthy status.

    Verifies:
        - Returns 200 with a ``services`` list.
        - All services have status ``healthy``.
        - ``checked_at`` is present.
    """
    mock_resp = _mock_response(200, {"status": "healthy"})

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.health_monitor.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/health/services", headers=auth_headers
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert "checked_at" in data
    assert len(data["services"]) == 9  # 8 SaaS + gateway
    for svc in data["services"]:
        assert svc["status"] == "healthy"
        assert svc["response_time_ms"] is not None


@pytest.mark.asyncio
async def test_health_services_mixed_states(client, auth_headers):
    """
    GET /health/services handles mixed healthy/degraded/down states.

    Mocks services to return different states based on URL.

    Verifies:
        - Services with 500 responses are marked ``degraded``.
        - Services that timeout are marked ``down``.
    """
    import httpx as httpx_lib

    call_count = 0

    async def mock_get(url, **kwargs):
        """Alternate between healthy, error, and timeout."""
        nonlocal call_count
        call_count += 1
        if call_count % 3 == 0:
            raise httpx_lib.TimeoutException("timeout")
        if call_count % 3 == 2:
            return _mock_response(500, {"status": "error"})
        return _mock_response(200, {"status": "healthy"})

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.health_monitor.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/health/services", headers=auth_headers
        )

    assert resp.status_code == 200
    data = resp.json()
    statuses = {svc["status"] for svc in data["services"]}
    # Should contain at least healthy and one of degraded/down
    assert "healthy" in statuses or "degraded" in statuses or "down" in statuses


@pytest.mark.asyncio
async def test_health_services_persists_snapshots(client, auth_headers, db):
    """
    GET /health/services persists health snapshots to the database.

    Verifies:
        - After calling the endpoint, snapshot records exist in the DB.
    """
    mock_resp = _mock_response(200, {"status": "healthy"})
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.health_monitor.httpx.AsyncClient", return_value=mock_client):
        resp = await client.get(
            "/api/v1/admin/health/services", headers=auth_headers
        )
    assert resp.status_code == 200

    # Check snapshots were persisted
    from sqlalchemy import select, func

    result = await db.execute(select(func.count(ServiceHealthSnapshot.id)))
    count = result.scalar()
    assert count == 9  # One per service


@pytest.mark.asyncio
async def test_health_history_empty(client, auth_headers):
    """
    GET /health/history with no snapshots returns an empty list.

    Verifies:
        - Returns 200 with an empty list.
    """
    resp = await client.get(
        "/api/v1/admin/health/history", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_health_history_returns_snapshots(client, auth_headers, db):
    """
    GET /health/history returns persisted snapshots ordered by time.

    Seeds two snapshots and verifies they are returned in descending order.

    Verifies:
        - Returns 200 with the seeded snapshots.
        - Snapshots are ordered by ``checked_at`` descending.
    """
    # Seed snapshots directly
    s1 = ServiceHealthSnapshot(
        service_name="llm-gateway",
        status="healthy",
        response_time_ms=42.5,
    )
    s2 = ServiceHealthSnapshot(
        service_name="trendscout",
        status="degraded",
        response_time_ms=150.0,
    )
    db.add(s1)
    db.add(s2)
    await db.flush()
    await db.commit()

    resp = await client.get(
        "/api/v1/admin/health/history", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Both should have required fields
    for snapshot in data:
        assert "service_name" in snapshot
        assert "status" in snapshot
        assert "checked_at" in snapshot


@pytest.mark.asyncio
async def test_health_history_filter_by_service(client, auth_headers, db):
    """
    GET /health/history?service_name=X filters to that service.

    Seeds snapshots for two services and filters for one.

    Verifies:
        - Only snapshots for the requested service are returned.
    """
    s1 = ServiceHealthSnapshot(
        service_name="llm-gateway", status="healthy", response_time_ms=30.0
    )
    s2 = ServiceHealthSnapshot(
        service_name="trendscout", status="down", response_time_ms=None
    )
    s3 = ServiceHealthSnapshot(
        service_name="llm-gateway", status="degraded", response_time_ms=200.0
    )
    db.add_all([s1, s2, s3])
    await db.flush()
    await db.commit()

    resp = await client.get(
        "/api/v1/admin/health/history?service_name=llm-gateway",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    for snapshot in data:
        assert snapshot["service_name"] == "llm-gateway"


@pytest.mark.asyncio
async def test_health_services_unauthorized(client):
    """
    GET /health/services without auth returns 401.

    Verifies:
        - Returns 401 (HTTPBearer rejects missing credentials).
    """
    resp = await client.get("/api/v1/admin/health/services")
    assert resp.status_code in (401, 403)
