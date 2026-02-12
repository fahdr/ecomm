"""Service integration business logic layer.

Manages the lifecycle of external SaaS microservice integrations: provisioning
user accounts in remote services, tracking connection state in the database,
fetching usage metrics, handling plan-bundled service tiers, and aggregating
cross-service usage summaries.

The dropshipping platform integrates with 8 standalone SaaS microservices,
each exposing a provisioning API (``POST /api/v1/auth/provision``), a usage
endpoint (``GET /api/v1/usage``), and a health check (``GET /api/v1/health``).
This module is the single point of coordination between the platform backend
and those external services.

**For Developers:**
    All functions are async (except the two pure-data catalog/bundle
    lookups). External HTTP calls use ``httpx.AsyncClient`` with a 10-second
    timeout and are wrapped in try/except so that an unreachable microservice
    never crashes the platform request -- callers receive structured error
    dicts instead of unhandled exceptions.

    The ``SERVICE_CATALOG`` constant is the single source of truth for
    service metadata (display names, URLs, tier definitions). It is
    referenced by API endpoints, the dashboard, and the storefront landing
    pages. To add a new service, add an entry to ``ServiceName`` in
    ``app.models.service_integration``, then add the corresponding catalog
    entry here.

    ``PLATFORM_BUNDLES`` maps platform subscription plans (free, starter,
    growth, pro) to the service tiers included with each plan. When a user
    upgrades their platform plan, ``auto_provision_bundled_services`` is
    called to provision or upgrade all bundled services automatically.

**For Project Managers:**
    This service powers the "Connected Services" dashboard and the
    per-service landing pages. It enables users to connect to AI-powered
    tools (product research, content generation, SEO, email marketing,
    competitor monitoring, social media, ad campaigns, AI chatbot) from
    a single platform. Platform plans (Growth, Pro) bundle service access
    at no extra cost, driving upsell from the free tier.

**For QA Engineers:**
    - ``provision_service`` is idempotent for active integrations: calling
      it twice for the same user + service returns an error result rather
      than creating a duplicate (enforced by the DB unique constraint).
    - ``disconnect_service`` soft-deletes by setting ``is_active = False``.
    - ``fetch_service_usage`` stores a snapshot in ``service_usage`` and
      updates ``last_synced_at`` on the integration.
    - If an external service is down, HTTP-calling functions log a warning
      and return a structured error dict instead of raising an exception.
    - ``upgrade_service`` validates the new tier against ``ServiceTier``.
    - ``auto_provision_bundled_services`` skips services that are already
      connected at an equal or higher tier.

**For End Users:**
    Connect your dropshipping platform to powerful AI tools with one click.
    Your platform plan may include free access to some or all services.
    From the Services dashboard you can see which tools are connected,
    view your usage, and upgrade individual service tiers for more capacity.
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PlanTier
from app.models.service_integration import (
    ServiceIntegration,
    ServiceName,
    ServiceTier,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP client configuration
# ---------------------------------------------------------------------------

#: Default timeout for external service HTTP calls (seconds).
_HTTP_TIMEOUT = 10.0


# ---------------------------------------------------------------------------
# Data classes for structured return types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServiceStatus:
    """Connection status of a single service for a user.

    Returned by ``get_user_services`` to give the dashboard a unified view
    of all 8 services regardless of whether the user has connected them.

    Attributes:
        service_name: The machine-readable service identifier.
        display_name: Human-friendly service name (e.g. "TrendScout").
        tagline: Short marketing tagline for the service.
        description: Longer description of what the service does.
        icon: Lucide icon name used by the dashboard UI.
        color: Hex color code for the service's brand accent.
        base_url: Backend API URL for the service.
        dashboard_url: Frontend dashboard URL for the service.
        landing_url: Platform landing page path for the service.
        tiers: List of tier definitions (name, price, features).
        is_connected: Whether the user has an active integration.
        current_tier: The user's current tier, or None if not connected.
        integration_id: UUID of the integration record, or None.
        provisioned_at: Timestamp when the service was provisioned, or None.
    """

    service_name: ServiceName
    display_name: str
    tagline: str
    description: str
    icon: str
    color: str
    base_url: str
    dashboard_url: str
    landing_url: str
    tiers: list[dict[str, Any]]
    is_connected: bool
    current_tier: ServiceTier | None
    integration_id: uuid.UUID | None
    provisioned_at: datetime | None


@dataclass(frozen=True)
class ProvisionResult:
    """Result of provisioning a user in an external service.

    Attributes:
        success: Whether provisioning succeeded.
        service_name: Which service was provisioned.
        service_user_id: The user's ID in the external service (on success).
        integration_id: UUID of the created integration record (on success).
        tier: The tier the user was provisioned at.
        error: Error message if provisioning failed, else None.
    """

    success: bool
    service_name: ServiceName
    service_user_id: str | None
    integration_id: uuid.UUID | None
    tier: ServiceTier
    error: str | None


@dataclass(frozen=True)
class UsageSummary:
    """Aggregated usage across all connected services for a user.

    Attributes:
        total_connected: Number of active service integrations.
        total_available: Total number of services in the catalog (always 8).
        services: Per-service usage dicts (service_name, tier, latest metrics).
        last_updated: Most recent sync timestamp across all services.
    """

    total_connected: int
    total_available: int
    services: list[dict[str, Any]]
    last_updated: datetime | None


# ---------------------------------------------------------------------------
# Service catalog -- single source of truth for all 8 microservices
# ---------------------------------------------------------------------------

SERVICE_CATALOG: dict[ServiceName, dict[str, Any]] = {
    ServiceName.trendscout: {
        "display_name": "TrendScout",
        "tagline": "AI-Powered Product Research",
        "description": (
            "Discover winning products with AI across AliExpress, TikTok, "
            "Google Trends, and Reddit."
        ),
        "icon": "search",
        "color": "#3b82f6",
        "base_url": os.getenv("TRENDSCOUT_URL", "http://localhost:8101"),
        "dashboard_url": os.getenv(
            "TRENDSCOUT_DASHBOARD_URL", "http://localhost:3101"
        ),
        "landing_url": "/services/trendscout",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "5 research runs/mo",
                    "2 sources",
                    "25 watchlist items",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 2900,
                "features": [
                    "50 research runs/mo",
                    "All sources",
                    "500 watchlist items",
                    "AI analysis",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 9900,
                "features": [
                    "Unlimited runs",
                    "All sources + API",
                    "Unlimited watchlist",
                    "Priority AI",
                ],
            },
        ],
    },
    ServiceName.contentforge: {
        "display_name": "ContentForge",
        "tagline": "AI Product Content Generator",
        "description": (
            "Generate optimized titles, descriptions, and images for your "
            "product listings."
        ),
        "icon": "pencil",
        "color": "#8b5cf6",
        "base_url": os.getenv("CONTENTFORGE_URL", "http://localhost:8102"),
        "dashboard_url": os.getenv(
            "CONTENTFORGE_DASHBOARD_URL", "http://localhost:3102"
        ),
        "landing_url": "/services/contentforge",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "10 generations/mo",
                    "500 words/gen",
                    "5 images",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 1900,
                "features": [
                    "200 generations/mo",
                    "2000 words/gen",
                    "100 images",
                    "Bulk import",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 7900,
                "features": [
                    "Unlimited generations",
                    "Unlimited words",
                    "Unlimited images",
                    "API access",
                ],
            },
        ],
    },
    ServiceName.rankpilot: {
        "display_name": "RankPilot",
        "tagline": "Automated SEO Engine",
        "description": (
            "Boost search rankings with AI blog posts, sitemaps, schema "
            "markup, and keyword tracking."
        ),
        "icon": "trending-up",
        "color": "#10b981",
        "base_url": os.getenv("RANKPILOT_URL", "http://localhost:8103"),
        "dashboard_url": os.getenv(
            "RANKPILOT_DASHBOARD_URL", "http://localhost:3103"
        ),
        "landing_url": "/services/rankpilot",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "2 blog posts/mo",
                    "20 keywords",
                    "1 sitemap",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 2900,
                "features": [
                    "20 blog posts/mo",
                    "200 keywords",
                    "5 sitemaps",
                    "JSON-LD",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 9900,
                "features": [
                    "Unlimited posts",
                    "Unlimited keywords",
                    "Unlimited sitemaps",
                    "API access",
                ],
            },
        ],
    },
    ServiceName.flowsend: {
        "display_name": "FlowSend",
        "tagline": "Smart Email Marketing",
        "description": (
            "Automate email campaigns with visual flows, A/B testing, and "
            "smart segmentation."
        ),
        "icon": "mail",
        "color": "#ef4444",
        "base_url": os.getenv("FLOWSEND_URL", "http://localhost:8104"),
        "dashboard_url": os.getenv(
            "FLOWSEND_DASHBOARD_URL", "http://localhost:3104"
        ),
        "landing_url": "/services/flowsend",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "500 emails/mo",
                    "2 flows",
                    "250 contacts",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 3900,
                "features": [
                    "25K emails/mo",
                    "20 flows",
                    "10K contacts",
                    "A/B testing",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 14900,
                "features": [
                    "Unlimited emails",
                    "Unlimited flows",
                    "Unlimited contacts",
                    "API access",
                ],
            },
        ],
    },
    ServiceName.spydrop: {
        "display_name": "SpyDrop",
        "tagline": "Competitor Intelligence",
        "description": (
            "Monitor competitor stores, track prices, and discover winning "
            "products."
        ),
        "icon": "eye",
        "color": "#06b6d4",
        "base_url": os.getenv("SPYDROP_URL", "http://localhost:8105"),
        "dashboard_url": os.getenv(
            "SPYDROP_DASHBOARD_URL", "http://localhost:3105"
        ),
        "landing_url": "/services/spydrop",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "3 competitors",
                    "Weekly scans",
                    "Basic alerts",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 2900,
                "features": [
                    "25 competitors",
                    "Daily scans",
                    "Price alerts",
                    "Source finding",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 9900,
                "features": [
                    "Unlimited competitors",
                    "Hourly scans",
                    "All features + API",
                ],
            },
        ],
    },
    ServiceName.postpilot: {
        "display_name": "PostPilot",
        "tagline": "Social Media Automation",
        "description": (
            "Schedule and auto-post to Instagram, Facebook, and TikTok "
            "with AI captions."
        ),
        "icon": "share-2",
        "color": "#ec4899",
        "base_url": os.getenv("POSTPILOT_URL", "http://localhost:8106"),
        "dashboard_url": os.getenv(
            "POSTPILOT_DASHBOARD_URL", "http://localhost:3106"
        ),
        "landing_url": "/services/postpilot",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "10 posts/mo",
                    "1 platform",
                    "5 AI captions",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 2900,
                "features": [
                    "200 posts/mo",
                    "All platforms",
                    "Unlimited AI",
                    "Auto-schedule",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 9900,
                "features": [
                    "Unlimited posts",
                    "All platforms + API",
                    "Analytics",
                    "Auto-schedule",
                ],
            },
        ],
    },
    ServiceName.adscale: {
        "display_name": "AdScale",
        "tagline": "AI Ad Campaign Manager",
        "description": (
            "Create and optimize Google & Meta ad campaigns with AI-powered "
            "automation."
        ),
        "icon": "target",
        "color": "#f59e0b",
        "base_url": os.getenv("ADSCALE_URL", "http://localhost:8107"),
        "dashboard_url": os.getenv(
            "ADSCALE_DASHBOARD_URL", "http://localhost:3107"
        ),
        "landing_url": "/services/adscale",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "2 campaigns",
                    "1 platform",
                    "5 AI copies",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 4900,
                "features": [
                    "25 campaigns",
                    "Both platforms",
                    "Unlimited AI",
                    "Auto-optimize",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 14900,
                "features": [
                    "Unlimited campaigns",
                    "All platforms + API",
                    "ROAS targets",
                ],
            },
        ],
    },
    ServiceName.shopchat: {
        "display_name": "ShopChat",
        "tagline": "AI Shopping Assistant",
        "description": (
            "Add an AI chatbot to your store for 24/7 customer support and "
            "product recommendations."
        ),
        "icon": "message-circle",
        "color": "#6366f1",
        "base_url": os.getenv("SHOPCHAT_URL", "http://localhost:8108"),
        "dashboard_url": os.getenv(
            "SHOPCHAT_DASHBOARD_URL", "http://localhost:3108"
        ),
        "landing_url": "/services/shopchat",
        "tiers": [
            {
                "tier": "free",
                "name": "Free",
                "price_monthly_cents": 0,
                "features": [
                    "50 conversations/mo",
                    "Basic knowledge",
                    "Branding only",
                ],
            },
            {
                "tier": "pro",
                "name": "Pro",
                "price_monthly_cents": 1900,
                "features": [
                    "1K conversations/mo",
                    "Full catalog",
                    "Custom personality",
                ],
            },
            {
                "tier": "enterprise",
                "name": "Enterprise",
                "price_monthly_cents": 7900,
                "features": [
                    "Unlimited conversations",
                    "White-label",
                    "API access",
                ],
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Platform bundle definitions -- what services each plan tier includes
# ---------------------------------------------------------------------------

PLATFORM_BUNDLES: dict[str, dict[ServiceName, ServiceTier]] = {
    "free": {},  # No services included
    "starter": {
        ServiceName.trendscout: ServiceTier.free,
        ServiceName.contentforge: ServiceTier.free,
    },
    "growth": {name: ServiceTier.free for name in ServiceName},
    "pro": {name: ServiceTier.pro for name in ServiceName},
}

#: Tier ordering for comparison (higher index = higher tier).
_TIER_ORDER: dict[ServiceTier, int] = {
    ServiceTier.free: 0,
    ServiceTier.starter: 1,
    ServiceTier.growth: 2,
    ServiceTier.pro: 3,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tier_gte(a: ServiceTier, b: ServiceTier) -> bool:
    """Check whether tier ``a`` is greater than or equal to tier ``b``.

    Used to decide whether an existing integration already meets or exceeds
    the target tier during bundled auto-provisioning.

    Args:
        a: The tier to check.
        b: The tier to compare against.

    Returns:
        True if ``a`` is at least as high as ``b``.
    """
    return _TIER_ORDER.get(a, 0) >= _TIER_ORDER.get(b, 0)


async def _call_provision_api(
    base_url: str,
    email: str,
    user_id: str,
    tier: str,
    store_id: str | None = None,
) -> dict[str, Any]:
    """Call an external service's provisioning endpoint via HTTP POST.

    Makes a ``POST`` request to ``{base_url}/api/v1/auth/provision`` with
    the user's email, platform user ID, tier, and optional store ID. Returns
    the parsed JSON response on success, or a dict with an ``error`` key on
    failure.

    Args:
        base_url: The root URL of the external service (e.g.
            ``http://localhost:8101``).
        email: The user's email address.
        user_id: The platform user's UUID as a string.
        tier: The service tier to provision (``"free"``, ``"pro"``, or
            ``"enterprise"``).
        store_id: Optional store UUID string to scope the integration.

    Returns:
        A dict with ``user_id`` and ``api_key`` on success, or a dict
        with ``error`` (str) on failure.
    """
    payload: dict[str, Any] = {
        "email": email,
        "platform_user_id": user_id,
        "tier": tier,
    }
    if store_id:
        payload["store_id"] = store_id

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/api/v1/auth/provision",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.warning(
            "Timeout provisioning user %s in service at %s",
            user_id,
            base_url,
        )
        return {"error": f"Service at {base_url} timed out during provisioning"}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %d from %s during provisioning for user %s: %s",
            exc.response.status_code,
            base_url,
            user_id,
            exc.response.text[:200],
        )
        return {
            "error": (
                f"Service returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            )
        }
    except httpx.HTTPError as exc:
        logger.warning(
            "HTTP error provisioning user %s in service at %s: %s",
            user_id,
            base_url,
            str(exc),
        )
        return {"error": f"Service at {base_url} is unavailable: {exc}"}


async def _call_usage_api(
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    """Call an external service's usage endpoint via HTTP GET.

    Makes a ``GET`` request to ``{base_url}/api/v1/usage`` with the
    ``X-API-Key`` header. Returns the parsed JSON response on success,
    or a dict with an ``error`` key on failure.

    Args:
        base_url: The root URL of the external service.
        api_key: The API key for authenticating with the service.

    Returns:
        A dict of usage metrics on success, or a dict with ``error`` (str)
        on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(
                f"{base_url}/api/v1/usage",
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.warning("Timeout fetching usage from %s", base_url)
        return {"error": f"Service at {base_url} timed out"}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %d from %s during usage fetch: %s",
            exc.response.status_code,
            base_url,
            exc.response.text[:200],
        )
        return {
            "error": (
                f"Service returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            )
        }
    except httpx.HTTPError as exc:
        logger.warning(
            "HTTP error fetching usage from %s: %s", base_url, str(exc)
        )
        return {"error": f"Service at {base_url} is unavailable: {exc}"}


async def _call_upgrade_api(
    base_url: str,
    api_key: str,
    new_tier: str,
) -> dict[str, Any]:
    """Call an external service's tier upgrade endpoint via HTTP POST.

    Makes a ``POST`` request to ``{base_url}/api/v1/auth/upgrade`` with
    the new tier. Returns the parsed JSON response on success, or a dict
    with an ``error`` key on failure.

    Args:
        base_url: The root URL of the external service.
        api_key: The API key for authenticating with the service.
        new_tier: The target tier to upgrade to.

    Returns:
        A dict confirming the upgrade on success, or a dict with ``error``
        (str) on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{base_url}/api/v1/auth/upgrade",
                json={"tier": new_tier},
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.warning("Timeout upgrading tier at %s", base_url)
        return {"error": f"Service at {base_url} timed out during upgrade"}
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "HTTP %d from %s during upgrade: %s",
            exc.response.status_code,
            base_url,
            exc.response.text[:200],
        )
        return {
            "error": (
                f"Service returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            )
        }
    except httpx.HTTPError as exc:
        logger.warning(
            "HTTP error upgrading tier at %s: %s", base_url, str(exc)
        )
        return {"error": f"Service at {base_url} is unavailable: {exc}"}


# ---------------------------------------------------------------------------
# Public API -- the 9 functions
# ---------------------------------------------------------------------------


def get_service_catalog() -> dict[ServiceName, dict[str, Any]]:
    """Return the full service catalog with tier definitions.

    This is a synchronous function because the catalog is a static constant
    and requires no I/O. It returns a shallow copy so callers cannot mutate
    the module-level constant.

    **For Developers:**
        Use this to populate the services listing page or the service
        detail/landing pages. Each entry includes display metadata, URLs,
        and a ``tiers`` list with pricing and feature descriptions.

    **For QA Engineers:**
        Verify that the returned dict has exactly 8 entries (one per
        ``ServiceName`` enum member) and that each entry contains all
        required keys (``display_name``, ``tagline``, ``description``,
        ``icon``, ``color``, ``base_url``, ``dashboard_url``,
        ``landing_url``, ``tiers``).

    Returns:
        A dict mapping ``ServiceName`` to catalog metadata dicts.
    """
    # Return a shallow copy to prevent accidental mutation of the constant.
    return dict(SERVICE_CATALOG)


async def get_user_services(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[ServiceStatus]:
    """Return the connection status of all 8 services for a user.

    Queries the ``service_integrations`` table for active integrations owned
    by the user, then merges that data with the static ``SERVICE_CATALOG``
    to produce a unified list suitable for the dashboard's services grid.

    **For Developers:**
        The returned list always has exactly 8 entries (one per service),
        regardless of how many integrations the user has. Unconnected
        services have ``is_connected=False`` and ``current_tier=None``.

    **For QA Engineers:**
        - A user with no integrations should get 8 entries all showing
          ``is_connected=False``.
        - An inactive integration (``is_active=False``) should also show
          ``is_connected=False``.
        - The list is ordered by ``ServiceName`` enum definition order.

    Args:
        db: Async database session.
        user_id: The UUID of the user to query.

    Returns:
        A list of 8 ``ServiceStatus`` dataclass instances.
    """
    # Fetch all active integrations for this user in one query.
    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user_id,
            ServiceIntegration.is_active.is_(True),
        )
    )
    integrations = result.scalars().all()

    # Index by service_name for O(1) lookup.
    integration_map: dict[ServiceName, ServiceIntegration] = {
        integ.service_name: integ for integ in integrations
    }

    statuses: list[ServiceStatus] = []
    for svc_name in ServiceName:
        catalog = SERVICE_CATALOG[svc_name]
        integ = integration_map.get(svc_name)

        statuses.append(
            ServiceStatus(
                service_name=svc_name,
                display_name=catalog["display_name"],
                tagline=catalog["tagline"],
                description=catalog["description"],
                icon=catalog["icon"],
                color=catalog["color"],
                base_url=catalog["base_url"],
                dashboard_url=catalog["dashboard_url"],
                landing_url=catalog["landing_url"],
                tiers=catalog["tiers"],
                is_connected=integ is not None,
                current_tier=(
                    integ.tier if integ is not None else None
                ),
                integration_id=(integ.id if integ is not None else None),
                provisioned_at=(
                    integ.provisioned_at if integ is not None else None
                ),
            )
        )

    return statuses


async def provision_service(
    db: AsyncSession,
    user: User,
    service_name: ServiceName,
    store_id: uuid.UUID | None = None,
    tier: ServiceTier = ServiceTier.free,
) -> ProvisionResult:
    """Provision a user account in an external service and record the integration.

    Calls the external service's ``POST /api/v1/auth/provision`` endpoint,
    then creates a ``ServiceIntegration`` row in the database with the
    returned credentials. If the user already has an active integration for
    this service, returns an error result instead of duplicating.

    **For Developers:**
        The external API is expected to return ``{"user_id": "...",
        "api_key": "..."}`` on success. The ``api_key`` is stored in
        ``service_api_key_encrypted`` (in production, this column should
        use application-level encryption; in dev mode the key is stored
        as-is for simplicity).

        If the user previously had an integration that was disconnected
        (``is_active=False``), this function reactivates it with new
        credentials rather than creating a duplicate row (honoring the
        unique constraint on ``(user_id, service_name)``).

    **For QA Engineers:**
        - Calling twice for the same user + service returns a failure
          result with an appropriate error message.
        - If the external service is unreachable, the function returns a
          failure result without raising an exception.
        - The ``provisioned_at`` timestamp is set to the current UTC time.

    Args:
        db: Async database session.
        user: The authenticated platform user.
        service_name: Which service to provision.
        store_id: Optional store UUID to scope the integration. Pass None
            for user-level services.
        tier: The tier to provision at. Defaults to ``free``.

    Returns:
        A ``ProvisionResult`` indicating success or failure.
    """
    # Check for existing active integration.
    existing = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user.id,
            ServiceIntegration.service_name == service_name,
            ServiceIntegration.is_active.is_(True),
        )
    )
    if existing.scalar_one_or_none() is not None:
        return ProvisionResult(
            success=False,
            service_name=service_name,
            service_user_id=None,
            integration_id=None,
            tier=tier,
            error=(
                f"User already has an active integration with "
                f"{service_name.value}. Disconnect it first to re-provision."
            ),
        )

    # Look up the service in the catalog.
    catalog = SERVICE_CATALOG.get(service_name)
    if catalog is None:
        return ProvisionResult(
            success=False,
            service_name=service_name,
            service_user_id=None,
            integration_id=None,
            tier=tier,
            error=f"Unknown service: {service_name.value}",
        )

    # Call the external provisioning API.
    api_response = await _call_provision_api(
        base_url=catalog["base_url"],
        email=user.email,
        user_id=str(user.id),
        tier=tier.value,
        store_id=str(store_id) if store_id else None,
    )

    if "error" in api_response:
        return ProvisionResult(
            success=False,
            service_name=service_name,
            service_user_id=None,
            integration_id=None,
            tier=tier,
            error=api_response["error"],
        )

    service_user_id = api_response.get("user_id", "")
    service_api_key = api_response.get("api_key", "")

    if not service_user_id or not service_api_key:
        return ProvisionResult(
            success=False,
            service_name=service_name,
            service_user_id=None,
            integration_id=None,
            tier=tier,
            error=(
                "External service returned an incomplete response "
                "(missing user_id or api_key)."
            ),
        )

    # Check for an existing inactive integration to reactivate, honoring
    # the unique constraint on (user_id, service_name).
    inactive_result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user.id,
            ServiceIntegration.service_name == service_name,
            ServiceIntegration.is_active.is_(False),
        )
    )
    existing_inactive = inactive_result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing_inactive is not None:
        # Reactivate the existing integration with new credentials.
        existing_inactive.service_user_id = service_user_id
        existing_inactive.api_key = service_api_key
        existing_inactive.tier = tier
        existing_inactive.store_id = store_id
        existing_inactive.is_active = True
        existing_inactive.provisioned_at = now
        integration = existing_inactive
    else:
        # Create a new integration record.
        integration = ServiceIntegration(
            user_id=user.id,
            store_id=store_id,
            service_name=service_name,
            service_user_id=service_user_id,
            api_key=service_api_key,
            tier=tier,
            is_active=True,
            provisioned_at=now,
        )
        db.add(integration)

    await db.flush()
    await db.refresh(integration)

    logger.info(
        "Provisioned user %s in %s (tier=%s, integration=%s)",
        user.id,
        service_name.value,
        tier.value,
        integration.id,
    )

    return ProvisionResult(
        success=True,
        service_name=service_name,
        service_user_id=service_user_id,
        integration_id=integration.id,
        tier=tier,
        error=None,
    )


async def disconnect_service(
    db: AsyncSession,
    user_id: uuid.UUID,
    service_name: ServiceName,
) -> bool:
    """Soft-disconnect a user from an external service.

    Sets ``is_active = False`` on the integration record rather than
    deleting it, preserving the audit trail and allowing reconnection
    later without losing historical usage data.

    **For Developers:**
        This does NOT call the external service's API to delete the user
        account -- it only marks the local integration as inactive. A future
        enhancement could add an optional ``revoke`` parameter to call a
        deprovisioning endpoint on the external service.

    **For QA Engineers:**
        - Returns ``True`` if an active integration was found and
          deactivated, ``False`` otherwise.
        - Calling ``disconnect_service`` on an already-disconnected service
          returns ``False`` (idempotent, no error raised).

    Args:
        db: Async database session.
        user_id: The UUID of the user.
        service_name: Which service to disconnect.

    Returns:
        True if an active integration was found and deactivated, False
        if no active integration existed for this user + service.
    """
    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user_id,
            ServiceIntegration.service_name == service_name,
            ServiceIntegration.is_active.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        logger.debug(
            "No active integration found for user %s and service %s",
            user_id,
            service_name.value,
        )
        return False

    integration.is_active = False
    await db.flush()
    await db.refresh(integration)

    logger.info(
        "Disconnected user %s from %s (integration=%s)",
        user_id,
        service_name.value,
        integration.id,
    )
    return True


async def fetch_service_usage(
    db: AsyncSession,
    integration_id: uuid.UUID,
) -> dict[str, Any]:
    """Fetch current usage metrics from an external service.

    Looks up the integration record and calls the external service's
    ``GET /api/v1/usage`` endpoint. Returns the usage data directly
    from the external service.

    **For Developers:**
        The external service returns a JSON dict with usage metrics
        (schema varies per service). This function acts as a pass-through
        proxy, adding the service name and tier for context.

    **For QA Engineers:**
        - Returns a dict with ``"metrics"`` key on success, or ``"error"``
          key on failure.
        - An inactive integration returns an error without calling the
          external service.
        - A missing integration returns an error.

    Args:
        db: Async database session.
        integration_id: UUID of the ServiceIntegration record.

    Returns:
        A dict with ``service_name``, ``tier``, and ``metrics`` on success,
        or ``error`` (str) on failure.
    """
    # Load the integration.
    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.id == integration_id
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        return {"error": "Integration not found"}

    if not integration.is_active:
        return {"error": "Integration is inactive"}

    # Look up service base URL.
    catalog = SERVICE_CATALOG.get(integration.service_name)
    if catalog is None:
        return {"error": f"Unknown service: {integration.service_name.value}"}

    # Call the external usage API.
    usage_data = await _call_usage_api(
        base_url=catalog["base_url"],
        api_key=integration.api_key,
    )

    if "error" in usage_data:
        return usage_data

    logger.info(
        "Fetched usage for integration %s (%s): %s",
        integration.id,
        integration.service_name.value,
        usage_data,
    )

    return {
        "service_name": integration.service_name.value,
        "tier": integration.tier.value,
        "metrics": usage_data,
    }


async def upgrade_service(
    db: AsyncSession,
    user_id: uuid.UUID,
    service_name: ServiceName,
    new_tier: ServiceTier,
) -> dict[str, Any]:
    """Upgrade a user's tier in an external service.

    Updates the tier in both the external service (via API call) and the
    local integration record. The new tier must be different from the
    current tier.

    **For Developers:**
        The external upgrade call is made to ``POST /api/v1/auth/upgrade``
        with the new tier. If the external call fails, the local record is
        NOT updated (consistency). If the external service does not support
        downgrades, it will return an HTTP error which is propagated.

    **For QA Engineers:**
        - Returns a dict with ``"success": True`` and the new tier on
          success, or ``"error"`` on failure.
        - Attempting to upgrade to the same tier returns an error.
        - An inactive or nonexistent integration returns an error.

    Args:
        db: Async database session.
        user_id: The UUID of the user.
        service_name: Which service to upgrade.
        new_tier: The target ``ServiceTier``.

    Returns:
        A dict with ``success`` (bool), ``service_name``, ``old_tier``,
        ``new_tier`` on success, or ``error`` (str) on failure.
    """
    # Load the integration.
    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user_id,
            ServiceIntegration.service_name == service_name,
            ServiceIntegration.is_active.is_(True),
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        return {
            "error": (
                f"No active integration found for {service_name.value}. "
                f"Provision the service first."
            )
        }

    old_tier = integration.tier

    if old_tier == new_tier:
        return {
            "error": (
                f"Service {service_name.value} is already on the "
                f"{new_tier.value} tier."
            )
        }

    # Look up service base URL.
    catalog = SERVICE_CATALOG.get(service_name)
    if catalog is None:
        return {"error": f"Unknown service: {service_name.value}"}

    # Call the external upgrade API.
    api_response = await _call_upgrade_api(
        base_url=catalog["base_url"],
        api_key=integration.api_key,
        new_tier=new_tier.value,
    )

    if "error" in api_response:
        return api_response

    # Update the local record only after successful external call.
    integration.tier = new_tier
    await db.flush()
    await db.refresh(integration)

    logger.info(
        "Upgraded user %s in %s from %s to %s",
        user_id,
        service_name.value,
        old_tier.value,
        new_tier.value,
    )

    return {
        "success": True,
        "service_name": service_name.value,
        "old_tier": old_tier.value,
        "new_tier": new_tier.value,
    }


def get_bundled_services(plan: str) -> dict[ServiceName, ServiceTier]:
    """Return the services included with a platform subscription plan.

    Looks up the plan name in ``PLATFORM_BUNDLES`` and returns the mapping
    of service names to their included tier. An unknown plan name returns
    an empty dict (equivalent to the free plan).

    **For Developers:**
        Use this to display "Included with your plan" badges on service
        cards, or to determine whether a user needs to pay extra for a
        service.

    **For QA Engineers:**
        - ``"free"`` returns an empty dict (no bundled services).
        - ``"starter"`` returns 2 services (trendscout + contentforge) at
          the free tier.
        - ``"growth"`` returns all 8 services at the free tier.
        - ``"pro"`` returns all 8 services at the pro tier.
        - An unrecognised plan name returns an empty dict.

    Args:
        plan: The platform plan tier name (e.g. ``"free"``, ``"starter"``,
            ``"growth"``, ``"pro"``).

    Returns:
        A dict mapping ``ServiceName`` to ``ServiceTier`` for the services
        included in the plan.
    """
    return dict(PLATFORM_BUNDLES.get(plan, {}))


async def auto_provision_bundled_services(
    db: AsyncSession,
    user: User,
) -> list[ProvisionResult]:
    """Provision or upgrade all services included in the user's platform plan.

    Called when a user upgrades their platform subscription. For each service
    bundled with the plan:

    - If the user has no active integration, provisions a new one at the
      bundled tier.
    - If the user has an active integration at a lower tier, upgrades it
      to the bundled tier.
    - If the user's existing tier is equal to or higher than the bundled
      tier, skips it (no downgrade).

    **For Developers:**
        This function calls ``provision_service`` or ``upgrade_service``
        for each bundled service. Errors in individual services do not
        abort the entire operation -- partial success is possible.

    **For QA Engineers:**
        - A user on the ``"free"`` plan gets no auto-provisioning (empty
          results list).
        - A user upgrading from ``"starter"`` to ``"growth"`` gets the 6
          new services provisioned and the 2 existing ones left unchanged
          (already at free tier).
        - A user upgrading from ``"growth"`` to ``"pro"`` gets all 8
          services upgraded from free to pro tier.
        - If an external service is down, that service is skipped with
          an error result; others succeed normally.

    Args:
        db: Async database session.
        user: The authenticated platform user (must have ``plan`` set).

    Returns:
        A list of ``ProvisionResult`` for each bundled service (empty if
        the plan has no bundled services).
    """
    plan_name = user.plan.value if isinstance(user.plan, PlanTier) else str(user.plan)
    bundled = get_bundled_services(plan_name)

    if not bundled:
        return []

    # Fetch existing active integrations for this user in a single query.
    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user.id,
            ServiceIntegration.is_active.is_(True),
        )
    )
    existing_integrations = {
        integ.service_name: integ for integ in result.scalars().all()
    }

    results: list[ProvisionResult] = []

    for svc_name, target_tier in bundled.items():
        existing = existing_integrations.get(svc_name)

        if existing is not None:
            # Service already connected -- check if upgrade is needed.
            if _tier_gte(existing.tier, target_tier):
                # Already at or above bundled tier -- skip.
                results.append(
                    ProvisionResult(
                        success=True,
                        service_name=svc_name,
                        service_user_id=existing.service_user_id,
                        integration_id=existing.id,
                        tier=existing.tier,
                        error=None,
                    )
                )
                continue

            # Need to upgrade to the bundled tier.
            upgrade_result = await upgrade_service(
                db, user.id, svc_name, target_tier
            )
            if "error" in upgrade_result:
                results.append(
                    ProvisionResult(
                        success=False,
                        service_name=svc_name,
                        service_user_id=existing.service_user_id,
                        integration_id=existing.id,
                        tier=existing.tier,
                        error=upgrade_result["error"],
                    )
                )
            else:
                results.append(
                    ProvisionResult(
                        success=True,
                        service_name=svc_name,
                        service_user_id=existing.service_user_id,
                        integration_id=existing.id,
                        tier=target_tier,
                        error=None,
                    )
                )
        else:
            # Not yet connected -- provision at the bundled tier.
            provision_result = await provision_service(
                db, user, svc_name, tier=target_tier
            )
            results.append(provision_result)

    logger.info(
        "Auto-provisioned bundled services for user %s (plan=%s): %d/%d succeeded",
        user.id,
        plan_name,
        sum(1 for r in results if r.success),
        len(results),
    )

    return results


async def get_usage_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UsageSummary:
    """Aggregate usage data across all connected services for a user.

    Queries all active integrations, then calls each service's usage
    endpoint to build a real-time summary. Results are combined into a
    single ``UsageSummary`` suitable for the dashboard overview page.

    **For Developers:**
        For each connected service, usage is fetched live via
        ``_call_usage_api``. If a service is unreachable, the entry
        will have ``metrics: {}`` (graceful degradation).

    **For QA Engineers:**
        - ``total_available`` is always 8.
        - ``total_connected`` counts only active integrations.
        - A user with no integrations gets ``total_connected: 0`` and
          an empty ``services`` list.
        - ``last_updated`` is set to the current time if any usage was
          fetched successfully, or None if no integrations exist.

    Args:
        db: Async database session.
        user_id: The UUID of the user.

    Returns:
        A ``UsageSummary`` dataclass with aggregated usage data.
    """
    # Fetch active integrations.
    result = await db.execute(
        select(ServiceIntegration).where(
            ServiceIntegration.user_id == user_id,
            ServiceIntegration.is_active.is_(True),
        )
    )
    integrations = result.scalars().all()

    services: list[dict[str, Any]] = []
    any_success = False

    for integ in integrations:
        catalog = SERVICE_CATALOG.get(integ.service_name, {})

        # Attempt to fetch live usage from the external service.
        metrics: dict[str, Any] = {}
        if catalog:
            usage_data = await _call_usage_api(
                base_url=catalog.get("base_url", ""),
                api_key=integ.api_key,
            )
            if "error" not in usage_data:
                metrics = usage_data
                any_success = True

        services.append({
            "service_name": integ.service_name.value,
            "display_name": catalog.get("display_name", integ.service_name.value),
            "icon": catalog.get("icon", ""),
            "color": catalog.get("color", ""),
            "tier": integ.tier.value,
            "integration_id": str(integ.id),
            "provisioned_at": integ.provisioned_at.isoformat(),
            "metrics": metrics,
        })

    return UsageSummary(
        total_connected=len(integrations),
        total_available=len(ServiceName),
        services=services,
        last_updated=datetime.now(timezone.utc) if any_success else None,
    )
