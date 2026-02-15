"""
Health monitoring router for the Super Admin Dashboard.

Provides real-time and historical health checks for all managed services.
Pings each service's ``/api/v1/health`` endpoint via httpx and records
the results in the ``admin_health_snapshots`` table.

For Developers:
    - ``GET /health/services``: Pings all services in ``settings.service_urls``
      concurrently using ``asyncio.gather`` and httpx. Records snapshots.
    - ``GET /health/history``: Returns the last N health snapshots, ordered
      by ``checked_at`` descending.

    Each ping uses a 5-second timeout. Services that respond with HTTP 200
    and ``status: healthy`` in the JSON body are marked ``healthy``.
    Non-200 responses are ``degraded``, and timeouts/errors are ``down``.

For QA Engineers:
    Mock the httpx.AsyncClient responses to test all three states:
    healthy, degraded, and down. Verify that snapshots are persisted
    and that history returns them in descending chronological order.

For Project Managers:
    This feature powers the dashboard's service status panel, showing
    admins which services are running, slow, or offline.

For End Users:
    Health monitoring helps platform operators detect and fix problems
    before they impact the customer-facing products.
"""

import asyncio
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.config import settings
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.health_snapshot import ServiceHealthSnapshot

router = APIRouter()

# Timeout for each service health check (seconds)
HEALTH_CHECK_TIMEOUT = 5.0


async def _ping_service(
    client: httpx.AsyncClient, name: str, url: str
) -> dict:
    """
    Ping a single service and return its health status.

    Sends a GET request to the service's ``/api/v1/health`` endpoint
    and measures the response time. Classifies the result as
    ``healthy``, ``degraded``, or ``down``.

    Args:
        client: The httpx async client to use for the request.
        name: The service name (for labeling).
        url: The service's base URL (e.g., ``http://localhost:8200``).

    Returns:
        A dict with keys: ``service_name``, ``status``, ``response_time_ms``,
        ``checked_at``, and optionally ``error``.
    """
    health_url = f"{url}/api/v1/health"
    checked_at = datetime.now(timezone.utc)

    try:
        start = time.monotonic()
        resp = await client.get(health_url, timeout=HEALTH_CHECK_TIMEOUT)
        elapsed_ms = (time.monotonic() - start) * 1000

        if resp.status_code == 200:
            body = resp.json()
            # Some services return {"status": "healthy"}, others just 200
            svc_status = body.get("status", "healthy")
            status_val = "healthy" if svc_status == "healthy" else "degraded"
        else:
            status_val = "degraded"
            elapsed_ms = (time.monotonic() - start) * 1000

        return {
            "service_name": name,
            "status": status_val,
            "response_time_ms": round(elapsed_ms, 2),
            "checked_at": checked_at.isoformat(),
        }
    except (httpx.TimeoutException, httpx.ConnectError, Exception):
        return {
            "service_name": name,
            "status": "down",
            "response_time_ms": None,
            "checked_at": checked_at.isoformat(),
        }


@router.get("/health/services")
async def check_all_services(
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Ping all managed services and return their current health.

    Sends concurrent health check requests to every service in
    ``settings.service_urls``. Persists a ``ServiceHealthSnapshot``
    for each result.

    Args:
        db: The async database session.
        _admin: The authenticated admin user (required for access).

    Returns:
        A dict with ``checked_at`` timestamp and a list of service results.
    """
    results = []

    async with httpx.AsyncClient() as client:
        tasks = [
            _ping_service(client, name, url)
            for name, url in settings.service_urls.items()
        ]
        results = await asyncio.gather(*tasks)

    # Persist snapshots
    for result in results:
        snapshot = ServiceHealthSnapshot(
            service_name=result["service_name"],
            status=result["status"],
            response_time_ms=result["response_time_ms"],
        )
        db.add(snapshot)
    await db.flush()

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "services": list(results),
    }


@router.get("/health/history")
async def health_history(
    limit: int = Query(50, ge=1, le=500),
    service_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    Return the last N health snapshots, optionally filtered by service.

    Args:
        limit: Maximum number of snapshots to return (default 50).
        service_name: Optional filter for a specific service.
        db: The async database session.
        _admin: The authenticated admin user (required for access).

    Returns:
        A list of health snapshot dicts ordered by ``checked_at`` descending.
    """
    query = select(ServiceHealthSnapshot).order_by(
        ServiceHealthSnapshot.checked_at.desc()
    )

    if service_name:
        query = query.where(
            ServiceHealthSnapshot.service_name == service_name
        )

    query = query.limit(limit)
    result = await db.execute(query)
    snapshots = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "service_name": s.service_name,
            "status": s.status,
            "response_time_ms": s.response_time_ms,
            "checked_at": s.checked_at.isoformat(),
        }
        for s in snapshots
    ]
