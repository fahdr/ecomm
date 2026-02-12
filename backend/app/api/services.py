"""Services API router.

Provides endpoints for managing connections between the dropshipping platform
and 8 standalone SaaS microservices: TrendScout (A1), ContentForge (A2),
RankPilot (A3), FlowSend (A4), SpyDrop (A5), PostPilot (A6), AdScale (A7),
and ShopChat (A8).

**For Developers:**
    The router is mounted at ``/services`` (full path: ``/api/v1/services``).
    Public endpoints (catalog, bundles) require no authentication. All other
    endpoints require a valid JWT via ``get_current_user``. Service functions
    are imported from ``app.services.service_integration_service``.

    Error mapping:
    - ``ProvisionResult.success == False`` -> 400 (invalid/unknown) or 409
      (duplicate) depending on error text
    - ``disconnect_service`` returns ``False`` -> 404 (not connected)
    - ``fetch_service_usage`` returns ``{"error": ...}`` -> 404 or 502
    - ``upgrade_service`` returns ``{"error": ...}`` -> 400/404/502

**For Project Managers:**
    These endpoints power the "Connected Services" dashboard feature,
    letting users browse available services, connect/disconnect them,
    view usage metrics, upgrade tiers, and see what's included in
    their platform plan.

**For QA Engineers:**
    - ``GET /services/catalog`` and ``GET /services/bundles`` are public
      (no auth required).
    - All other endpoints return 401 without a valid token.
    - ``POST /{service_name}/provision`` returns 201 on success, 400 for
      invalid service name, 409 if already connected, 502 if external
      service is unreachable.
    - ``DELETE /{service_name}`` returns 204 on success, 400 for invalid
      service name, 404 if not connected.
    - ``GET /{service_name}/usage`` returns 200 with metrics or 404 if
      not connected.
    - ``POST /{service_name}/upgrade`` returns 200 on success, 404 if
      not connected, 422 for invalid tier.
    - ``GET /services/usage/summary`` aggregates usage across all
      connected services.
    - The ``api_key`` field is NEVER exposed in any response.

**For End Users:**
    - Browse the catalog to see what AI-powered tools are available.
    - Connect services from your dashboard to extend your store's
      capabilities.
    - Monitor usage and upgrade tiers as your business grows.
    - Check what services are included with your platform plan.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.service_integration import ServiceName, ServiceTier
from app.models.user import User
from app.schemas.services import (
    BundledServiceInfo,
    PlatformBundleInfo,
    ProvisionServiceRequest,
    ProvisionServiceResponse,
    ServiceInfo,
    ServiceStatus,
    ServiceTierInfo,
    ServiceUsageResponse,
    ServiceUsageSummary,
    UpgradeServiceRequest,
)

router = APIRouter(prefix="/services", tags=["services"])


# ---------------------------------------------------------------------------
# Helper: validate service name from URL path
# ---------------------------------------------------------------------------


def _parse_service_name(raw: str) -> ServiceName:
    """Validate and convert a raw string to a ``ServiceName`` enum.

    Args:
        raw: The service name string from the URL path.

    Returns:
        The corresponding ``ServiceName`` enum value.

    Raises:
        HTTPException 400: If the string is not a valid service name.

    **For Developers:**
        This is used by every ``/{service_name}/*`` endpoint to convert
        the path parameter to a strongly-typed enum before passing it
        to the service layer.

    **For QA Engineers:**
        An invalid service name returns 400 with a message listing
        the valid options.
    """
    try:
        return ServiceName(raw)
    except ValueError:
        valid = ", ".join(s.value for s in ServiceName)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown service: '{raw}'. Valid services: {valid}",
        )


def _catalog_entry_to_service_info(
    name: ServiceName,
    entry: dict[str, Any],
) -> ServiceInfo:
    """Convert a catalog dict entry into a ``ServiceInfo`` schema.

    Args:
        name: The service name enum.
        entry: The catalog dict with display_name, tagline, etc.

    Returns:
        A ``ServiceInfo`` Pydantic model.

    **For Developers:**
        The catalog stores tiers as plain dicts with a ``tier`` key
        (string). This helper converts those to ``ServiceTierInfo``
        models for the response schema.
    """
    tiers = [
        ServiceTierInfo(
            tier=t["tier"],
            name=t["name"],
            price_monthly_cents=t["price_monthly_cents"],
            features=t.get("features", []),
        )
        for t in entry.get("tiers", [])
    ]
    return ServiceInfo(
        name=name,
        display_name=entry["display_name"],
        tagline=entry["tagline"],
        description=entry["description"],
        icon=entry["icon"],
        color=entry["color"],
        dashboard_url=entry["dashboard_url"],
        landing_url=entry["landing_url"],
        tiers=tiers,
    )


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------


@router.get("/catalog", response_model=list[ServiceInfo])
async def get_service_catalog() -> list[ServiceInfo]:
    """List all available external services with metadata.

    Returns the full catalog of 8 SaaS microservices that can be
    integrated with the dropshipping platform. Each entry includes
    the service name, description, available tiers, and pricing.

    **No authentication required.** This endpoint is public so
    prospective users can explore available integrations.

    Returns:
        A list of ServiceInfo objects for all 8 services.

    **For Developers:**
        Calls ``get_service_catalog()`` which returns a dict keyed by
        ``ServiceName``. Each entry is converted to a ``ServiceInfo``
        schema by ``_catalog_entry_to_service_info``.

    **For QA Engineers:**
        - Returns 200 with exactly 8 services.
        - Each service has ``name``, ``display_name``, ``tagline``,
          ``description``, ``icon``, ``color``, ``dashboard_url``,
          ``landing_url``, and ``tiers``.
        - Each service has exactly 3 tiers (free, pro, enterprise).
        - No auth header required.

    **For End Users:**
        Browse all available AI-powered services you can connect
        to your dropshipping platform.
    """
    from app.services import service_integration_service

    catalog = service_integration_service.get_service_catalog()
    return [
        _catalog_entry_to_service_info(name, entry)
        for name, entry in catalog.items()
    ]


@router.get("/bundles", response_model=list[PlatformBundleInfo])
async def get_service_bundles(
    plan: str | None = Query(
        default=None,
        description="Filter by platform plan tier (free, starter, growth, pro)",
    ),
) -> list[PlatformBundleInfo]:
    """List what services are included in each platform plan.

    Shows which services (and at which tier) are included free
    with each platform subscription plan. Optionally filter to
    a specific plan.

    **No authentication required.** This is useful for the
    pricing page and plan comparison UI.

    Args:
        plan: Optional plan tier to filter by. If omitted, returns
            bundles for all 4 plans.

    Returns:
        A list of PlatformBundleInfo objects, one per plan.

    Raises:
        HTTPException 400: If an invalid plan name is provided.

    **For Developers:**
        Calls ``get_bundled_services(plan)`` for each requested plan.
        The service layer returns ``dict[ServiceName, ServiceTier]``
        which is converted to ``BundledServiceInfo`` list for the schema.

    **For QA Engineers:**
        - Without ``plan`` param: returns 4 bundles (free, starter,
          growth, pro).
        - Growth plan includes all 8 services at free tier.
        - Pro plan includes all 8 services at pro tier.
        - Free plan includes 0 services (empty ``included_services``).
        - Invalid plan returns 400.

    **For End Users:**
        See which AI services come free with your platform plan,
        so you know what you get when you upgrade.
    """
    from app.services import service_integration_service

    valid_plans = ["free", "starter", "growth", "pro"]

    if plan is not None:
        if plan not in valid_plans:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan: '{plan}'. Valid plans: {', '.join(valid_plans)}",
            )
        plans_to_query = [plan]
    else:
        plans_to_query = valid_plans

    results: list[PlatformBundleInfo] = []
    for p in plans_to_query:
        bundled = service_integration_service.get_bundled_services(p)
        included_services = [
            BundledServiceInfo(
                service_name=svc_name,
                included_tier=svc_tier,
                can_upgrade=svc_tier != ServiceTier.pro,
            )
            for svc_name, svc_tier in bundled.items()
        ]
        results.append(
            PlatformBundleInfo(
                plan=p,
                included_services=included_services,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("/usage/summary", response_model=ServiceUsageSummary)
async def get_usage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceUsageSummary:
    """Get aggregated usage across all connected services.

    Fetches current-period usage from each connected service and
    returns a summary with total monthly cost and per-service
    usage data.

    Args:
        current_user: The authenticated platform user.
        db: Async database session.

    Returns:
        ServiceUsageSummary with services list, total_monthly_cost_cents,
        and bundle_savings_cents.

    **For Developers:**
        Calls ``get_usage_summary(db, user_id)`` which returns a
        ``UsageSummary`` dataclass. The dataclass fields are mapped
        to the ``ServiceUsageSummary`` Pydantic schema.

    **For QA Engineers:**
        - Requires authentication (401 without token).
        - ``services`` list contains only connected services.
        - ``total_monthly_cost_cents`` is the sum of tier prices.
        - Unreachable services appear with empty ``metrics``.

    **For End Users:**
        View a single dashboard showing usage and costs across
        all your connected AI services.
    """
    from app.services import service_integration_service

    summary = await service_integration_service.get_usage_summary(
        db, current_user.id
    )

    # Convert UsageSummary dataclass to ServiceUsageSummary schema.
    # The service layer returns raw dicts for each service; convert
    # to ServiceUsageResponse where possible.
    now = datetime.now(timezone.utc)
    today = date.today()
    service_usages: list[ServiceUsageResponse] = []
    total_cost = 0

    for svc_data in summary.services:
        svc_name_str = svc_data.get("service_name", "")
        tier_str = svc_data.get("tier", "free")

        # Look up tier cost from catalog.
        try:
            svc_name_enum = ServiceName(svc_name_str)
        except ValueError:
            continue

        catalog = service_integration_service.SERVICE_CATALOG.get(svc_name_enum, {})
        for t in catalog.get("tiers", []):
            if t["tier"] == tier_str:
                total_cost += t.get("price_monthly_cents", 0)
                break

        service_usages.append(
            ServiceUsageResponse(
                service_name=svc_name_enum,
                tier=ServiceTier(tier_str),
                period_start=date.fromisoformat(svc_data["period_start"])
                if svc_data.get("period_start")
                else today.replace(day=1),
                period_end=date.fromisoformat(svc_data["period_end"])
                if svc_data.get("period_end")
                else today,
                metrics=svc_data.get("metrics", {}),
                fetched_at=now,
            )
        )

    return ServiceUsageSummary(
        services=service_usages,
        total_monthly_cost_cents=total_cost,
        bundle_savings_cents=0,
    )


@router.get("", response_model=list[ServiceStatus])
async def list_user_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceStatus]:
    """List all services with the user's connection status.

    Returns all 8 services, each annotated with whether the user
    has an active integration. Connected services include the tier
    and provisioned timestamp.

    Args:
        current_user: The authenticated platform user.
        db: Async database session.

    Returns:
        A list of 8 ServiceStatus objects with connection information.

    **For Developers:**
        Calls ``get_user_services(db, user_id)`` which returns a list
        of ``ServiceStatus`` dataclass instances (from the service layer).
        Each is converted to the Pydantic ``ServiceStatus`` schema by
        nesting ``ServiceInfo`` and mapping fields.

    **For QA Engineers:**
        - Requires authentication (401 without token).
        - Always returns exactly 8 services.
        - Connected services have ``is_connected=True``, ``current_tier``,
          ``provisioned_at``, and ``integration_id`` populated.
        - Disconnected services have ``is_connected=False`` and
          null values for current_tier/provisioned_at/integration_id.

    **For End Users:**
        See all available AI services and which ones you've
        connected to your platform.
    """
    from app.services import service_integration_service

    statuses = await service_integration_service.get_user_services(
        db, current_user.id
    )

    # Convert service-layer ServiceStatus dataclasses to schema ServiceStatus.
    result: list[ServiceStatus] = []
    for s in statuses:
        # Build the nested ServiceInfo from the dataclass fields.
        service_info = ServiceInfo(
            name=s.service_name,
            display_name=s.display_name,
            tagline=s.tagline,
            description=s.description,
            icon=s.icon,
            color=s.color,
            dashboard_url=s.dashboard_url,
            landing_url=s.landing_url,
            tiers=[
                ServiceTierInfo(
                    tier=t["tier"],
                    name=t["name"],
                    price_monthly_cents=t["price_monthly_cents"],
                    features=t.get("features", []),
                )
                for t in s.tiers
            ],
        )

        result.append(
            ServiceStatus(
                service=service_info,
                is_connected=s.is_connected,
                integration_id=s.integration_id,
                current_tier=s.current_tier,
                is_active=s.is_connected,
                provisioned_at=s.provisioned_at,
                usage=None,
            )
        )

    return result


@router.post(
    "/{service_name}/provision",
    response_model=ProvisionServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_service(
    service_name: str,
    request: ProvisionServiceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProvisionServiceResponse:
    """Provision (connect) the user in an external service.

    Creates an account for the user in the specified external SaaS
    microservice and stores the integration credentials in the
    platform database.

    Args:
        service_name: The service to provision (e.g. ``trendscout``).
            Taken from the URL path.
        request: Provisioning options (service_name, store_id, tier).
        current_user: The authenticated platform user.
        db: Async database session.

    Returns:
        ProvisionServiceResponse with the integration ID, service user ID,
        dashboard URL, tier, and provisioned timestamp.

    Raises:
        HTTPException 400: If the service name is invalid or the external
            service returned an incomplete response.
        HTTPException 409: If the user is already connected to this service.
        HTTPException 502: If the external service is unreachable.

    **For Developers:**
        Calls ``provision_service(db, user, service_name, store_id, tier)``
        which makes an HTTP POST to the external service and returns a
        ``ProvisionResult`` dataclass. The ``success`` field determines the
        HTTP status; the ``error`` field determines 400 vs 409 vs 502.

    **For QA Engineers:**
        - Requires authentication (401 without token).
        - Returns 201 on success with dashboard URL.
        - Returns 400 for unknown service names.
        - Returns 409 if already connected (duplicate).
        - Returns 502 if external service is down.

    **For End Users:**
        Connect an AI service to your platform. You'll receive a
        direct link to the service dashboard.
    """
    from app.services import service_integration_service

    svc_name = _parse_service_name(service_name)

    result = await service_integration_service.provision_service(
        db,
        user=current_user,
        service_name=svc_name,
        store_id=request.store_id,
        tier=request.tier,
    )

    if not result.success:
        error = result.error or "Provisioning failed"
        if "already" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=error
            )
        elif "unavailable" in error.lower() or "timed out" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error
            )

    # Look up dashboard URL from catalog.
    catalog = service_integration_service.SERVICE_CATALOG.get(svc_name, {})
    dashboard_url = catalog.get("dashboard_url", "")

    return ProvisionServiceResponse(
        integration_id=result.integration_id,
        service_name=result.service_name,
        service_user_id=result.service_user_id or "",
        tier=result.tier,
        dashboard_url=dashboard_url,
        provisioned_at=datetime.now(timezone.utc),
    )


@router.delete("/{service_name}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_service(
    service_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Disconnect (deactivate) a service integration.

    Marks the user's integration with the specified service as
    inactive. Does not delete the record or call the external
    service -- those are handled by background cleanup jobs.

    Args:
        service_name: The service to disconnect (e.g. ``trendscout``).
        current_user: The authenticated platform user.
        db: Async database session.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException 400: If the service name is invalid.
        HTTPException 404: If the user has no active integration with
            this service.

    **For Developers:**
        Calls ``disconnect_service(db, user_id, service_name)`` which
        returns ``True`` on success or ``False`` if no active integration
        was found.

    **For QA Engineers:**
        - Requires authentication (401 without token).
        - Returns 204 with empty body on success.
        - Returns 400 for unknown service names.
        - Returns 404 if the user is not connected to this service.
        - After disconnect, the service should show ``is_connected=False``
          in the ``GET /services`` list.

    **For End Users:**
        Disconnect an AI service you no longer need. Your data is
        preserved for 30 days in case you want to reconnect.
    """
    from app.services import service_integration_service

    svc_name = _parse_service_name(service_name)

    disconnected = await service_integration_service.disconnect_service(
        db, current_user.id, svc_name
    )

    if not disconnected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active integration found for {svc_name.value}",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{service_name}/usage", response_model=ServiceUsageResponse)
async def get_service_usage(
    service_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceUsageResponse:
    """Get usage data for a connected service.

    Fetches the current billing period's usage metrics from the
    external service and returns them along with the user's tier.

    Args:
        service_name: The service to fetch usage for (e.g. ``trendscout``).
        current_user: The authenticated platform user.
        db: Async database session.

    Returns:
        ServiceUsageResponse with tier, billing period, metrics, and
        fetched_at timestamp.

    Raises:
        HTTPException 400: If the service name is invalid.
        HTTPException 404: If the user has no active integration with
            this service.
        HTTPException 502: If the external service is unreachable.

    **For Developers:**
        First looks up the user's integration for the given service to
        get the ``integration_id``, then calls ``fetch_service_usage(db,
        integration_id)`` which makes an HTTP GET to the external service.

    **For QA Engineers:**
        - Requires authentication (401 without token).
        - Returns 200 with ``service_name``, ``tier``, ``period_start``,
          ``period_end``, ``metrics`` dict, and ``fetched_at``.
        - Returns 400 for unknown service names.
        - Returns 404 if not connected.
        - Returns 502 if external service is unreachable.
        - ``metrics`` schema varies per service.

    **For End Users:**
        Check how much of your service quota you've used this
        billing period (e.g. research runs, email sends).
    """
    from app.services import service_integration_service

    svc_name = _parse_service_name(service_name)

    # Look up user's active integration for this service to get the
    # integration_id needed by fetch_service_usage.
    from sqlalchemy import select
    from app.models.service_integration import ServiceIntegration

    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == current_user.id,
            ServiceIntegration.service_name == svc_name,
            ServiceIntegration.is_active.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active integration found for {svc_name.value}. Provision it first.",
        )

    usage = await service_integration_service.fetch_service_usage(
        db, integration.id
    )

    if "error" in usage:
        error_msg = usage["error"]
        if "unavailable" in error_msg.lower() or "timed out" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        )

    now = datetime.now(timezone.utc)
    today = date.today()

    return ServiceUsageResponse(
        service_name=svc_name,
        tier=integration.tier,
        period_start=today.replace(day=1),
        period_end=today,
        metrics=usage.get("metrics", {}),
        fetched_at=now,
    )


@router.post("/{service_name}/upgrade")
async def upgrade_service(
    service_name: str,
    request: UpgradeServiceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upgrade the subscription tier for a connected service.

    Changes the user's tier in the external service and updates
    the local integration record.

    Args:
        service_name: The service to upgrade (e.g. ``trendscout``).
        request: The upgrade payload with the target tier.
        current_user: The authenticated platform user.
        db: Async database session.

    Returns:
        A dict with ``service_name``, ``old_tier``, ``new_tier``, and
        ``message``.

    Raises:
        HTTPException 400: If the service name is invalid or same tier.
        HTTPException 404: If the user has no active integration with
            this service.
        HTTPException 502: If the external service is unreachable.

    **For Developers:**
        Calls ``upgrade_service(db, user_id, service_name, new_tier)``
        which returns a dict with either ``"success": True`` or
        ``"error": "..."`` to indicate the outcome.

    **For QA Engineers:**
        - Requires authentication (401 without token).
        - Returns 200 with ``old_tier``, ``new_tier``, and ``message``.
        - Returns 400 for unknown service names or same-tier upgrade.
        - Returns 404 if not connected.
        - Returns 502 if external service is unreachable.

    **For End Users:**
        Upgrade your AI service tier to unlock higher quotas and
        premium features.
    """
    from app.services import service_integration_service

    svc_name = _parse_service_name(service_name)

    result = await service_integration_service.upgrade_service(
        db, current_user.id, svc_name, request.tier
    )

    if "error" in result:
        error = result["error"]
        if "no active integration" in error.lower() or "provision" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=error
            )
        elif "unavailable" in error.lower() or "timed out" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error
            )

    return {
        "service_name": result.get("service_name", svc_name.value),
        "old_tier": result.get("old_tier"),
        "new_tier": result.get("new_tier"),
        "message": (
            f"Upgraded {svc_name.value} from {result.get('old_tier')} "
            f"to {result.get('new_tier')}"
        ),
    }
