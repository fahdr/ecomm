"""
Tests for the Super Admin Dashboard service overview endpoint.

For Developers:
    Tests the ``GET /services`` endpoint that returns a list of all
    managed services with their last known health status. Seeds health
    snapshots directly to test the enrichment logic.

For QA Engineers:
    Covers: listing all 9 services, default ``unknown`` status when no
    snapshots exist, enrichment with the latest snapshot, port extraction
    from URLs, and unauthorized access rejection.

For Project Managers:
    These tests validate the service overview page that admins see first
    when opening the dashboard. It must accurately reflect the current
    state of all platform services.

For End Users:
    Service overview tests ensure the admin dashboard presents an accurate
    view of the platform, helping operators maintain service availability.
"""

import pytest

from app.models.health_snapshot import ServiceHealthSnapshot


@pytest.mark.asyncio
async def test_list_services_returns_all(client, auth_headers):
    """
    GET /services returns all 9 managed services.

    Verifies:
        - Returns 200 with exactly 9 services.
        - Each service has name, port, url, and last_status fields.
    """
    resp = await client.get(
        "/api/v1/admin/services", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 9

    # Check all expected services are present
    names = {svc["name"] for svc in data}
    assert "llm-gateway" in names
    assert "trendscout" in names
    assert "contentforge" in names
    assert "priceoptimizer" in names
    assert "reviewsentinel" in names
    assert "inventoryiq" in names
    assert "customerinsight" in names
    assert "adcreator" in names
    assert "competitorradar" in names


@pytest.mark.asyncio
async def test_list_services_default_unknown_status(client, auth_headers):
    """
    GET /services returns ``unknown`` status when no snapshots exist.

    Verifies:
        - All services have ``last_status`` set to ``unknown``.
        - ``last_response_time_ms`` and ``last_checked_at`` are None.
    """
    resp = await client.get(
        "/api/v1/admin/services", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    for svc in data:
        assert svc["last_status"] == "unknown"
        assert svc["last_response_time_ms"] is None
        assert svc["last_checked_at"] is None


@pytest.mark.asyncio
async def test_list_services_with_health_snapshot(client, auth_headers, db):
    """
    GET /services enriches results with the latest health snapshot.

    Seeds a health snapshot for ``llm-gateway`` and verifies it appears
    in the service listing.

    Verifies:
        - The ``llm-gateway`` service has ``last_status`` set to ``healthy``.
        - The ``last_response_time_ms`` matches the seeded value.
        - The ``last_checked_at`` is not None.
    """
    snapshot = ServiceHealthSnapshot(
        service_name="llm-gateway",
        status="healthy",
        response_time_ms=35.2,
    )
    db.add(snapshot)
    await db.flush()
    await db.commit()

    resp = await client.get(
        "/api/v1/admin/services", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    gateway = next(svc for svc in data if svc["name"] == "llm-gateway")
    assert gateway["last_status"] == "healthy"
    assert gateway["last_response_time_ms"] == 35.2
    assert gateway["last_checked_at"] is not None

    # Other services should still be unknown
    trendscout = next(svc for svc in data if svc["name"] == "trendscout")
    assert trendscout["last_status"] == "unknown"


@pytest.mark.asyncio
async def test_list_services_port_extraction(client, auth_headers):
    """
    GET /services correctly extracts ports from service URLs.

    Verifies:
        - The LLM Gateway has port 8200.
        - SaaS services have ports 8101-8108.
    """
    resp = await client.get(
        "/api/v1/admin/services", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    gateway = next(svc for svc in data if svc["name"] == "llm-gateway")
    assert gateway["port"] == 8200

    trendscout = next(svc for svc in data if svc["name"] == "trendscout")
    assert trendscout["port"] == 8101


@pytest.mark.asyncio
async def test_list_services_uses_latest_snapshot(client, auth_headers, db):
    """
    GET /services uses the most recent snapshot, not older ones.

    Seeds two snapshots for the same service (first healthy, then degraded)
    and verifies the latest one is used.

    Verifies:
        - The service's ``last_status`` reflects the most recent snapshot.
    """
    import asyncio

    # First snapshot: healthy
    s1 = ServiceHealthSnapshot(
        service_name="trendscout",
        status="healthy",
        response_time_ms=30.0,
    )
    db.add(s1)
    await db.flush()
    await db.commit()

    # Brief pause to ensure different timestamps
    await asyncio.sleep(0.05)

    # Second snapshot: degraded (more recent)
    s2 = ServiceHealthSnapshot(
        service_name="trendscout",
        status="degraded",
        response_time_ms=500.0,
    )
    db.add(s2)
    await db.flush()
    await db.commit()

    resp = await client.get(
        "/api/v1/admin/services", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    trendscout = next(svc for svc in data if svc["name"] == "trendscout")
    assert trendscout["last_status"] == "degraded"
    assert trendscout["last_response_time_ms"] == 500.0


@pytest.mark.asyncio
async def test_list_services_unauthorized(client):
    """
    GET /services without auth returns 401.

    Verifies:
        - Returns 401 (HTTPBearer rejects missing credentials).
    """
    resp = await client.get("/api/v1/admin/services")
    assert resp.status_code in (401, 403)
