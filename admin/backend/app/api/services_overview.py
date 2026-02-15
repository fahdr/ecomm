"""
Service overview router for the Super Admin Dashboard.

Provides a summary view of all managed services with their configuration
and last known health status. This powers the dashboard's service listing
page where admins can see at a glance which services are running.

For Developers:
    ``GET /services`` returns a list of all 9 managed services (8 SaaS +
    LLM Gateway) with their name, port, URL, and the most recent health
    snapshot from the database.

    The service list is derived from ``settings.service_urls``. Port numbers
    are extracted from the URLs. The latest health snapshot for each service
    is fetched in a single query with a subquery for the max ``checked_at``.

For QA Engineers:
    Test that the endpoint returns all 9 services. Test with and without
    health snapshots in the database. Verify that ``last_status`` is
    ``unknown`` when no snapshots exist for a service.

For Project Managers:
    This endpoint provides the birds-eye view of the platform. It is the
    first thing admins see when opening the dashboard, enabling them to
    quickly identify which services need attention.

For End Users:
    The service overview helps platform operators ensure all products
    are running, which directly impacts the availability of customer-facing
    features.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.config import settings
from app.database import get_db
from app.models.admin_user import AdminUser
from app.models.health_snapshot import ServiceHealthSnapshot

router = APIRouter()


class ServiceInfo(BaseModel):
    """
    Schema for a service in the overview list.

    Attributes:
        name: The service's identifier (e.g., ``llm-gateway``).
        port: The port the service listens on.
        url: The service's base URL.
        last_status: The most recent health check status (healthy/degraded/down/unknown).
        last_response_time_ms: The most recent response time in milliseconds.
        last_checked_at: ISO timestamp of the last health check, or None.
    """

    name: str
    port: int
    url: str
    last_status: str
    last_response_time_ms: float | None = None
    last_checked_at: str | None = None

    model_config = {"from_attributes": True}


def _extract_port(url: str) -> int:
    """
    Extract the port number from a URL.

    Args:
        url: A URL string like ``http://localhost:8200``.

    Returns:
        The port number as an integer. Defaults to 80 if no port is specified.
    """
    try:
        # Split on ":" and take the last part, stripping any path
        parts = url.rstrip("/").split(":")
        return int(parts[-1].split("/")[0])
    except (ValueError, IndexError):
        return 80


@router.get("/services", response_model=list[ServiceInfo])
async def list_services(
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    """
    List all managed services with their last known health status.

    Returns one entry per service in ``settings.service_urls``, enriched
    with the most recent health snapshot from the database (if any).

    Args:
        db: The async database session.
        _admin: The authenticated admin user (required for access).

    Returns:
        List of ServiceInfo objects for all 9 managed services.
    """
    # Fetch the latest health snapshot for each service
    latest_snapshots: dict[str, ServiceHealthSnapshot] = {}
    for svc_name in settings.service_urls:
        result = await db.execute(
            select(ServiceHealthSnapshot)
            .where(ServiceHealthSnapshot.service_name == svc_name)
            .order_by(ServiceHealthSnapshot.checked_at.desc())
            .limit(1)
        )
        snapshot = result.scalar_one_or_none()
        if snapshot:
            latest_snapshots[svc_name] = snapshot

    services = []
    for name, url in settings.service_urls.items():
        snapshot = latest_snapshots.get(name)
        services.append(
            ServiceInfo(
                name=name,
                port=_extract_port(url),
                url=url,
                last_status=snapshot.status if snapshot else "unknown",
                last_response_time_ms=(
                    snapshot.response_time_ms if snapshot else None
                ),
                last_checked_at=(
                    snapshot.checked_at.isoformat() if snapshot else None
                ),
            )
        )

    return services
