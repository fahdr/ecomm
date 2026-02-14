"""ServiceBridge REST API endpoints.

Exposes platform event activity queries and manual dispatch for the
dashboard UI. All endpoints require authentication.

**For Developers:**
    All endpoints use ``get_current_user`` for auth. Query endpoints
    delegate to ``bridge_service`` async helpers. The manual dispatch
    endpoint fires a Celery task and returns immediately.

**For QA Engineers:**
    - ``GET /bridge/activity`` returns paginated ``BridgeDelivery`` records.
    - Filters: ``event``, ``service``, ``status`` (success/failed).
    - ``GET /bridge/activity/{resource_type}/{resource_id}`` returns
      deliveries for a specific product/order/customer.
    - ``GET /bridge/service/{service_name}/activity`` returns per-service
      deliveries.
    - ``GET /bridge/summary`` returns per-service 24h summary.
    - ``POST /bridge/dispatch`` fires an event manually (admin/debug).

**For Project Managers:**
    These endpoints power the Service Activity dashboard pages, the
    per-resource service status panels, and the services hub health
    indicators.

**For End Users:**
    These endpoints provide the data behind the "Service Activity" page
    in your dashboard, showing which AI tools were notified about your
    store events and whether those notifications succeeded.
"""

import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.bridge import (
    BridgeActivityResponse,
    BridgeDeliveryResponse,
    BridgeDispatchRequest,
    ServiceSummaryResponse,
)
from app.services.bridge_service import (
    fire_platform_event,
    get_recent_activity,
    get_resource_deliveries,
    get_service_activity,
    get_service_summary,
)

router = APIRouter(prefix="/bridge", tags=["bridge"])


def _delivery_to_response(d) -> BridgeDeliveryResponse:
    """Convert a BridgeDelivery ORM object to a response schema.

    Args:
        d: A ``BridgeDelivery`` ORM instance.

    Returns:
        A ``BridgeDeliveryResponse`` with all fields serialized.
    """
    return BridgeDeliveryResponse(
        id=str(d.id),
        service_name=d.service_name.value if hasattr(d.service_name, "value") else str(d.service_name),
        event=d.event,
        resource_id=d.resource_id,
        resource_type=d.resource_type,
        success=d.success,
        error_message=d.error_message,
        response_status=d.response_status,
        latency_ms=d.latency_ms,
        created_at=d.created_at,
    )


@router.get("/activity", response_model=BridgeActivityResponse)
async def get_activity(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    event: str | None = Query(None, description="Filter by event type"),
    service: str | None = Query(None, description="Filter by service name"),
    status: str | None = Query(None, description="Filter: success or failed"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BridgeActivityResponse:
    """Get paginated bridge delivery activity for the current user.

    Supports filtering by event type, service name, and delivery status.

    Args:
        page: Page number (1-based).
        per_page: Items per page (max 100).
        event: Optional event type filter (e.g. ``"product.created"``).
        service: Optional service name filter (e.g. ``"contentforge"``).
        status: Optional status filter (``"success"`` or ``"failed"``).
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        Paginated list of delivery records with total and page metadata.
    """
    deliveries, total = await get_recent_activity(
        db=db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        event_filter=event,
        service_filter=service,
        status_filter=status,
    )

    return BridgeActivityResponse(
        items=[_delivery_to_response(d) for d in deliveries],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, math.ceil(total / per_page)),
    )


@router.get(
    "/activity/{resource_type}/{resource_id}",
    response_model=list[BridgeDeliveryResponse],
)
async def get_resource_activity(
    resource_type: str,
    resource_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BridgeDeliveryResponse]:
    """Get delivery history for a specific resource (product, order, customer).

    Args:
        resource_type: Type of resource (``"product"``, ``"order"``,
            ``"customer"``).
        resource_id: UUID string of the resource.
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        List of delivery records for the resource, most recent first.
    """
    deliveries = await get_resource_deliveries(
        db=db,
        resource_id=resource_id,
        resource_type=resource_type,
    )
    return [_delivery_to_response(d) for d in deliveries]


@router.get(
    "/service/{service_name}/activity",
    response_model=list[BridgeDeliveryResponse],
)
async def get_service_activity_endpoint(
    service_name: str,
    limit: int = Query(10, ge=1, le=50, description="Max items"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BridgeDeliveryResponse]:
    """Get recent delivery activity for a specific service.

    Args:
        service_name: Service identifier (e.g. ``"contentforge"``).
        limit: Maximum items to return (1-50).
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        List of delivery records for the service, most recent first.
    """
    deliveries = await get_service_activity(
        db=db,
        user_id=current_user.id,
        service_name=service_name,
        limit=limit,
    )
    return [_delivery_to_response(d) for d in deliveries]


@router.get("/summary", response_model=list[ServiceSummaryResponse])
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceSummaryResponse]:
    """Get per-service delivery summary for the last 24 hours.

    Returns a list of service summaries with last event time, success
    status, and failure count.

    Args:
        current_user: The authenticated user.
        db: Async database session.

    Returns:
        List of service summaries.
    """
    summary = await get_service_summary(db=db, user_id=current_user.id)
    return [
        ServiceSummaryResponse(
            service_name=svc_name,
            last_event_at=data["last_event_at"],
            last_success=data["last_success"],
            failure_count_24h=data["failure_count_24h"],
        )
        for svc_name, data in summary.items()
    ]


@router.post("/dispatch", response_model=dict)
async def dispatch_event(
    request: BridgeDispatchRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Manually dispatch a platform event (admin/debug endpoint).

    Fires the event via the Celery bridge task. Returns immediately;
    the actual delivery happens asynchronously.

    Args:
        request: The dispatch request body.
        current_user: The authenticated user.

    Returns:
        Confirmation dict with the event type and resource info.
    """
    store_id = uuid.UUID(request.store_id) if request.store_id else None
    fire_platform_event(
        user_id=current_user.id,
        store_id=store_id,
        event=request.event,
        resource_id=uuid.UUID(request.resource_id),
        resource_type=request.resource_type,
        payload=request.payload,
    )
    return {
        "status": "dispatched",
        "event": request.event,
        "resource_id": request.resource_id,
        "resource_type": request.resource_type,
    }
