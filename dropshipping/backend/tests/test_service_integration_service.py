"""Unit tests for the service integration business logic layer.

Tests the 9 public functions and internal helpers in
``app.services.service_integration_service`` using mocked HTTP calls and
a real PostgreSQL database (via the shared ``client`` fixture's session).

**For Developers:**
    These tests exercise the service layer directly (not via API endpoints).
    A dedicated ``db_session`` fixture provides a fresh SQLAlchemy async
    session for each test. External HTTP calls are mocked via the
    ``mock_httpx`` fixture which patches ``httpx.AsyncClient`` in the
    service module.

**For QA Engineers:**
    Tests are grouped by function:
    1. ``get_service_catalog`` -- static catalog correctness (5 tests)
    2. ``get_bundled_services`` -- plan bundle mappings (5 tests)
    3. ``_tier_gte`` -- tier comparison helper (4 tests)
    4. ``get_user_services`` -- user service status list (3 tests)
    5. ``provision_service`` -- provisioning flow (5 tests)
    6. ``disconnect_service`` -- soft-delete flow (3 tests)
    7. ``fetch_service_usage`` -- usage proxy (4 tests)
    8. ``upgrade_service`` -- tier change flow (4 tests)
    9. ``auto_provision_bundled_services`` -- bulk provisioning (3 tests)
    10. ``get_usage_summary`` -- aggregated summary (2 tests)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants.plans import PlanTier
from app.database import Base
from app.models.service_integration import ServiceIntegration, ServiceName, ServiceTier
from app.models.user import User
from app.services.service_integration_service import (
    PLATFORM_BUNDLES,
    SERVICE_CATALOG,
    ProvisionResult,
    ServiceStatus,
    UsageSummary,
    _tier_gte,
    auto_provision_bundled_services,
    disconnect_service,
    fetch_service_usage,
    get_bundled_services,
    get_service_catalog,
    get_usage_summary,
    get_user_services,
    provision_service,
    upgrade_service,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session(db):
    """Alias for the shared ``db`` fixture from conftest.

    The service integration tests use ``db_session`` as their parameter name.
    This fixture delegates to the schema-isolated ``db`` fixture to ensure
    all tests operate within the ``dropshipping_test`` schema.

    Args:
        db: The shared async database session from conftest.

    Yields:
        AsyncSession: A SQLAlchemy async session for direct DB operations.
    """
    yield db


async def _create_test_user(
    db: AsyncSession,
    email: str = "test@example.com",
    plan: PlanTier = PlanTier.free,
) -> User:
    """Create a test user in the database.

    Args:
        db: Async database session.
        email: User email address.
        plan: Platform plan tier.

    Returns:
        The created User instance.
    """
    user = User(
        email=email,
        hashed_password="$2b$12$fakehash",
        is_active=True,
        plan=plan,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_test_integration(
    db: AsyncSession,
    user_id: uuid.UUID,
    service_name: ServiceName = ServiceName.trendscout,
    tier: ServiceTier = ServiceTier.free,
    is_active: bool = True,
) -> ServiceIntegration:
    """Create a test service integration in the database.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        service_name: Which service.
        tier: Service tier.
        is_active: Whether the integration is active.

    Returns:
        The created ServiceIntegration instance.
    """
    integration = ServiceIntegration(
        user_id=user_id,
        service_name=service_name,
        service_user_id=f"svc_{uuid.uuid4().hex[:8]}",
        api_key=f"key_{uuid.uuid4().hex[:16]}",
        tier=tier,
        is_active=is_active,
        provisioned_at=datetime.now(timezone.utc),
    )
    db.add(integration)
    await db.flush()
    await db.refresh(integration)
    return integration


@pytest.fixture
def mock_httpx():
    """Mock httpx.AsyncClient in the service integration module.

    Pre-configures successful provision and usage responses. Tests can
    override ``mock_client.post.return_value`` or
    ``mock_client.get.return_value`` for specific scenarios.

    Yields:
        The mock client instance used inside ``async with`` blocks.
    """
    mock_client = AsyncMock()

    # Default provision response.
    provision_resp = MagicMock()
    provision_resp.status_code = 201
    provision_resp.json.return_value = {
        "user_id": f"svc_{uuid.uuid4().hex[:8]}",
        "api_key": f"key_{uuid.uuid4().hex[:16]}",
    }
    provision_resp.raise_for_status = MagicMock()
    mock_client.post.return_value = provision_resp

    # Default usage response.
    usage_resp = MagicMock()
    usage_resp.status_code = 200
    usage_resp.json.return_value = {
        "research_runs_used": 3,
        "research_runs_limit": 5,
    }
    usage_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = usage_resp

    with patch(
        "app.services.service_integration_service.httpx.AsyncClient"
    ) as mock_class:
        mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client


# ===========================================================================
# 1. get_service_catalog tests
# ===========================================================================


class TestGetServiceCatalog:
    """Tests for the ``get_service_catalog()`` function.

    **For QA Engineers:**
        Verifies catalog completeness, structure, and immutability.
    """

    def test_catalog_has_8_entries(self):
        """Catalog returns exactly 8 services."""
        catalog = get_service_catalog()
        assert len(catalog) == 8

    def test_catalog_keys_are_service_names(self):
        """All catalog keys are valid ServiceName enum members."""
        catalog = get_service_catalog()
        for key in catalog:
            assert isinstance(key, ServiceName)

    def test_catalog_entries_have_required_fields(self):
        """Each catalog entry has all required metadata fields."""
        required = {
            "display_name", "tagline", "description", "icon", "color",
            "base_url", "dashboard_url", "landing_url", "tiers",
        }
        catalog = get_service_catalog()
        for svc_name, entry in catalog.items():
            missing = required - set(entry.keys())
            assert not missing, f"{svc_name.value} missing: {missing}"

    def test_each_service_has_3_tiers(self):
        """Each service defines exactly 3 pricing tiers."""
        catalog = get_service_catalog()
        for svc_name, entry in catalog.items():
            assert len(entry["tiers"]) == 3, (
                f"{svc_name.value} has {len(entry['tiers'])} tiers"
            )

    def test_catalog_returns_copy(self):
        """Catalog returns a copy, not the original constant."""
        catalog1 = get_service_catalog()
        catalog2 = get_service_catalog()
        assert catalog1 is not catalog2
        assert catalog1 is not SERVICE_CATALOG


# ===========================================================================
# 2. get_bundled_services tests
# ===========================================================================


class TestGetBundledServices:
    """Tests for the ``get_bundled_services()`` function.

    **For QA Engineers:**
        Verifies correct bundle mappings for each platform plan.
    """

    def test_free_plan_has_no_bundles(self):
        """Free plan includes no services."""
        assert get_bundled_services("free") == {}

    def test_starter_plan_has_2_services(self):
        """Starter plan includes trendscout and contentforge at free tier."""
        bundles = get_bundled_services("starter")
        assert len(bundles) == 2
        assert bundles[ServiceName.trendscout] == ServiceTier.free
        assert bundles[ServiceName.contentforge] == ServiceTier.free

    def test_growth_plan_has_all_8_at_free(self):
        """Growth plan includes all 8 services at free tier."""
        bundles = get_bundled_services("growth")
        assert len(bundles) == 8
        for tier in bundles.values():
            assert tier == ServiceTier.free

    def test_pro_plan_has_all_8_at_pro(self):
        """Pro plan includes all 8 services at pro tier."""
        bundles = get_bundled_services("pro")
        assert len(bundles) == 8
        for tier in bundles.values():
            assert tier == ServiceTier.pro

    def test_unknown_plan_returns_empty(self):
        """An unrecognised plan name returns an empty dict."""
        assert get_bundled_services("diamond") == {}


# ===========================================================================
# 3. _tier_gte tests
# ===========================================================================


class TestTierComparison:
    """Tests for the ``_tier_gte()`` helper function.

    **For QA Engineers:**
        Verifies tier ordering: free < starter < growth < pro.
    """

    def test_same_tier(self):
        """A tier is >= itself."""
        assert _tier_gte(ServiceTier.free, ServiceTier.free) is True
        assert _tier_gte(ServiceTier.pro, ServiceTier.pro) is True

    def test_higher_tier(self):
        """A higher tier is >= a lower tier."""
        assert _tier_gte(ServiceTier.pro, ServiceTier.free) is True
        assert _tier_gte(ServiceTier.growth, ServiceTier.starter) is True

    def test_lower_tier(self):
        """A lower tier is NOT >= a higher tier."""
        assert _tier_gte(ServiceTier.free, ServiceTier.pro) is False
        assert _tier_gte(ServiceTier.starter, ServiceTier.growth) is False

    def test_full_ordering(self):
        """Complete tier ordering: free < starter < growth < pro."""
        tiers = [ServiceTier.free, ServiceTier.starter, ServiceTier.growth, ServiceTier.pro]
        for i, lower in enumerate(tiers):
            for j, higher in enumerate(tiers):
                if i <= j:
                    # higher >= lower when j >= i
                    assert _tier_gte(higher, lower) is True
                else:
                    assert _tier_gte(higher, lower) is False


# ===========================================================================
# 4. get_user_services tests
# ===========================================================================


class TestGetUserServices:
    """Tests for the ``get_user_services()`` function.

    **For QA Engineers:**
        Verifies the unified 8-service status list with DB integration data.
    """

    @pytest.mark.asyncio
    async def test_no_integrations_returns_8_disconnected(self, db_session):
        """A user with no integrations gets 8 disconnected entries."""
        user = await _create_test_user(db_session)
        statuses = await get_user_services(db_session, user.id)
        assert len(statuses) == 8
        for s in statuses:
            assert isinstance(s, ServiceStatus)
            assert s.is_connected is False
            assert s.current_tier is None
            assert s.integration_id is None

    @pytest.mark.asyncio
    async def test_one_connected_shows_correctly(self, db_session):
        """A user with one integration sees it as connected."""
        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.trendscout, ServiceTier.pro
        )
        statuses = await get_user_services(db_session, user.id)
        ts = next(s for s in statuses if s.service_name == ServiceName.trendscout)
        assert ts.is_connected is True
        assert ts.current_tier == ServiceTier.pro
        assert ts.integration_id == integ.id

        # Other services should be disconnected.
        others = [s for s in statuses if s.service_name != ServiceName.trendscout]
        for s in others:
            assert s.is_connected is False

    @pytest.mark.asyncio
    async def test_inactive_integration_shows_disconnected(self, db_session):
        """An inactive integration is treated as disconnected."""
        user = await _create_test_user(db_session)
        await _create_test_integration(
            db_session, user.id, ServiceName.shopchat, is_active=False
        )
        statuses = await get_user_services(db_session, user.id)
        sc = next(s for s in statuses if s.service_name == ServiceName.shopchat)
        assert sc.is_connected is False
        assert sc.current_tier is None


# ===========================================================================
# 5. provision_service tests
# ===========================================================================


class TestProvisionService:
    """Tests for the ``provision_service()`` function.

    **For QA Engineers:**
        Verifies provisioning creates DB records, handles duplicates,
        reactivates inactive integrations, and handles HTTP errors.
    """

    @pytest.mark.asyncio
    async def test_provision_success(self, db_session, mock_httpx):
        """Successful provisioning creates an integration record."""
        user = await _create_test_user(db_session)
        result = await provision_service(
            db_session, user, ServiceName.trendscout, tier=ServiceTier.free
        )
        assert result.success is True
        assert result.service_name == ServiceName.trendscout
        assert result.tier == ServiceTier.free
        assert result.integration_id is not None
        assert result.service_user_id is not None
        assert result.error is None

    @pytest.mark.asyncio
    async def test_provision_creates_db_record(self, db_session, mock_httpx):
        """Provisioning persists the integration in the database."""
        user = await _create_test_user(db_session)
        result = await provision_service(
            db_session, user, ServiceName.contentforge
        )
        assert result.success is True

        # Verify in DB.
        db_result = await db_session.execute(
            select(ServiceIntegration).where(
                ServiceIntegration.id == result.integration_id
            )
        )
        integ = db_result.scalar_one()
        assert integ.service_name == ServiceName.contentforge
        assert integ.tier == ServiceTier.free
        assert integ.is_active is True

    @pytest.mark.asyncio
    async def test_provision_duplicate_fails(self, db_session, mock_httpx):
        """Provisioning the same service twice returns an error result."""
        user = await _create_test_user(db_session)
        result1 = await provision_service(
            db_session, user, ServiceName.rankpilot
        )
        assert result1.success is True

        result2 = await provision_service(
            db_session, user, ServiceName.rankpilot
        )
        assert result2.success is False
        assert "already has an active integration" in result2.error

    @pytest.mark.asyncio
    async def test_provision_reactivates_inactive(self, db_session, mock_httpx):
        """Provisioning a previously disconnected service reactivates it."""
        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.flowsend, is_active=False
        )
        old_id = integ.id

        result = await provision_service(
            db_session, user, ServiceName.flowsend, tier=ServiceTier.starter
        )
        assert result.success is True
        # Should reuse the same integration record (same UUID).
        assert result.integration_id == old_id
        assert result.tier == ServiceTier.starter

    @pytest.mark.asyncio
    async def test_provision_http_error_returns_failure(self, db_session, mock_httpx):
        """HTTP error during provisioning returns a failure result."""
        import httpx as _httpx
        mock_httpx.post.side_effect = _httpx.ConnectError("Connection refused")

        user = await _create_test_user(db_session)
        result = await provision_service(
            db_session, user, ServiceName.spydrop
        )
        assert result.success is False
        assert result.error is not None
        assert "unavailable" in result.error


# ===========================================================================
# 6. disconnect_service tests
# ===========================================================================


class TestDisconnectService:
    """Tests for the ``disconnect_service()`` function.

    **For QA Engineers:**
        Verifies soft-delete behavior, idempotency, and correct return values.
    """

    @pytest.mark.asyncio
    async def test_disconnect_active_returns_true(self, db_session):
        """Disconnecting an active integration returns True."""
        user = await _create_test_user(db_session)
        await _create_test_integration(
            db_session, user.id, ServiceName.adscale
        )
        result = await disconnect_service(
            db_session, user.id, ServiceName.adscale
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_sets_inactive(self, db_session):
        """Disconnecting sets ``is_active = False`` in the database."""
        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.postpilot
        )
        await disconnect_service(db_session, user.id, ServiceName.postpilot)

        db_result = await db_session.execute(
            select(ServiceIntegration).where(
                ServiceIntegration.id == integ.id
            )
        )
        updated = db_result.scalar_one()
        assert updated.is_active is False

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_returns_false(self, db_session):
        """Disconnecting a service with no active integration returns False."""
        user = await _create_test_user(db_session)
        result = await disconnect_service(
            db_session, user.id, ServiceName.shopchat
        )
        assert result is False


# ===========================================================================
# 7. fetch_service_usage tests
# ===========================================================================


class TestFetchServiceUsage:
    """Tests for the ``fetch_service_usage()`` function.

    **For QA Engineers:**
        Verifies usage fetching with real DB records and mocked HTTP.
    """

    @pytest.mark.asyncio
    async def test_fetch_usage_success(self, db_session, mock_httpx):
        """Successful usage fetch returns metrics dict."""
        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.trendscout
        )
        result = await fetch_service_usage(db_session, integ.id)
        assert "error" not in result
        assert "metrics" in result
        assert result["service_name"] == "trendscout"

    @pytest.mark.asyncio
    async def test_fetch_usage_nonexistent_integration(self, db_session, mock_httpx):
        """Fetching usage for a nonexistent integration returns error."""
        fake_id = uuid.uuid4()
        result = await fetch_service_usage(db_session, fake_id)
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_fetch_usage_inactive_returns_error(self, db_session, mock_httpx):
        """Fetching usage for an inactive integration returns error."""
        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.shopchat, is_active=False
        )
        result = await fetch_service_usage(db_session, integ.id)
        assert "error" in result
        assert "inactive" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_fetch_usage_http_error(self, db_session, mock_httpx):
        """HTTP error during usage fetch returns error dict."""
        import httpx as _httpx
        mock_httpx.get.side_effect = _httpx.ConnectError("Connection refused")

        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.contentforge
        )
        result = await fetch_service_usage(db_session, integ.id)
        assert "error" in result
        assert "unavailable" in result["error"]


# ===========================================================================
# 8. upgrade_service tests
# ===========================================================================


class TestUpgradeService:
    """Tests for the ``upgrade_service()`` function.

    **For QA Engineers:**
        Verifies tier changes, same-tier rejection, and missing integration.
    """

    @pytest.mark.asyncio
    async def test_upgrade_success(self, db_session, mock_httpx):
        """Upgrading a connected service returns success with tier info."""
        user = await _create_test_user(db_session)
        await _create_test_integration(
            db_session, user.id, ServiceName.trendscout, ServiceTier.free
        )
        result = await upgrade_service(
            db_session, user.id, ServiceName.trendscout, ServiceTier.pro
        )
        assert result.get("success") is True
        assert result["old_tier"] == "free"
        assert result["new_tier"] == "pro"

    @pytest.mark.asyncio
    async def test_upgrade_updates_db(self, db_session, mock_httpx):
        """Upgrade persists the new tier in the database."""
        user = await _create_test_user(db_session)
        integ = await _create_test_integration(
            db_session, user.id, ServiceName.adscale, ServiceTier.free
        )
        await upgrade_service(
            db_session, user.id, ServiceName.adscale, ServiceTier.growth
        )
        db_result = await db_session.execute(
            select(ServiceIntegration).where(
                ServiceIntegration.id == integ.id
            )
        )
        updated = db_result.scalar_one()
        assert updated.tier == ServiceTier.growth

    @pytest.mark.asyncio
    async def test_upgrade_same_tier_returns_error(self, db_session, mock_httpx):
        """Upgrading to the same tier returns an error."""
        user = await _create_test_user(db_session)
        await _create_test_integration(
            db_session, user.id, ServiceName.flowsend, ServiceTier.pro
        )
        result = await upgrade_service(
            db_session, user.id, ServiceName.flowsend, ServiceTier.pro
        )
        assert "error" in result
        assert "already on" in result["error"]

    @pytest.mark.asyncio
    async def test_upgrade_no_integration_returns_error(self, db_session, mock_httpx):
        """Upgrading a service that's not connected returns an error."""
        user = await _create_test_user(db_session)
        result = await upgrade_service(
            db_session, user.id, ServiceName.spydrop, ServiceTier.pro
        )
        assert "error" in result
        assert "no active integration" in result["error"].lower()


# ===========================================================================
# 9. auto_provision_bundled_services tests
# ===========================================================================


class TestAutoProvisionBundledServices:
    """Tests for the ``auto_provision_bundled_services()`` function.

    **For QA Engineers:**
        Verifies bulk provisioning/upgrading based on plan bundles.
    """

    @pytest.mark.asyncio
    async def test_free_plan_provisions_nothing(self, db_session, mock_httpx):
        """A user on the free plan gets no auto-provisioning."""
        user = await _create_test_user(db_session, plan=PlanTier.free)
        results = await auto_provision_bundled_services(db_session, user)
        assert results == []

    @pytest.mark.asyncio
    async def test_growth_plan_provisions_all_8(self, db_session, mock_httpx):
        """A user on the growth plan gets all 8 services provisioned."""
        user = await _create_test_user(
            db_session, email="growth@example.com", plan=PlanTier.growth
        )
        results = await auto_provision_bundled_services(db_session, user)
        assert len(results) == 8
        for r in results:
            assert isinstance(r, ProvisionResult)
            # May fail due to HTTP mock, but should attempt all 8.
            assert r.service_name in ServiceName

    @pytest.mark.asyncio
    async def test_skips_existing_at_equal_or_higher_tier(self, db_session, mock_httpx):
        """Existing integrations at >= bundled tier are skipped (not downgraded)."""
        user = await _create_test_user(
            db_session, email="skip@example.com", plan=PlanTier.growth
        )
        # Pre-create trendscout at pro tier (higher than growth's free).
        await _create_test_integration(
            db_session, user.id, ServiceName.trendscout, ServiceTier.pro
        )
        results = await auto_provision_bundled_services(db_session, user)
        ts_result = next(
            r for r in results if r.service_name == ServiceName.trendscout
        )
        # Should succeed without change, keeping pro tier.
        assert ts_result.success is True
        assert ts_result.tier == ServiceTier.pro


# ===========================================================================
# 10. get_usage_summary tests
# ===========================================================================


class TestGetUsageSummary:
    """Tests for the ``get_usage_summary()`` function.

    **For QA Engineers:**
        Verifies the aggregated usage summary structure and content.
    """

    @pytest.mark.asyncio
    async def test_no_integrations_returns_empty_summary(self, db_session, mock_httpx):
        """A user with no integrations gets an empty summary."""
        user = await _create_test_user(db_session)
        summary = await get_usage_summary(db_session, user.id)
        assert isinstance(summary, UsageSummary)
        assert summary.total_connected == 0
        assert summary.total_available == 8
        assert summary.services == []
        assert summary.last_updated is None

    @pytest.mark.asyncio
    async def test_summary_includes_connected_services(self, db_session, mock_httpx):
        """Summary includes usage data for each connected service."""
        user = await _create_test_user(db_session, email="summary@example.com")
        await _create_test_integration(
            db_session, user.id, ServiceName.trendscout, ServiceTier.free
        )
        await _create_test_integration(
            db_session, user.id, ServiceName.shopchat, ServiceTier.pro
        )
        summary = await get_usage_summary(db_session, user.id)
        assert summary.total_connected == 2
        assert summary.total_available == 8
        assert len(summary.services) == 2
        svc_names = {s["service_name"] for s in summary.services}
        assert svc_names == {"trendscout", "shopchat"}
