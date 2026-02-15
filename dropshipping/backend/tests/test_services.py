"""Tests for service integration endpoints (Phase 2 - Automation & AI).

Comprehensive test suite covering the ``/api/v1/services/*`` endpoints for
managing connections between the dropshipping platform and 8 standalone SaaS
microservices (TrendScout, ContentForge, RankPilot, FlowSend, SpyDrop,
PostPilot, AdScale, ShopChat).

**For QA Engineers:**
    Each test is independent -- the database is reset between tests via the
    ``client`` fixture. External HTTP calls to microservices are mocked using
    ``unittest.mock.patch`` on ``httpx.AsyncClient`` to avoid real network
    traffic. Tests are organised into 8 categories:

    1. Catalog tests (5 tests) -- public endpoint, no auth
    2. Provision tests (6 tests) -- creating service integrations
    3. User services list tests (4 tests) -- listing connection status
    4. Disconnect tests (3 tests) -- soft-deleting integrations
    5. Usage tests (4 tests) -- fetching usage metrics
    6. Upgrade tests (4 tests) -- changing service tiers
    7. Bundle tests (5 tests) -- platform plan service bundles
    8. Lifecycle tests (3 tests) -- end-to-end workflows

**For Developers:**
    The ``mock_service_http`` fixture patches ``httpx.AsyncClient`` globally
    within the ``service_integration_service`` module. Mock responses are
    pre-configured for provision (POST) and usage (GET) calls, with a
    ``raise_for_status`` that is a no-op by default.

    Helper functions ``register_and_get_token`` and ``provision_trendscout``
    reduce boilerplate for setting up authenticated users and pre-connected
    services.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(
    client, email: str = "svc@example.com"
) -> str:
    """Register a user and return the JWT access token.

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        The JWT access token string.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    assert resp.status_code in (200, 201), f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


def _make_mock_response(status_code: int = 200, json_data: dict | None = None):
    """Create a mock httpx Response object.

    Args:
        status_code: HTTP status code for the response.
        json_data: JSON body to return from ``.json()``.

    Returns:
        A MagicMock configured to behave like an httpx.Response.

    **For Developers:**
        The ``raise_for_status`` method is a no-op by default so that
        successful responses don't raise. Override it with a side_effect
        to simulate HTTP errors.
    """
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = str(json_data or {})
    resp.raise_for_status = MagicMock()  # No-op by default
    return resp


def _make_mock_client():
    """Create a pre-configured mock httpx.AsyncClient.

    Returns:
        An AsyncMock configured as an httpx.AsyncClient with default
        provision (POST) and usage (GET) responses.

    **For Developers:**
        The mock is set up for the async context manager pattern used
        by ``async with httpx.AsyncClient(...) as client:``. Override
        ``mock_client.post.return_value`` or ``mock_client.get.return_value``
        in individual tests to simulate error scenarios.
    """
    mock_client = AsyncMock()

    # Default provision response (POST).
    provision_resp = _make_mock_response(
        status_code=201,
        json_data={
            "user_id": str(uuid.uuid4()),
            "api_key": "ts_live_test123456789",
        },
    )
    mock_client.post.return_value = provision_resp

    # Default usage response (GET).
    usage_resp = _make_mock_response(
        status_code=200,
        json_data={
            "plan": "free",
            "period_start": "2026-02-01",
            "period_end": "2026-02-28",
            "research_runs_used": 3,
            "research_runs_limit": 5,
        },
    )
    mock_client.get.return_value = usage_resp

    return mock_client


@pytest.fixture
def mock_service_http():
    """Mock external service HTTP calls via httpx.AsyncClient.

    Patches ``httpx.AsyncClient`` in the ``service_integration_service``
    module so that provision and usage calls return canned responses
    instead of hitting real microservices.

    Yields:
        The mock client instance with pre-configured ``post`` and ``get``
        return values. Tests can override these for specific scenarios.

    **For Developers:**
        The mock patches the async context manager pattern:
        ``async with httpx.AsyncClient(...) as client:``
        The yielded ``mock_client`` is what gets used inside the ``with``
        block, so override ``mock_client.post.return_value`` to change
        the provision response, etc.
    """
    mock_client = _make_mock_client()

    with patch(
        "app.services.service_integration_service.httpx.AsyncClient"
    ) as mock_class:
        # Make the async context manager return the mock client.
        mock_class.return_value.__aenter__ = AsyncMock(
            return_value=mock_client
        )
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client


async def provision_trendscout(
    client, token: str, mock_client: AsyncMock
) -> dict:
    """Provision TrendScout for the authenticated user.

    A convenience helper that provisions TrendScout at the free tier
    and returns the response JSON. Requires mock_service_http fixture.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        mock_client: The mock httpx client from ``mock_service_http``.

    Returns:
        The JSON response dict from the provision endpoint.
    """
    resp = await client.post(
        "/api/v1/services/trendscout/provision",
        json={"service_name": "trendscout", "tier": "free"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Provision failed: {resp.text}"
    return resp.json()


# ===========================================================================
# 1. Catalog Tests (5 tests)
# ===========================================================================


class TestServiceCatalog:
    """Tests for GET /api/v1/services/catalog (public, no auth).

    **For QA Engineers:**
        Verify the catalog returns all 8 services with correct metadata
        and that no authentication is required.
    """

    @pytest.mark.asyncio
    async def test_catalog_returns_all_8_services(self, client):
        """GET /catalog returns exactly 8 services.

        Validates that the service catalog endpoint returns one entry
        for each known microservice.
        """
        resp = await client.get("/api/v1/services/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 8

    @pytest.mark.asyncio
    async def test_catalog_service_fields(self, client):
        """Each catalog entry has all required fields.

        Validates the shape of each service entry in the catalog,
        ensuring all metadata fields are present.
        """
        resp = await client.get("/api/v1/services/catalog")
        assert resp.status_code == 200
        data = resp.json()

        required_fields = {
            "name", "display_name", "tagline", "description",
            "icon", "color", "dashboard_url", "landing_url", "tiers",
        }
        for service in data:
            assert required_fields.issubset(set(service.keys())), (
                f"Missing fields in service {service.get('name')}: "
                f"{required_fields - set(service.keys())}"
            )

    @pytest.mark.asyncio
    async def test_catalog_each_service_has_3_tiers(self, client):
        """Each service offers exactly 3 pricing tiers (free, pro, enterprise).

        Validates tier structure completeness for all services.
        """
        resp = await client.get("/api/v1/services/catalog")
        data = resp.json()

        for service in data:
            assert len(service["tiers"]) == 3, (
                f"Expected 3 tiers for {service['name']}, "
                f"got {len(service['tiers'])}"
            )
            tier_names = {t["tier"] for t in service["tiers"]}
            assert tier_names == {"free", "pro", "enterprise"}

    @pytest.mark.asyncio
    async def test_catalog_does_not_require_auth(self, client):
        """The catalog endpoint is public and returns 200 without auth.

        Ensures unauthenticated users can browse available services.
        """
        resp = await client.get("/api/v1/services/catalog")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_catalog_service_names_match_enum(self, client):
        """All 8 known service names appear in the catalog response.

        Cross-references the returned service names against the
        expected ServiceName enum values.
        """
        expected_names = {
            "trendscout", "contentforge", "rankpilot", "flowsend",
            "spydrop", "postpilot", "adscale", "shopchat",
        }
        resp = await client.get("/api/v1/services/catalog")
        data = resp.json()
        actual_names = {s["name"] for s in data}
        assert actual_names == expected_names


# ===========================================================================
# 2. Provision Tests (6 tests)
# ===========================================================================


class TestProvisionService:
    """Tests for POST /api/v1/services/{service_name}/provision.

    **For QA Engineers:**
        Verify provisioning creates an integration, returns correct status
        codes, and rejects invalid/duplicate requests.
    """

    @pytest.mark.asyncio
    async def test_provision_success(self, client, mock_service_http):
        """Provisioning a service returns 201 with integration details.

        Validates the happy path: register user, provision TrendScout,
        and verify the response contains all expected fields.
        """
        token = await register_and_get_token(client)
        resp = await client.post(
            "/api/v1/services/trendscout/provision",
            json={"service_name": "trendscout", "tier": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["service_name"] == "trendscout"
        assert data["tier"] == "free"
        assert "integration_id" in data
        assert "service_user_id" in data
        assert "dashboard_url" in data
        assert "provisioned_at" in data

    @pytest.mark.asyncio
    async def test_provision_creates_integration_record(
        self, client, mock_service_http
    ):
        """Provisioning creates a record visible in the user services list.

        After provisioning, GET /services should show the service as
        connected with the correct tier.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        # Verify via user services list.
        resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        trendscout = next(
            s for s in data
            if s["service"]["name"] == "trendscout"
        )
        assert trendscout["is_connected"] is True
        assert trendscout["current_tier"] == "free"
        assert trendscout["integration_id"] is not None

    @pytest.mark.asyncio
    async def test_provision_response_format(
        self, client, mock_service_http
    ):
        """Provision response matches the ProvisionServiceResponse schema.

        Verifies the response shape has exactly the expected keys and
        value types.
        """
        token = await register_and_get_token(client)
        resp = await client.post(
            "/api/v1/services/contentforge/provision",
            json={"service_name": "contentforge"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        expected_keys = {
            "integration_id", "service_name", "service_user_id",
            "tier", "dashboard_url", "provisioned_at",
        }
        assert set(data.keys()) == expected_keys

    @pytest.mark.asyncio
    async def test_provision_invalid_service_name(self, client, mock_service_http):
        """Provisioning an unknown service returns 400.

        Validates that invalid service names are rejected with a clear
        error message listing valid options.
        """
        token = await register_and_get_token(client)
        resp = await client.post(
            "/api/v1/services/nonexistent/provision",
            json={"service_name": "trendscout", "tier": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "unknown service" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_provision_duplicate_returns_409(
        self, client, mock_service_http
    ):
        """Provisioning the same service twice returns 409 Conflict.

        After provisioning TrendScout once, a second provision attempt
        should be rejected with a conflict error.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        # Second provision should fail.
        resp = await client.post(
            "/api/v1/services/trendscout/provision",
            json={"service_name": "trendscout", "tier": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409
        assert "already" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_provision_requires_auth(self, client, mock_service_http):
        """Provisioning without authentication returns 401.

        Validates that the provision endpoint enforces JWT authentication.
        """
        resp = await client.post(
            "/api/v1/services/trendscout/provision",
            json={"service_name": "trendscout", "tier": "free"},
        )
        assert resp.status_code == 401


# ===========================================================================
# 3. User Services List Tests (4 tests)
# ===========================================================================


class TestUserServicesList:
    """Tests for GET /api/v1/services (authenticated).

    **For QA Engineers:**
        Verify the list always returns all 8 services and correctly
        reflects connection status.
    """

    @pytest.mark.asyncio
    async def test_list_returns_all_8_services(self, client):
        """GET /services returns exactly 8 service status entries.

        Even with no connections, all services should appear.
        """
        token = await register_and_get_token(client)
        resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 8

    @pytest.mark.asyncio
    async def test_connected_service_shows_tier_and_timestamp(
        self, client, mock_service_http
    ):
        """Connected services show tier and provisioned_at in the list.

        After provisioning, the service entry should have ``is_connected=True``
        with the tier and timestamp populated.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        trendscout = next(
            s for s in data if s["service"]["name"] == "trendscout"
        )
        assert trendscout["is_connected"] is True
        assert trendscout["current_tier"] == "free"
        assert trendscout["provisioned_at"] is not None

    @pytest.mark.asyncio
    async def test_disconnected_services_show_not_connected(self, client):
        """Disconnected services have is_connected=False and null tier.

        Before any provisioning, all services should show as disconnected.
        """
        token = await register_and_get_token(client)
        resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        for svc in data:
            assert svc["is_connected"] is False
            assert svc["current_tier"] is None
            assert svc["provisioned_at"] is None
            assert svc["integration_id"] is None

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        """GET /services without authentication returns 401.

        Validates that the user services list enforces JWT authentication.
        """
        resp = await client.get("/api/v1/services")
        assert resp.status_code == 401


# ===========================================================================
# 4. Disconnect Tests (3 tests)
# ===========================================================================


class TestDisconnectService:
    """Tests for DELETE /api/v1/services/{service_name}.

    **For QA Engineers:**
        Verify disconnect marks integrations inactive, returns 204,
        and handles edge cases (not connected, no auth).
    """

    @pytest.mark.asyncio
    async def test_disconnect_success(self, client, mock_service_http):
        """Disconnecting a connected service returns 204.

        After provisioning and disconnecting, the service should appear
        as not connected in the list.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        resp = await client.delete(
            "/api/v1/services/trendscout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204
        assert resp.content == b""

        # Verify it's disconnected in the list.
        resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        trendscout = next(
            s for s in resp.json()
            if s["service"]["name"] == "trendscout"
        )
        assert trendscout["is_connected"] is False

    @pytest.mark.asyncio
    async def test_disconnect_not_connected_returns_404(self, client):
        """Disconnecting a service that's not connected returns 404.

        The user has never provisioned TrendScout, so disconnect should
        fail with a not-found error.
        """
        token = await register_and_get_token(client)
        resp = await client.delete(
            "/api/v1/services/trendscout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_disconnect_requires_auth(self, client):
        """Disconnecting without authentication returns 401.

        Validates that the disconnect endpoint enforces JWT authentication.
        """
        resp = await client.delete("/api/v1/services/trendscout")
        assert resp.status_code == 401


# ===========================================================================
# 5. Usage Tests (4 tests)
# ===========================================================================


class TestServiceUsage:
    """Tests for GET /api/v1/services/{service_name}/usage and usage summary.

    **For QA Engineers:**
        Verify usage returns metrics for connected services and proper
        error responses for unconnected or invalid services.
    """

    @pytest.mark.asyncio
    async def test_fetch_usage_success(self, client, mock_service_http):
        """Fetching usage for a connected service returns 200 with metrics.

        After provisioning TrendScout, fetching its usage should return
        data with correct fields.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        resp = await client.get(
            "/api/v1/services/trendscout/usage",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["service_name"] == "trendscout"
        assert data["tier"] == "free"
        assert "period_start" in data
        assert "period_end" in data
        assert "metrics" in data
        assert "fetched_at" in data

    @pytest.mark.asyncio
    async def test_usage_summary_no_services(self, client):
        """Usage summary with no connected services returns empty list.

        A user with no integrations should get an empty services list
        with zero costs.
        """
        token = await register_and_get_token(client)
        resp = await client.get(
            "/api/v1/services/usage/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["services"] == []
        assert data["total_monthly_cost_cents"] == 0
        assert data["bundle_savings_cents"] == 0

    @pytest.mark.asyncio
    async def test_usage_not_connected_returns_404(self, client):
        """Fetching usage for an unconnected service returns 404.

        The user has not provisioned TrendScout, so usage fetch should
        fail with a not-found error.
        """
        token = await register_and_get_token(client)
        resp = await client.get(
            "/api/v1/services/trendscout/usage",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_usage_requires_auth(self, client):
        """Fetching usage without authentication returns 401.

        Validates that the usage endpoint enforces JWT authentication.
        """
        resp = await client.get("/api/v1/services/trendscout/usage")
        assert resp.status_code == 401


# ===========================================================================
# 6. Upgrade Tests (4 tests)
# ===========================================================================


class TestUpgradeService:
    """Tests for POST /api/v1/services/{service_name}/upgrade.

    **For QA Engineers:**
        Verify upgrade changes the tier, returns correct response,
        and handles error conditions (not connected, invalid tier).
    """

    @pytest.mark.asyncio
    async def test_upgrade_success(self, client, mock_service_http):
        """Upgrading a connected service returns 200 with new tier info.

        After provisioning at free tier, upgrading to pro should succeed
        with a confirmation message.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        resp = await client.post(
            "/api/v1/services/trendscout/upgrade",
            json={"tier": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["service_name"] == "trendscout"
        assert data["old_tier"] == "free"
        assert data["new_tier"] == "pro"
        assert "message" in data

    @pytest.mark.asyncio
    async def test_upgrade_not_connected_returns_404(self, client, mock_service_http):
        """Upgrading an unconnected service returns 404.

        The user has not provisioned TrendScout, so upgrade should
        fail with a not-found error.
        """
        token = await register_and_get_token(client)
        resp = await client.post(
            "/api/v1/services/trendscout/upgrade",
            json={"tier": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_upgrade_invalid_tier_returns_422(self, client, mock_service_http):
        """Upgrading to an invalid tier returns 422 (validation error).

        Pydantic validation should reject unknown tier values before
        the endpoint logic runs.
        """
        token = await register_and_get_token(client)
        await provision_trendscout(client, token, mock_service_http)

        resp = await client.post(
            "/api/v1/services/trendscout/upgrade",
            json={"tier": "diamond"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_upgrade_requires_auth(self, client):
        """Upgrading without authentication returns 401.

        Validates that the upgrade endpoint enforces JWT authentication.
        """
        resp = await client.post(
            "/api/v1/services/trendscout/upgrade",
            json={"tier": "pro"},
        )
        assert resp.status_code == 401


# ===========================================================================
# 7. Bundle Tests (5 tests)
# ===========================================================================


class TestServiceBundles:
    """Tests for GET /api/v1/services/bundles (public, no auth).

    **For QA Engineers:**
        Verify bundle data matches the platform plan definitions and
        that no authentication is required.
    """

    @pytest.mark.asyncio
    async def test_bundles_returns_all_plans(self, client):
        """GET /bundles without filter returns bundles for all 4 plans.

        Validates that free, starter, growth, and pro are all present.
        """
        resp = await client.get("/api/v1/services/bundles")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        plans = {b["plan"] for b in data}
        assert plans == {"free", "starter", "growth", "pro"}

    @pytest.mark.asyncio
    async def test_growth_plan_includes_all_8_at_free(self, client):
        """Growth plan includes all 8 services at free tier.

        The growth bundle should have exactly 8 services, each at
        the free tier.
        """
        resp = await client.get(
            "/api/v1/services/bundles", params={"plan": "growth"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        growth = data[0]
        assert growth["plan"] == "growth"
        assert len(growth["included_services"]) == 8
        for svc in growth["included_services"]:
            assert svc["included_tier"] == "free"

    @pytest.mark.asyncio
    async def test_pro_plan_includes_all_8_at_pro(self, client):
        """Pro plan includes all 8 services at pro tier.

        The pro bundle should have exactly 8 services, each at
        the pro tier.
        """
        resp = await client.get(
            "/api/v1/services/bundles", params={"plan": "pro"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        pro = data[0]
        assert pro["plan"] == "pro"
        assert len(pro["included_services"]) == 8
        for svc in pro["included_services"]:
            assert svc["included_tier"] == "pro"

    @pytest.mark.asyncio
    async def test_free_plan_includes_no_services(self, client):
        """Free plan includes no services (empty included_services).

        Free-tier platform users don't get any bundled service access.
        """
        resp = await client.get(
            "/api/v1/services/bundles", params={"plan": "free"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        free = data[0]
        assert free["plan"] == "free"
        assert len(free["included_services"]) == 0

    @pytest.mark.asyncio
    async def test_bundles_does_not_require_auth(self, client):
        """The bundles endpoint is public and returns 200 without auth.

        Ensures the pricing page can display bundle data to anonymous
        visitors.
        """
        resp = await client.get("/api/v1/services/bundles")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_bundles_invalid_plan_returns_400(self, client):
        """Requesting bundles for an invalid plan returns 400.

        Validates that the endpoint rejects unrecognised plan names.
        """
        resp = await client.get(
            "/api/v1/services/bundles", params={"plan": "diamond"}
        )
        assert resp.status_code == 400
        assert "invalid plan" in resp.json()["detail"].lower()


# ===========================================================================
# 8. Full Lifecycle Tests (3 tests)
# ===========================================================================


class TestServiceLifecycle:
    """End-to-end lifecycle tests covering provision -> usage -> upgrade -> disconnect.

    **For QA Engineers:**
        These tests verify the complete user journey through service
        integration, ensuring all state transitions work correctly.
    """

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, client, mock_service_http):
        """Complete lifecycle: provision -> usage -> upgrade -> disconnect.

        Walks through the entire flow a user would follow when connecting,
        using, upgrading, and disconnecting a service.
        """
        token = await register_and_get_token(client, email="lifecycle@example.com")

        # 1. Provision TrendScout.
        provision_resp = await client.post(
            "/api/v1/services/trendscout/provision",
            json={"service_name": "trendscout", "tier": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert provision_resp.status_code == 201
        assert provision_resp.json()["tier"] == "free"

        # 2. Verify it appears as connected.
        list_resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        trendscout = next(
            s for s in list_resp.json()
            if s["service"]["name"] == "trendscout"
        )
        assert trendscout["is_connected"] is True

        # 3. Fetch usage.
        usage_resp = await client.get(
            "/api/v1/services/trendscout/usage",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert usage_resp.status_code == 200
        assert "metrics" in usage_resp.json()

        # 4. Upgrade to pro.
        upgrade_resp = await client.post(
            "/api/v1/services/trendscout/upgrade",
            json={"tier": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert upgrade_resp.status_code == 200
        assert upgrade_resp.json()["new_tier"] == "pro"

        # 5. Verify upgrade persisted.
        list_resp2 = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        trendscout2 = next(
            s for s in list_resp2.json()
            if s["service"]["name"] == "trendscout"
        )
        assert trendscout2["current_tier"] == "pro"

        # 6. Disconnect.
        disconnect_resp = await client.delete(
            "/api/v1/services/trendscout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert disconnect_resp.status_code == 204

        # 7. Verify disconnected.
        list_resp3 = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        trendscout3 = next(
            s for s in list_resp3.json()
            if s["service"]["name"] == "trendscout"
        )
        assert trendscout3["is_connected"] is False

    @pytest.mark.asyncio
    async def test_provision_multiple_services(
        self, client, mock_service_http
    ):
        """Provisioning multiple services creates independent integrations.

        Users should be able to connect multiple services simultaneously,
        each tracked independently.
        """
        token = await register_and_get_token(client, email="multi@example.com")

        # Provision TrendScout and ContentForge.
        resp1 = await client.post(
            "/api/v1/services/trendscout/provision",
            json={"service_name": "trendscout", "tier": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/services/contentforge/provision",
            json={"service_name": "contentforge", "tier": "free"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 201

        # Verify both appear connected.
        list_resp = await client.get(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
        )
        connected = [
            s for s in list_resp.json() if s["is_connected"]
        ]
        assert len(connected) == 2
        connected_names = {s["service"]["name"] for s in connected}
        assert connected_names == {"trendscout", "contentforge"}

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(
        self, client, mock_service_http
    ):
        """A user can reconnect a service after disconnecting it.

        After disconnect, a new provision call should succeed and
        create a fresh integration.
        """
        token = await register_and_get_token(client, email="reconnect@example.com")

        # Provision, disconnect, re-provision.
        await provision_trendscout(client, token, mock_service_http)

        resp = await client.delete(
            "/api/v1/services/trendscout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        resp = await client.post(
            "/api/v1/services/trendscout/provision",
            json={"service_name": "trendscout", "tier": "pro"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["tier"] == "pro"
