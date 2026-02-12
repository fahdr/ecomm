"""Service integration request and response schemas.

Defines data structures for managing connections between the dropshipping
platform and external SaaS microservices (TrendScout, ContentForge, etc.).

**For Developers:**
    All schemas use Pydantic v2 with ``from_attributes`` for ORM compatibility.
    ``ServiceName`` and ``ServiceTier`` enums are imported from
    ``app.models.service_integration``. Forward references are used where
    needed (e.g. ``ServiceUsageResponse`` referenced before definition) and
    resolved via ``model_rebuild()`` at module end.

**For QA Engineers:**
    Validate that all 8 service names are accepted, tier values are correct,
    and usage metrics return proper JSON structures. ``ServiceStatus`` is
    the main schema for the service catalog listing endpoint; it nests
    ``ServiceInfo``, ``ServiceTierInfo``, and optionally ``ServiceUsageResponse``.

**For Project Managers:**
    These schemas power the "Connected Services" section of the dashboard
    where users can browse, provision, upgrade, and disconnect AI tools.

**For End Users:**
    These schemas describe the data you see when managing your connected
    AI tools from the dashboard — service details, pricing tiers, usage
    metrics, and bundle savings.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.service_integration import ServiceName, ServiceTier


# ---------------------------------------------------------------------------
# Service catalog schemas
# ---------------------------------------------------------------------------


class ServiceTierInfo(BaseModel):
    """Pricing tier details for a service.

    Represents one tier option within a service's pricing structure.
    Used inside ``ServiceInfo.tiers`` to present all available plans.

    **For Developers:**
        This is a read-only schema — tiers are defined server-side in the
        service catalog, not created by users.

    **For QA Engineers:**
        - ``tier`` must be a valid ``ServiceTier`` enum value.
        - ``price_monthly_cents`` should be non-negative (0 for free tier).
        - ``features`` is a list of human-readable feature descriptions.

    **For End Users:**
        Each tier shows its name, monthly price, and what features are
        included so you can choose the right plan for your needs.

    Attributes:
        tier: The tier identifier (free, starter, growth, pro).
        name: Human-readable tier name (e.g. "Free", "Starter").
        price_monthly_cents: Monthly price in US cents (0 for free tier).
        features: List of feature descriptions included in this tier.
    """

    tier: str = Field(..., description="Tier identifier (e.g. free, pro, enterprise)")
    name: str = Field(..., min_length=1, max_length=50, description="Display name")
    price_monthly_cents: int = Field(
        ..., ge=0, description="Monthly price in US cents"
    )
    features: list[str] = Field(
        default_factory=list, description="Feature descriptions for this tier"
    )


class ServiceInfo(BaseModel):
    """Static catalog information about a microservice.

    Contains branding, links, and pricing tiers for a single service.
    This schema is embedded inside ``ServiceStatus`` and also used
    independently for the service catalog listing.

    **For Developers:**
        ``icon`` is a string key (e.g. ``"search"``, ``"sparkles"``) that
        the dashboard maps to a Lucide icon component. ``color`` is a hex
        string used for accent branding in the UI.

    **For QA Engineers:**
        - All 8 services must appear in the catalog.
        - ``tiers`` must contain at least one entry (the free tier).
        - ``dashboard_url`` and ``landing_url`` should be valid URL formats.

    **For End Users:**
        This is the information card you see for each AI tool — its name,
        description, icon, and available pricing plans.

    Attributes:
        name: Service identifier enum value.
        display_name: Human-readable service name (e.g. "TrendScout").
        tagline: Short one-line description of the service.
        description: Longer description of what the service does.
        icon: Icon key for the dashboard UI (maps to Lucide icon).
        color: Hex color string for service branding (e.g. "#4F46E5").
        dashboard_url: URL to the service's standalone dashboard.
        landing_url: URL to the service's public landing page.
        tiers: Available pricing tiers for this service.
    """

    name: ServiceName = Field(..., description="Service identifier")
    display_name: str = Field(
        ..., min_length=1, max_length=100, description="Human-readable service name"
    )
    tagline: str = Field(
        ..., min_length=1, max_length=200, description="Short one-line description"
    )
    description: str = Field(
        ..., min_length=1, description="Full description of the service"
    )
    icon: str = Field(
        ..., min_length=1, max_length=50, description="Icon key for the dashboard"
    )
    color: str = Field(
        ...,
        min_length=4,
        max_length=9,
        pattern=r"^#[0-9a-fA-F]{3,8}$",
        description="Hex color for service branding",
    )
    dashboard_url: str = Field(
        ..., min_length=1, description="URL to the service dashboard"
    )
    landing_url: str = Field(
        ..., min_length=1, description="URL to the service landing page"
    )
    tiers: list[ServiceTierInfo] = Field(
        ..., min_length=1, description="Available pricing tiers (at least free)"
    )


class ServiceStatus(BaseModel):
    """A service's connection status for the current user.

    Combines catalog information (``ServiceInfo``) with the user's
    integration state. Returned by the service listing endpoint so the
    dashboard can show both available and connected services in one view.

    **For Developers:**
        ``is_connected`` is derived server-side by checking whether a
        ``ServiceIntegration`` record exists. ``usage`` is populated only
        when the service is connected and usage data has been fetched.

    **For QA Engineers:**
        - When ``is_connected`` is False: ``integration_id``, ``current_tier``,
          ``provisioned_at``, and ``usage`` should all be None/default.
        - When ``is_connected`` is True: ``integration_id`` and ``current_tier``
          must be populated.
        - ``is_active`` defaults to False when not connected.

    **For End Users:**
        This is the full status card for each AI tool — showing whether
        you're connected, which plan you're on, and your current usage.

    Attributes:
        service: Static catalog information for this service.
        is_connected: Whether the user has provisioned this service.
        integration_id: UUID of the integration record (None if not connected).
        current_tier: The user's current tier in this service (None if not connected).
        is_active: Whether the integration is currently active.
        provisioned_at: When the user first connected this service.
        usage: Latest usage data (None if not connected or not yet fetched).
    """

    service: ServiceInfo = Field(..., description="Service catalog information")
    is_connected: bool = Field(
        False, description="Whether the user has provisioned this service"
    )
    integration_id: uuid.UUID | None = Field(
        None, description="Integration record UUID"
    )
    current_tier: ServiceTier | None = Field(
        None, description="User's current tier in this service"
    )
    is_active: bool = Field(False, description="Whether the integration is active")
    provisioned_at: datetime | None = Field(
        None, description="When the user connected this service"
    )
    usage: ServiceUsageResponse | None = Field(
        None, description="Latest usage data for this service"
    )


# ---------------------------------------------------------------------------
# Provisioning schemas
# ---------------------------------------------------------------------------


class ProvisionServiceRequest(BaseModel):
    """Request body for provisioning a user in an external microservice.

    Sent when a user clicks "Connect" on a service card in the dashboard.
    The backend calls the service's ``POST /api/v1/auth/provision`` endpoint.

    **For Developers:**
        ``store_id`` is optional — when provided, the integration is linked
        to that specific store. ``tier`` defaults to ``free`` if not specified.

    **For QA Engineers:**
        - ``service_name`` must be one of the 8 valid ``ServiceName`` values.
        - ``store_id``, if provided, must be a UUID of an existing store.
        - ``tier`` defaults to ``free`` when omitted.
        - Provisioning the same service twice should return a 409 Conflict.

    **For End Users:**
        Choose which AI tool to connect and optionally link it to a
        specific store. You start on the free tier by default.

    Attributes:
        service_name: Which service to provision.
        store_id: Optional store to link the integration to.
        tier: Desired pricing tier (defaults to free).
    """

    service_name: ServiceName = Field(..., description="Service to provision")
    store_id: uuid.UUID | None = Field(
        None, description="Optional store to link the integration to"
    )
    tier: ServiceTier = Field(
        ServiceTier.free, description="Desired pricing tier"
    )


class ProvisionServiceResponse(BaseModel):
    """Response after successfully provisioning a user in a microservice.

    Returned immediately after the backend provisions the user in the
    external service and stores the integration record.

    **For Developers:**
        ``service_user_id`` is the ID assigned by the external service.
        ``dashboard_url`` includes any auth tokens or redirect params
        needed for SSO into the service dashboard.

    **For QA Engineers:**
        - ``integration_id`` should be a valid UUID v4.
        - ``service_user_id`` should be a non-empty string.
        - ``tier`` should match the requested tier.
        - ``provisioned_at`` should be close to the current server time.

    **For End Users:**
        After connecting, you get a direct link to the service's dashboard
        where you can start using the AI tool right away.

    Attributes:
        integration_id: UUID of the newly created integration record.
        service_name: Which service was provisioned.
        service_user_id: The user's ID within the external service.
        tier: The tier the user was provisioned at.
        dashboard_url: Direct link to the service dashboard (may include SSO token).
        provisioned_at: Timestamp of when provisioning completed.
    """

    model_config = {"from_attributes": True}

    integration_id: uuid.UUID = Field(..., description="Integration record UUID")
    service_name: ServiceName = Field(..., description="Provisioned service")
    service_user_id: str = Field(
        ..., min_length=1, description="User ID in the external service"
    )
    tier: ServiceTier = Field(..., description="Provisioned tier")
    dashboard_url: str = Field(
        ..., min_length=1, description="Direct link to the service dashboard"
    )
    provisioned_at: datetime = Field(
        ..., description="When provisioning completed"
    )


# ---------------------------------------------------------------------------
# Usage schemas
# ---------------------------------------------------------------------------


class ServiceUsageResponse(BaseModel):
    """Usage metrics for a single connected service.

    Retrieved by polling the service's ``GET /api/v1/usage`` endpoint.
    The ``metrics`` dict is flexible — each service defines its own
    metric keys (e.g. ``products_researched``, ``emails_sent``).

    **For Developers:**
        ``metrics`` is typed as ``dict[str, Any]`` to accommodate different
        metric shapes per service. The frontend should handle unknown keys
        gracefully. ``fetched_at`` indicates freshness of the cached data.

    **For QA Engineers:**
        - ``period_start`` must be before or equal to ``period_end``.
        - ``metrics`` should be a valid JSON-serialisable dict.
        - ``fetched_at`` should be recent (within the cache TTL window).
        - All ``ServiceName`` and ``ServiceTier`` values must be valid enums.

    **For End Users:**
        This shows how much you've used each AI tool during the current
        billing period, including specific metrics like items researched
        or emails sent.

    Attributes:
        service_name: Which service this usage data belongs to.
        tier: The user's current tier in this service.
        period_start: Start of the billing/usage period.
        period_end: End of the billing/usage period.
        metrics: Flexible per-service usage metrics (keys vary by service).
        fetched_at: When this usage data was last fetched from the service.
    """

    service_name: ServiceName = Field(..., description="Service identifier")
    tier: ServiceTier = Field(..., description="User's current tier")
    period_start: date = Field(..., description="Usage period start date")
    period_end: date = Field(..., description="Usage period end date")
    metrics: dict[str, Any] = Field(
        default_factory=dict, description="Per-service usage metrics"
    )
    fetched_at: datetime = Field(
        ..., description="When this data was fetched from the service"
    )


class ServiceUsageSummary(BaseModel):
    """Aggregated usage and cost summary across all connected services.

    Returned by the dashboard's "Services Overview" page to give users
    a single view of their total service spending and bundle savings.

    **For Developers:**
        ``total_monthly_cost_cents`` sums the per-service tier prices.
        ``bundle_savings_cents`` is calculated as the difference between
        buying each service individually vs. the platform bundle price.

    **For QA Engineers:**
        - ``services`` should only contain entries for connected services.
        - ``total_monthly_cost_cents`` must be non-negative.
        - ``bundle_savings_cents`` must be non-negative (0 if no bundle).
        - Total cost should equal the sum of individual service tier prices.

    **For End Users:**
        See your total monthly spend across all connected AI tools and
        how much you're saving with your platform bundle plan.

    Attributes:
        services: Usage data for each connected service.
        total_monthly_cost_cents: Total monthly cost in US cents.
        bundle_savings_cents: Savings from platform bundle vs. buying individually.
    """

    services: list[ServiceUsageResponse] = Field(
        default_factory=list, description="Usage data per connected service"
    )
    total_monthly_cost_cents: int = Field(
        ..., ge=0, description="Total monthly cost in US cents"
    )
    bundle_savings_cents: int = Field(
        ..., ge=0, description="Savings from platform bundle pricing"
    )


# ---------------------------------------------------------------------------
# Upgrade / disconnect schemas
# ---------------------------------------------------------------------------


class UpgradeServiceRequest(BaseModel):
    """Request to change a connected service's pricing tier.

    Sent when a user upgrades or downgrades their plan for a specific
    service from the dashboard.

    **For Developers:**
        The backend forwards this to the service's billing endpoint.
        Downgrades take effect at the end of the current billing period;
        upgrades are applied immediately with prorated charges.

    **For QA Engineers:**
        - ``tier`` must be a valid ``ServiceTier`` enum value.
        - Upgrading to the current tier should return a 400 error.
        - The service must be connected (provisioned) before upgrading.

    **For End Users:**
        Choose a new plan tier for your connected AI tool. Upgrades
        take effect immediately; downgrades apply at the next billing date.

    Attributes:
        tier: The desired new pricing tier.
    """

    tier: ServiceTier = Field(..., description="Desired new pricing tier")


class DisconnectServiceResponse(BaseModel):
    """Response after disconnecting (deprovisioning) a service.

    Returned when a user clicks "Disconnect" on a connected service.
    The integration record is soft-deleted (marked inactive).

    **For Developers:**
        The backend calls the service's deprovisioning endpoint (if one
        exists) and then marks the ``ServiceIntegration`` as inactive.
        The record is preserved for audit/re-connection purposes.

    **For QA Engineers:**
        - ``service_name`` should match the service that was disconnected.
        - ``message`` should be a human-readable confirmation string.
        - After disconnection, the service should appear as not connected.

    **For End Users:**
        Confirmation that the AI tool has been disconnected from your
        account. You can reconnect it later if needed.

    Attributes:
        service_name: Which service was disconnected.
        message: Human-readable confirmation message.
    """

    service_name: ServiceName = Field(..., description="Disconnected service")
    message: str = Field(
        ..., min_length=1, description="Human-readable confirmation message"
    )


# ---------------------------------------------------------------------------
# Bundle schemas
# ---------------------------------------------------------------------------


class BundledServiceInfo(BaseModel):
    """A single service included in a platform plan bundle.

    Describes which tier of a service is included with a given platform
    subscription plan, and whether the user can upgrade beyond it.

    **For Developers:**
        ``can_upgrade`` is True when higher tiers are available for
        purchase beyond what the bundle includes. The dashboard uses
        this to show or hide the upgrade button.

    **For QA Engineers:**
        - ``service_name`` must be a valid ``ServiceName`` enum value.
        - ``included_tier`` must be a valid ``ServiceTier`` enum value.
        - ``can_upgrade`` should be True for all tiers except ``pro``.

    **For End Users:**
        Shows which AI tool tier is included free with your platform
        plan and whether you can upgrade to a higher tier.

    Attributes:
        service_name: Which service is included in the bundle.
        included_tier: The tier that comes free with the platform plan.
        can_upgrade: Whether higher tiers are available for purchase.
    """

    service_name: ServiceName = Field(..., description="Bundled service identifier")
    included_tier: ServiceTier = Field(
        ..., description="Tier included free with the platform plan"
    )
    can_upgrade: bool = Field(
        True, description="Whether higher tiers are available for purchase"
    )


class PlatformBundleInfo(BaseModel):
    """Services included in a platform subscription plan bundle.

    Returned by the pricing/plans endpoint to show users what AI tools
    come included with each platform tier.

    **For Developers:**
        The ``plan`` field is a string matching ``PlanTier`` values
        (free, starter, growth, pro) rather than the enum itself, to
        keep this schema decoupled from the billing module.

    **For QA Engineers:**
        - ``plan`` must be one of: "free", "starter", "growth", "pro".
        - Free plan: ``included_services`` should be empty.
        - Starter plan: should include TrendScout + ContentForge at free tier.
        - Growth plan: should include all 8 services at free tier.
        - Pro plan: should include all 8 services at pro tier.

    **For End Users:**
        See exactly which AI tools and plan levels are included with
        your platform subscription, and how much you save versus buying
        each tool separately.

    Attributes:
        plan: Platform subscription tier name.
        included_services: List of services and tiers included in this plan.
    """

    plan: str = Field(
        ...,
        pattern=r"^(free|starter|growth|pro)$",
        description="Platform subscription tier",
    )
    included_services: list[BundledServiceInfo] = Field(
        default_factory=list,
        description="Services included in this platform plan",
    )


# ---------------------------------------------------------------------------
# Resolve forward references
# ---------------------------------------------------------------------------

# ServiceStatus references ServiceUsageResponse which is defined after it,
# so we rebuild the model to resolve the forward reference.
ServiceStatus.model_rebuild()
