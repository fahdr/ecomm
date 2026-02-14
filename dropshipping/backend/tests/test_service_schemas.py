"""Comprehensive tests for service integration Pydantic schemas.

Tests cover all schema classes in ``app.schemas.services``, validating
correct construction, serialisation, field constraints, default values,
enum validation, forward reference resolution, and error handling.

**For QA Engineers:**
    Each test is independent and covers a specific schema or validation
    rule. Tests are grouped by schema class. Run with:
    ``pytest tests/test_service_schemas.py -v``

**For Developers:**
    These are pure unit tests — no database or HTTP client required.
    They validate Pydantic model behaviour only.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.service_integration import ServiceName, ServiceTier
from app.schemas.services import (
    BundledServiceInfo,
    DisconnectServiceResponse,
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


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

ALL_SERVICE_NAMES = [
    ServiceName.trendscout,
    ServiceName.contentforge,
    ServiceName.rankpilot,
    ServiceName.flowsend,
    ServiceName.spydrop,
    ServiceName.postpilot,
    ServiceName.adscale,
    ServiceName.shopchat,
]

ALL_SERVICE_TIERS = [
    ServiceTier.free,
    ServiceTier.starter,
    ServiceTier.growth,
    ServiceTier.pro,
]


def _make_tier_info(**overrides) -> ServiceTierInfo:
    """Build a ServiceTierInfo with sensible defaults.

    Args:
        **overrides: Fields to override on the default tier info.

    Returns:
        A valid ServiceTierInfo instance.
    """
    defaults = {
        "tier": ServiceTier.free,
        "name": "Free",
        "price_monthly_cents": 0,
        "features": ["Basic access", "Community support"],
    }
    defaults.update(overrides)
    return ServiceTierInfo(**defaults)


def _make_service_info(**overrides) -> ServiceInfo:
    """Build a ServiceInfo with sensible defaults.

    Args:
        **overrides: Fields to override on the default service info.

    Returns:
        A valid ServiceInfo instance.
    """
    defaults = {
        "name": ServiceName.trendscout,
        "display_name": "TrendScout",
        "tagline": "AI-Powered Product Research",
        "description": "Find winning dropshipping products with AI-driven market analysis.",
        "icon": "search",
        "color": "#4F46E5",
        "dashboard_url": "http://localhost:3101",
        "landing_url": "http://localhost:3201",
        "tiers": [_make_tier_info()],
    }
    defaults.update(overrides)
    return ServiceInfo(**defaults)


def _make_usage(**overrides) -> ServiceUsageResponse:
    """Build a ServiceUsageResponse with sensible defaults.

    Args:
        **overrides: Fields to override on the default usage response.

    Returns:
        A valid ServiceUsageResponse instance.
    """
    defaults = {
        "service_name": ServiceName.trendscout,
        "tier": ServiceTier.free,
        "period_start": date(2026, 2, 1),
        "period_end": date(2026, 2, 28),
        "metrics": {"products_researched": 42, "reports_generated": 5},
        "fetched_at": datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return ServiceUsageResponse(**defaults)


# ===========================================================================
# ServiceName enum tests
# ===========================================================================


class TestServiceNameEnum:
    """Tests for the ServiceName string enum."""

    def test_has_exactly_eight_members(self):
        """ServiceName should contain exactly 8 service identifiers."""
        assert len(ServiceName) == 8

    def test_all_expected_values(self):
        """Every expected service name should be a valid enum member."""
        expected = {
            "trendscout", "contentforge", "rankpilot", "flowsend",
            "spydrop", "postpilot", "adscale", "shopchat",
        }
        assert {s.value for s in ServiceName} == expected

    def test_string_coercion(self):
        """ServiceName members should be usable as plain strings."""
        assert str(ServiceName.trendscout) == "ServiceName.trendscout"
        assert ServiceName.trendscout.value == "trendscout"
        assert ServiceName("trendscout") == ServiceName.trendscout

    def test_invalid_name_raises(self):
        """An invalid service name string should raise ValueError."""
        with pytest.raises(ValueError):
            ServiceName("nonexistent_service")


# ===========================================================================
# ServiceTier enum tests
# ===========================================================================


class TestServiceTierEnum:
    """Tests for the ServiceTier string enum."""

    def test_has_exactly_four_members(self):
        """ServiceTier should contain exactly 4 pricing tiers."""
        assert len(ServiceTier) == 4

    def test_all_expected_values(self):
        """Every expected tier should be a valid enum member."""
        expected = {"free", "starter", "growth", "pro"}
        assert {t.value for t in ServiceTier} == expected

    def test_invalid_tier_raises(self):
        """An invalid tier string should raise ValueError."""
        with pytest.raises(ValueError):
            ServiceTier("enterprise")


# ===========================================================================
# ServiceTierInfo tests
# ===========================================================================


class TestServiceTierInfo:
    """Tests for the ServiceTierInfo schema."""

    def test_valid_construction(self):
        """A valid ServiceTierInfo should construct without errors."""
        tier_info = _make_tier_info()
        assert tier_info.tier == ServiceTier.free
        assert tier_info.name == "Free"
        assert tier_info.price_monthly_cents == 0
        assert tier_info.features == ["Basic access", "Community support"]

    def test_all_tiers_accepted(self):
        """Every ServiceTier value should be accepted."""
        for tier in ALL_SERVICE_TIERS:
            info = _make_tier_info(tier=tier, name=tier.value.capitalize())
            assert info.tier == tier

    def test_negative_price_rejected(self):
        """Negative price_monthly_cents should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            _make_tier_info(price_monthly_cents=-100)
        assert "price_monthly_cents" in str(exc_info.value)

    def test_empty_name_rejected(self):
        """An empty name string should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            _make_tier_info(name="")
        assert "name" in str(exc_info.value)

    def test_empty_features_list_allowed(self):
        """An empty features list should be valid (some tiers may list no features)."""
        info = _make_tier_info(features=[])
        assert info.features == []

    def test_default_features_is_empty_list(self):
        """When features is not provided, it should default to an empty list."""
        info = ServiceTierInfo(
            tier=ServiceTier.free, name="Free", price_monthly_cents=0
        )
        assert info.features == []

    def test_serialisation_roundtrip(self):
        """model_dump -> model_validate should produce an identical object."""
        original = _make_tier_info(
            tier=ServiceTier.pro,
            name="Pro",
            price_monthly_cents=4900,
            features=["Unlimited access", "Priority support", "Custom reports"],
        )
        dumped = original.model_dump()
        restored = ServiceTierInfo.model_validate(dumped)
        assert restored == original


# ===========================================================================
# ServiceInfo tests
# ===========================================================================


class TestServiceInfo:
    """Tests for the ServiceInfo schema."""

    def test_valid_construction(self):
        """A valid ServiceInfo should construct without errors."""
        info = _make_service_info()
        assert info.name == ServiceName.trendscout
        assert info.display_name == "TrendScout"
        assert len(info.tiers) == 1

    def test_all_service_names_accepted(self):
        """Every ServiceName value should be accepted."""
        for svc_name in ALL_SERVICE_NAMES:
            info = _make_service_info(name=svc_name, display_name=svc_name.value)
            assert info.name == svc_name

    def test_multiple_tiers(self):
        """ServiceInfo should accept multiple tier entries."""
        tiers = [
            _make_tier_info(tier=ServiceTier.free, name="Free", price_monthly_cents=0),
            _make_tier_info(tier=ServiceTier.starter, name="Starter", price_monthly_cents=1900),
            _make_tier_info(tier=ServiceTier.pro, name="Pro", price_monthly_cents=4900),
        ]
        info = _make_service_info(tiers=tiers)
        assert len(info.tiers) == 3
        assert info.tiers[0].tier == ServiceTier.free
        assert info.tiers[2].price_monthly_cents == 4900

    def test_empty_tiers_rejected(self):
        """ServiceInfo with an empty tiers list should fail (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            _make_service_info(tiers=[])
        assert "tiers" in str(exc_info.value)

    def test_invalid_color_hex_rejected(self):
        """A non-hex color string should fail the regex pattern."""
        with pytest.raises(ValidationError) as exc_info:
            _make_service_info(color="not-a-color")
        assert "color" in str(exc_info.value)

    def test_shorthand_hex_color_accepted(self):
        """A 3-digit shorthand hex color should be accepted."""
        info = _make_service_info(color="#FFF")
        assert info.color == "#FFF"

    def test_eight_digit_hex_color_accepted(self):
        """An 8-digit hex color with alpha should be accepted."""
        info = _make_service_info(color="#4F46E5FF")
        assert info.color == "#4F46E5FF"

    def test_empty_display_name_rejected(self):
        """An empty display_name should fail validation."""
        with pytest.raises(ValidationError):
            _make_service_info(display_name="")

    def test_empty_tagline_rejected(self):
        """An empty tagline should fail validation."""
        with pytest.raises(ValidationError):
            _make_service_info(tagline="")

    def test_empty_description_rejected(self):
        """An empty description should fail validation."""
        with pytest.raises(ValidationError):
            _make_service_info(description="")

    def test_invalid_service_name_rejected(self):
        """An invalid service name string should fail validation."""
        with pytest.raises(ValidationError):
            _make_service_info(name="invalid_service")

    def test_serialisation_roundtrip(self):
        """model_dump -> model_validate should produce an identical object."""
        original = _make_service_info()
        dumped = original.model_dump()
        restored = ServiceInfo.model_validate(dumped)
        assert restored == original

    def test_json_roundtrip(self):
        """model_dump_json -> model_validate_json should produce an identical object."""
        original = _make_service_info()
        json_str = original.model_dump_json()
        restored = ServiceInfo.model_validate_json(json_str)
        assert restored == original


# ===========================================================================
# ServiceStatus tests
# ===========================================================================


class TestServiceStatus:
    """Tests for the ServiceStatus schema."""

    def test_disconnected_defaults(self):
        """A disconnected service should have sensible defaults."""
        status = ServiceStatus(service=_make_service_info())
        assert status.is_connected is False
        assert status.integration_id is None
        assert status.current_tier is None
        assert status.is_active is False
        assert status.provisioned_at is None
        assert status.usage is None

    def test_connected_service(self):
        """A connected service should have integration details populated."""
        now = datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc)
        integration_id = uuid.uuid4()
        status = ServiceStatus(
            service=_make_service_info(),
            is_connected=True,
            integration_id=integration_id,
            current_tier=ServiceTier.starter,
            is_active=True,
            provisioned_at=now,
            usage=_make_usage(),
        )
        assert status.is_connected is True
        assert status.integration_id == integration_id
        assert status.current_tier == ServiceTier.starter
        assert status.is_active is True
        assert status.provisioned_at == now
        assert status.usage is not None
        assert status.usage.metrics["products_researched"] == 42

    def test_connected_without_usage(self):
        """A connected service may not yet have usage data fetched."""
        status = ServiceStatus(
            service=_make_service_info(),
            is_connected=True,
            integration_id=uuid.uuid4(),
            current_tier=ServiceTier.free,
            is_active=True,
            usage=None,
        )
        assert status.is_connected is True
        assert status.usage is None

    def test_forward_reference_resolved(self):
        """ServiceStatus should accept ServiceUsageResponse via forward reference."""
        usage = _make_usage()
        status = ServiceStatus(
            service=_make_service_info(),
            is_connected=True,
            integration_id=uuid.uuid4(),
            current_tier=ServiceTier.free,
            is_active=True,
            usage=usage,
        )
        assert status.usage.service_name == ServiceName.trendscout

    def test_serialisation_roundtrip(self):
        """model_dump -> model_validate should produce an identical object."""
        status = ServiceStatus(
            service=_make_service_info(),
            is_connected=True,
            integration_id=uuid.uuid4(),
            current_tier=ServiceTier.growth,
            is_active=True,
            provisioned_at=datetime(2026, 1, 15, 8, 30, 0, tzinfo=timezone.utc),
            usage=_make_usage(),
        )
        dumped = status.model_dump()
        restored = ServiceStatus.model_validate(dumped)
        assert restored == status


# ===========================================================================
# ProvisionServiceRequest tests
# ===========================================================================


class TestProvisionServiceRequest:
    """Tests for the ProvisionServiceRequest schema."""

    def test_minimal_request(self):
        """Only service_name is required; other fields should default."""
        req = ProvisionServiceRequest(service_name=ServiceName.contentforge)
        assert req.service_name == ServiceName.contentforge
        assert req.store_id is None
        assert req.tier == ServiceTier.free

    def test_full_request(self):
        """All fields should be accepted when provided."""
        store_id = uuid.uuid4()
        req = ProvisionServiceRequest(
            service_name=ServiceName.adscale,
            store_id=store_id,
            tier=ServiceTier.growth,
        )
        assert req.service_name == ServiceName.adscale
        assert req.store_id == store_id
        assert req.tier == ServiceTier.growth

    def test_all_services_accepted(self):
        """Every service name should be accepted in a provision request."""
        for svc in ALL_SERVICE_NAMES:
            req = ProvisionServiceRequest(service_name=svc)
            assert req.service_name == svc

    def test_all_tiers_accepted(self):
        """Every tier should be accepted in a provision request."""
        for tier in ALL_SERVICE_TIERS:
            req = ProvisionServiceRequest(
                service_name=ServiceName.trendscout, tier=tier
            )
            assert req.tier == tier

    def test_invalid_service_name_rejected(self):
        """An invalid service_name should fail validation."""
        with pytest.raises(ValidationError):
            ProvisionServiceRequest(service_name="nonexistent")

    def test_invalid_tier_rejected(self):
        """An invalid tier should fail validation."""
        with pytest.raises(ValidationError):
            ProvisionServiceRequest(
                service_name=ServiceName.trendscout, tier="enterprise"
            )

    def test_missing_service_name_rejected(self):
        """Omitting service_name entirely should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProvisionServiceRequest()
        assert "service_name" in str(exc_info.value)


# ===========================================================================
# ProvisionServiceResponse tests
# ===========================================================================


class TestProvisionServiceResponse:
    """Tests for the ProvisionServiceResponse schema."""

    def test_valid_construction(self):
        """A fully populated response should construct without errors."""
        now = datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc)
        integration_id = uuid.uuid4()
        resp = ProvisionServiceResponse(
            integration_id=integration_id,
            service_name=ServiceName.shopchat,
            service_user_id="svc_user_abc123",
            tier=ServiceTier.free,
            dashboard_url="http://localhost:3108/dashboard?token=xyz",
            provisioned_at=now,
        )
        assert resp.integration_id == integration_id
        assert resp.service_name == ServiceName.shopchat
        assert resp.service_user_id == "svc_user_abc123"
        assert resp.tier == ServiceTier.free
        assert "3108" in resp.dashboard_url
        assert resp.provisioned_at == now

    def test_empty_service_user_id_rejected(self):
        """An empty service_user_id should fail validation (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ProvisionServiceResponse(
                integration_id=uuid.uuid4(),
                service_name=ServiceName.trendscout,
                service_user_id="",
                tier=ServiceTier.free,
                dashboard_url="http://localhost:3101",
                provisioned_at=datetime.now(timezone.utc),
            )
        assert "service_user_id" in str(exc_info.value)

    def test_empty_dashboard_url_rejected(self):
        """An empty dashboard_url should fail validation (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            ProvisionServiceResponse(
                integration_id=uuid.uuid4(),
                service_name=ServiceName.trendscout,
                service_user_id="usr_123",
                tier=ServiceTier.free,
                dashboard_url="",
                provisioned_at=datetime.now(timezone.utc),
            )
        assert "dashboard_url" in str(exc_info.value)

    def test_has_from_attributes_config(self):
        """ProvisionServiceResponse should have from_attributes for ORM compat."""
        assert ProvisionServiceResponse.model_config.get("from_attributes") is True


# ===========================================================================
# ServiceUsageResponse tests
# ===========================================================================


class TestServiceUsageResponse:
    """Tests for the ServiceUsageResponse schema."""

    def test_valid_construction(self):
        """A valid usage response should construct without errors."""
        usage = _make_usage()
        assert usage.service_name == ServiceName.trendscout
        assert usage.tier == ServiceTier.free
        assert usage.period_start == date(2026, 2, 1)
        assert usage.period_end == date(2026, 2, 28)
        assert usage.metrics["products_researched"] == 42
        assert usage.metrics["reports_generated"] == 5

    def test_empty_metrics_allowed(self):
        """An empty metrics dict should be valid (service may report nothing yet)."""
        usage = _make_usage(metrics={})
        assert usage.metrics == {}

    def test_default_metrics_is_empty_dict(self):
        """When metrics is not provided, it should default to empty dict."""
        usage = ServiceUsageResponse(
            service_name=ServiceName.trendscout,
            tier=ServiceTier.free,
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
            fetched_at=datetime.now(timezone.utc),
        )
        assert usage.metrics == {}

    def test_complex_metrics_accepted(self):
        """Metrics should accept nested structures (dict values are Any)."""
        complex_metrics = {
            "emails_sent": 1500,
            "open_rate": 0.342,
            "top_campaigns": ["Welcome", "Abandoned Cart"],
            "breakdown": {"automated": 800, "manual": 700},
        }
        usage = _make_usage(
            service_name=ServiceName.flowsend,
            metrics=complex_metrics,
        )
        assert usage.metrics["top_campaigns"] == ["Welcome", "Abandoned Cart"]
        assert usage.metrics["breakdown"]["automated"] == 800

    def test_all_services_in_usage(self):
        """Every service name should be valid in a usage response."""
        for svc in ALL_SERVICE_NAMES:
            usage = _make_usage(service_name=svc)
            assert usage.service_name == svc

    def test_serialisation_roundtrip(self):
        """model_dump -> model_validate should produce an identical object."""
        original = _make_usage()
        dumped = original.model_dump()
        restored = ServiceUsageResponse.model_validate(dumped)
        assert restored == original


# ===========================================================================
# ServiceUsageSummary tests
# ===========================================================================


class TestServiceUsageSummary:
    """Tests for the ServiceUsageSummary schema."""

    def test_valid_construction(self):
        """A valid summary should construct without errors."""
        summary = ServiceUsageSummary(
            services=[_make_usage()],
            total_monthly_cost_cents=2900,
            bundle_savings_cents=500,
        )
        assert len(summary.services) == 1
        assert summary.total_monthly_cost_cents == 2900
        assert summary.bundle_savings_cents == 500

    def test_empty_services_list(self):
        """A user with no connected services should have an empty list."""
        summary = ServiceUsageSummary(
            services=[],
            total_monthly_cost_cents=0,
            bundle_savings_cents=0,
        )
        assert summary.services == []

    def test_multiple_services(self):
        """Summary should accept usage from multiple services."""
        usages = [
            _make_usage(service_name=ServiceName.trendscout),
            _make_usage(service_name=ServiceName.contentforge),
            _make_usage(service_name=ServiceName.rankpilot),
        ]
        summary = ServiceUsageSummary(
            services=usages,
            total_monthly_cost_cents=5700,
            bundle_savings_cents=2100,
        )
        assert len(summary.services) == 3
        service_names = {s.service_name for s in summary.services}
        assert ServiceName.trendscout in service_names
        assert ServiceName.contentforge in service_names
        assert ServiceName.rankpilot in service_names

    def test_negative_cost_rejected(self):
        """Negative total_monthly_cost_cents should fail validation (ge=0)."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUsageSummary(
                services=[],
                total_monthly_cost_cents=-100,
                bundle_savings_cents=0,
            )
        assert "total_monthly_cost_cents" in str(exc_info.value)

    def test_negative_savings_rejected(self):
        """Negative bundle_savings_cents should fail validation (ge=0)."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUsageSummary(
                services=[],
                total_monthly_cost_cents=0,
                bundle_savings_cents=-50,
            )
        assert "bundle_savings_cents" in str(exc_info.value)

    def test_default_services_is_empty_list(self):
        """When services is not provided, it should default to empty list."""
        summary = ServiceUsageSummary(
            total_monthly_cost_cents=0,
            bundle_savings_cents=0,
        )
        assert summary.services == []


# ===========================================================================
# UpgradeServiceRequest tests
# ===========================================================================


class TestUpgradeServiceRequest:
    """Tests for the UpgradeServiceRequest schema."""

    def test_valid_construction(self):
        """A valid upgrade request should construct without errors."""
        req = UpgradeServiceRequest(tier=ServiceTier.growth)
        assert req.tier == ServiceTier.growth

    def test_all_tiers_accepted(self):
        """Every ServiceTier should be accepted as an upgrade target."""
        for tier in ALL_SERVICE_TIERS:
            req = UpgradeServiceRequest(tier=tier)
            assert req.tier == tier

    def test_invalid_tier_rejected(self):
        """An invalid tier value should fail validation."""
        with pytest.raises(ValidationError):
            UpgradeServiceRequest(tier="enterprise")

    def test_missing_tier_rejected(self):
        """Omitting tier should fail validation (it's required)."""
        with pytest.raises(ValidationError) as exc_info:
            UpgradeServiceRequest()
        assert "tier" in str(exc_info.value)


# ===========================================================================
# DisconnectServiceResponse tests
# ===========================================================================


class TestDisconnectServiceResponse:
    """Tests for the DisconnectServiceResponse schema."""

    def test_valid_construction(self):
        """A valid disconnect response should construct without errors."""
        resp = DisconnectServiceResponse(
            service_name=ServiceName.spydrop,
            message="SpyDrop has been disconnected from your account.",
        )
        assert resp.service_name == ServiceName.spydrop
        assert "disconnected" in resp.message

    def test_all_services_accepted(self):
        """Every service name should be valid in a disconnect response."""
        for svc in ALL_SERVICE_NAMES:
            resp = DisconnectServiceResponse(
                service_name=svc,
                message=f"{svc.value} disconnected.",
            )
            assert resp.service_name == svc

    def test_empty_message_rejected(self):
        """An empty message should fail validation (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            DisconnectServiceResponse(
                service_name=ServiceName.trendscout,
                message="",
            )
        assert "message" in str(exc_info.value)


# ===========================================================================
# BundledServiceInfo tests
# ===========================================================================


class TestBundledServiceInfo:
    """Tests for the BundledServiceInfo schema."""

    def test_valid_construction(self):
        """A valid bundled service info should construct without errors."""
        info = BundledServiceInfo(
            service_name=ServiceName.trendscout,
            included_tier=ServiceTier.free,
            can_upgrade=True,
        )
        assert info.service_name == ServiceName.trendscout
        assert info.included_tier == ServiceTier.free
        assert info.can_upgrade is True

    def test_can_upgrade_defaults_true(self):
        """can_upgrade should default to True when not provided."""
        info = BundledServiceInfo(
            service_name=ServiceName.contentforge,
            included_tier=ServiceTier.starter,
        )
        assert info.can_upgrade is True

    def test_pro_tier_no_upgrade(self):
        """Pro tier should accept can_upgrade=False (no higher tier exists)."""
        info = BundledServiceInfo(
            service_name=ServiceName.adscale,
            included_tier=ServiceTier.pro,
            can_upgrade=False,
        )
        assert info.can_upgrade is False

    def test_all_services_accepted(self):
        """Every service name should be valid in bundle info."""
        for svc in ALL_SERVICE_NAMES:
            info = BundledServiceInfo(
                service_name=svc,
                included_tier=ServiceTier.free,
            )
            assert info.service_name == svc


# ===========================================================================
# PlatformBundleInfo tests
# ===========================================================================


class TestPlatformBundleInfo:
    """Tests for the PlatformBundleInfo schema."""

    def test_free_plan_no_services(self):
        """Free plan should have an empty included_services list."""
        bundle = PlatformBundleInfo(plan="free", included_services=[])
        assert bundle.plan == "free"
        assert bundle.included_services == []

    def test_starter_plan(self):
        """Starter plan should include TrendScout and ContentForge."""
        bundle = PlatformBundleInfo(
            plan="starter",
            included_services=[
                BundledServiceInfo(
                    service_name=ServiceName.trendscout,
                    included_tier=ServiceTier.free,
                ),
                BundledServiceInfo(
                    service_name=ServiceName.contentforge,
                    included_tier=ServiceTier.free,
                ),
            ],
        )
        assert bundle.plan == "starter"
        assert len(bundle.included_services) == 2

    def test_growth_plan_all_eight(self):
        """Growth plan should include all 8 services at free tier."""
        services = [
            BundledServiceInfo(
                service_name=svc,
                included_tier=ServiceTier.free,
            )
            for svc in ALL_SERVICE_NAMES
        ]
        bundle = PlatformBundleInfo(plan="growth", included_services=services)
        assert bundle.plan == "growth"
        assert len(bundle.included_services) == 8

    def test_pro_plan_all_eight_pro_tier(self):
        """Pro plan should include all 8 services at pro tier."""
        services = [
            BundledServiceInfo(
                service_name=svc,
                included_tier=ServiceTier.pro,
                can_upgrade=False,
            )
            for svc in ALL_SERVICE_NAMES
        ]
        bundle = PlatformBundleInfo(plan="pro", included_services=services)
        assert bundle.plan == "pro"
        assert len(bundle.included_services) == 8
        for svc in bundle.included_services:
            assert svc.included_tier == ServiceTier.pro
            assert svc.can_upgrade is False

    def test_invalid_plan_rejected(self):
        """An invalid plan name should fail the regex pattern."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformBundleInfo(plan="enterprise", included_services=[])
        assert "plan" in str(exc_info.value)

    def test_all_valid_plan_names(self):
        """All four plan names should be accepted by the pattern."""
        for plan in ("free", "starter", "growth", "pro"):
            bundle = PlatformBundleInfo(plan=plan, included_services=[])
            assert bundle.plan == plan

    def test_default_included_services_is_empty(self):
        """When included_services is not provided, it should default to empty list."""
        bundle = PlatformBundleInfo(plan="free")
        assert bundle.included_services == []

    def test_serialisation_roundtrip(self):
        """model_dump -> model_validate should produce an identical object."""
        original = PlatformBundleInfo(
            plan="growth",
            included_services=[
                BundledServiceInfo(
                    service_name=ServiceName.trendscout,
                    included_tier=ServiceTier.free,
                    can_upgrade=True,
                ),
            ],
        )
        dumped = original.model_dump()
        restored = PlatformBundleInfo.model_validate(dumped)
        assert restored == original


# ===========================================================================
# Cross-schema integration tests
# ===========================================================================


class TestCrossSchemaIntegration:
    """Tests that validate interaction between multiple schema types."""

    def test_full_service_catalog_entry(self):
        """Build a complete service status with all nested schemas."""
        tier_free = _make_tier_info(
            tier=ServiceTier.free, name="Free", price_monthly_cents=0,
            features=["5 product lookups/day"],
        )
        tier_pro = _make_tier_info(
            tier=ServiceTier.pro, name="Pro", price_monthly_cents=4900,
            features=["Unlimited lookups", "API access", "Priority support"],
        )
        info = _make_service_info(
            name=ServiceName.trendscout,
            display_name="TrendScout",
            tiers=[tier_free, tier_pro],
        )
        usage = _make_usage(
            service_name=ServiceName.trendscout,
            tier=ServiceTier.pro,
            metrics={"products_researched": 1200, "winning_products_found": 45},
        )
        status = ServiceStatus(
            service=info,
            is_connected=True,
            integration_id=uuid.uuid4(),
            current_tier=ServiceTier.pro,
            is_active=True,
            provisioned_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            usage=usage,
        )

        # Verify the full object graph
        assert status.service.name == ServiceName.trendscout
        assert len(status.service.tiers) == 2
        assert status.service.tiers[1].price_monthly_cents == 4900
        assert status.usage.metrics["winning_products_found"] == 45
        assert status.current_tier == ServiceTier.pro

    def test_full_usage_summary_with_all_services(self):
        """Build a usage summary spanning all 8 services."""
        usages = []
        for svc in ALL_SERVICE_NAMES:
            usages.append(_make_usage(
                service_name=svc,
                tier=ServiceTier.free,
                metrics={"api_calls": 100},
            ))
        summary = ServiceUsageSummary(
            services=usages,
            total_monthly_cost_cents=0,
            bundle_savings_cents=15000,
        )
        assert len(summary.services) == 8
        assert summary.bundle_savings_cents == 15000
        svc_names = {s.service_name for s in summary.services}
        assert svc_names == set(ALL_SERVICE_NAMES)

    def test_provision_to_status_flow(self):
        """Simulate the flow from provision request to service status."""
        # Step 1: User sends provision request
        req = ProvisionServiceRequest(
            service_name=ServiceName.postpilot,
            tier=ServiceTier.starter,
        )
        assert req.service_name == ServiceName.postpilot

        # Step 2: Backend returns provision response
        integration_id = uuid.uuid4()
        now = datetime(2026, 2, 12, 10, 0, 0, tzinfo=timezone.utc)
        resp = ProvisionServiceResponse(
            integration_id=integration_id,
            service_name=req.service_name,
            service_user_id="pp_usr_12345",
            tier=req.tier,
            dashboard_url="http://localhost:3106/dashboard",
            provisioned_at=now,
        )
        assert resp.integration_id == integration_id

        # Step 3: Service appears as connected in the catalog
        status = ServiceStatus(
            service=_make_service_info(name=ServiceName.postpilot, display_name="PostPilot"),
            is_connected=True,
            integration_id=resp.integration_id,
            current_tier=resp.tier,
            is_active=True,
            provisioned_at=resp.provisioned_at,
        )
        assert status.is_connected is True
        assert status.current_tier == ServiceTier.starter

    def test_upgrade_flow(self):
        """Simulate the upgrade request flow."""
        # User requests upgrade
        upgrade_req = UpgradeServiceRequest(tier=ServiceTier.pro)
        assert upgrade_req.tier == ServiceTier.pro

        # After upgrade, status reflects new tier
        status = ServiceStatus(
            service=_make_service_info(),
            is_connected=True,
            integration_id=uuid.uuid4(),
            current_tier=upgrade_req.tier,
            is_active=True,
            provisioned_at=datetime.now(timezone.utc),
        )
        assert status.current_tier == ServiceTier.pro

    def test_disconnect_flow(self):
        """Simulate the disconnect response and verify status reset."""
        disconnect_resp = DisconnectServiceResponse(
            service_name=ServiceName.rankpilot,
            message="RankPilot has been disconnected. Your data will be retained for 30 days.",
        )
        assert disconnect_resp.service_name == ServiceName.rankpilot

        # After disconnect, status should show as not connected
        status = ServiceStatus(
            service=_make_service_info(name=ServiceName.rankpilot, display_name="RankPilot"),
            is_connected=False,
        )
        assert status.is_connected is False
        assert status.integration_id is None
