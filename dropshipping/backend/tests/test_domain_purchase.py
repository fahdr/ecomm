"""Tests for domain purchasing (Feature 7).

Covers domain search, purchase, renewal, auto-renew toggle, owned domain
listing, and full purchase flow with auto-DNS and SSL.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Domain search uses ``/domains/search?q=...&tlds=...``.
    Purchase uses ``/stores/{store_id}/domain/purchase``.
    Renewal uses ``/stores/{store_id}/domain/renew``.
    Auto-renew uses ``PATCH /stores/{store_id}/domain/auto-renew``.
    Owned domains uses ``/domains/owned``.
"""

import pytest

from app.services.domain_registrar.mock import MockDomainProvider
from app.services.domain_registrar.factory import get_domain_provider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(client, email: str = "purchase@example.com") -> str:
    """Register a user and return the access token.

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
    return resp.json()["access_token"]


async def create_test_store(
    client, token: str, name: str = "Purchase Store", niche: str = "electronics"
) -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        name: Store name.
        niche: Store niche.

    Returns:
        The JSON response dictionary for the created store.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": niche},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# MockDomainProvider unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_search_domains():
    """MockDomainProvider.search_domains returns results for each TLD."""
    provider = MockDomainProvider()
    results = await provider.search_domains("mybrand", ["com", "io", "store"])
    assert len(results) == 3
    assert results[0].domain == "mybrand.com"
    assert results[0].available is True
    assert results[1].domain == "mybrand.io"
    assert results[2].domain == "mybrand.store"


@pytest.mark.asyncio
async def test_mock_provider_search_unavailable():
    """MockDomainProvider marks domains with 'taken' in query as unavailable."""
    provider = MockDomainProvider()
    results = await provider.search_domains("taken", ["com"])
    assert len(results) == 1
    assert results[0].available is False


@pytest.mark.asyncio
async def test_mock_provider_purchase_domain():
    """MockDomainProvider.purchase_domain returns success with order details."""
    provider = MockDomainProvider()
    result = await provider.purchase_domain("mybrand.com", 1, {})
    assert result.domain == "mybrand.com"
    assert result.status == "success"
    assert result.order_id.startswith("mock-order-")
    assert result.expiry_date is not None


@pytest.mark.asyncio
async def test_mock_provider_check_availability():
    """MockDomainProvider.check_availability returns search result."""
    provider = MockDomainProvider()
    result = await provider.check_availability("available.com")
    assert result.available is True
    assert result.domain == "available.com"


@pytest.mark.asyncio
async def test_mock_provider_check_availability_taken():
    """MockDomainProvider.check_availability returns unavailable for taken domains."""
    provider = MockDomainProvider()
    result = await provider.check_availability("taken.com")
    assert result.available is False


@pytest.mark.asyncio
async def test_mock_provider_renew_domain():
    """MockDomainProvider.renew_domain returns success with new expiry."""
    provider = MockDomainProvider()
    result = await provider.renew_domain("mybrand.com", 2)
    assert result.domain == "mybrand.com"
    assert result.status == "success"
    assert result.order_id.startswith("mock-renew-")
    assert result.expiry_date is not None


@pytest.mark.asyncio
async def test_mock_provider_set_nameservers():
    """MockDomainProvider.set_nameservers always returns True."""
    provider = MockDomainProvider()
    result = await provider.set_nameservers(
        "mybrand.com", ["ns1.platform.app", "ns2.platform.app"]
    )
    assert result is True


@pytest.mark.asyncio
async def test_mock_provider_get_domain_info():
    """MockDomainProvider.get_domain_info returns domain details dict."""
    provider = MockDomainProvider()
    info = await provider.get_domain_info("mybrand.com")
    assert info["domain"] == "mybrand.com"
    assert info["status"] == "active"
    assert info["registrar"] == "mock"
    assert "nameservers" in info


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_domain_factory_returns_mock():
    """get_domain_provider returns MockDomainProvider by default."""
    provider = get_domain_provider()
    assert isinstance(provider, MockDomainProvider)


@pytest.mark.asyncio
async def test_domain_factory_returns_resellerclub():
    """get_domain_provider returns ResellerClubProvider when configured."""
    from unittest.mock import patch
    from app.services.domain_registrar.resellerclub import ResellerClubProvider

    with patch("app.config.settings") as mock_settings:
        mock_settings.domain_provider_mode = "resellerclub"
        mock_settings.resellerclub_api_key = "key"
        mock_settings.resellerclub_reseller_id = "id"
        provider = get_domain_provider()
        assert isinstance(provider, ResellerClubProvider)


@pytest.mark.asyncio
async def test_domain_factory_returns_squarespace():
    """get_domain_provider returns SquarespaceDomainProvider when configured."""
    from unittest.mock import patch
    from app.services.domain_registrar.squarespace import SquarespaceDomainProvider

    with patch("app.config.settings") as mock_settings:
        mock_settings.domain_provider_mode = "squarespace"
        mock_settings.squarespace_api_key = "key"
        provider = get_domain_provider()
        assert isinstance(provider, SquarespaceDomainProvider)


# ---------------------------------------------------------------------------
# Domain Search API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_domains_endpoint(client):
    """Search endpoint returns domain availability and pricing."""
    token = await register_and_get_token(client, "search@example.com")

    resp = await client.get(
        "/api/v1/domains/search?q=mybrand&tlds=com,io,store",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 3

    # Check result shape
    result = data["results"][0]
    assert "domain" in result
    assert "available" in result
    assert "price" in result
    assert "currency" in result
    assert "period_years" in result


@pytest.mark.asyncio
async def test_search_domains_no_auth(client):
    """Search without authentication returns 401."""
    resp = await client.get("/api/v1/domains/search?q=mybrand")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_domains_default_tlds(client):
    """Search with default TLDs returns com, io, store."""
    token = await register_and_get_token(client, "default-tlds@example.com")

    resp = await client.get(
        "/api/v1/domains/search?q=testbrand",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    domains = [r["domain"] for r in data["results"]]
    assert "testbrand.com" in domains
    assert "testbrand.io" in domains
    assert "testbrand.store" in domains


# ---------------------------------------------------------------------------
# Domain Purchase API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_domain_success(client):
    """Purchasing a domain creates the domain record with purchase info."""
    token = await register_and_get_token(client, "buyer@example.com")
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "mybrand.com", "years": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["domain"] == "mybrand.com"
    assert data["status"] == "success"
    assert data["order_id"] is not None
    assert data["expiry_date"] is not None
    assert data["auto_dns_configured"] is True
    assert data["ssl_provisioned"] is True


@pytest.mark.asyncio
async def test_purchase_domain_no_auth(client):
    """Purchasing without authentication returns 401."""
    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/domain/purchase",
        json={"domain": "noauth.com"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_purchase_domain_store_not_found(client):
    """Purchasing for a nonexistent store returns 404."""
    token = await register_and_get_token(client, "no-store@example.com")

    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/domain/purchase",
        json={"domain": "nostore.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_purchase_domain_already_has_domain(client):
    """Purchasing when store already has a domain returns 400."""
    token = await register_and_get_token(client, "dup-domain@example.com")
    store = await create_test_store(client, token)

    # Set a domain first
    await client.post(
        f"/api/v1/stores/{store['id']}/domain",
        json={"domain": "existing.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to purchase another
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "another.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Domain Renewal API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_renew_domain_success(client):
    """Renewing a purchased domain returns new expiry date."""
    token = await register_and_get_token(client, "renew@example.com")
    store = await create_test_store(client, token)

    # Purchase first
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "renewme.com", "years": 1},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Renew
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/renew",
        json={"years": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "renewme.com"
    assert data["new_expiry_date"] is not None
    assert data["order_id"] is not None


@pytest.mark.asyncio
async def test_renew_non_purchased_domain(client):
    """Renewing a non-purchased domain returns 400."""
    token = await register_and_get_token(client, "renew-np@example.com")
    store = await create_test_store(client, token)

    # Set a domain (not purchased)
    await client.post(
        f"/api/v1/stores/{store['id']}/domain",
        json={"domain": "notpurchased.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Try to renew
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/renew",
        json={"years": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "not purchased" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_renew_no_domain(client):
    """Renewing when no domain exists returns 404."""
    token = await register_and_get_token(client, "renew-none@example.com")
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/renew",
        json={"years": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auto-Renew Toggle API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_auto_renew_on(client):
    """Enabling auto-renew returns the updated status."""
    token = await register_and_get_token(client, "auto-on@example.com")
    store = await create_test_store(client, token)

    # Purchase domain
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "autorenew-on.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Enable auto-renew
    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/domain/auto-renew",
        json={"auto_renew": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "autorenew-on.com"
    assert data["auto_renew"] is True


@pytest.mark.asyncio
async def test_toggle_auto_renew_off(client):
    """Disabling auto-renew returns the updated status."""
    token = await register_and_get_token(client, "auto-off@example.com")
    store = await create_test_store(client, token)

    # Purchase and enable auto-renew
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "autorenew-off.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.patch(
        f"/api/v1/stores/{store['id']}/domain/auto-renew",
        json={"auto_renew": True},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Disable auto-renew
    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/domain/auto-renew",
        json={"auto_renew": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["auto_renew"] is False


@pytest.mark.asyncio
async def test_toggle_auto_renew_non_purchased(client):
    """Toggling auto-renew on a non-purchased domain returns 400."""
    token = await register_and_get_token(client, "auto-np@example.com")
    store = await create_test_store(client, token)

    # Set a domain (not purchased)
    await client.post(
        f"/api/v1/stores/{store['id']}/domain",
        json={"domain": "notpurchased-ar.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/domain/auto-renew",
        json={"auto_renew": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Owned Domains API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_owned_domains_empty(client):
    """Listing owned domains with no purchases returns empty list."""
    token = await register_and_get_token(client, "empty-owned@example.com")

    resp = await client.get(
        "/api/v1/domains/owned",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domains"] == []


@pytest.mark.asyncio
async def test_list_owned_domains_with_purchase(client):
    """Listing owned domains after purchase returns the domain."""
    token = await register_and_get_token(client, "has-owned@example.com")
    store = await create_test_store(client, token)

    # Purchase a domain
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "owned-domain.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/domains/owned",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["domains"]) == 1
    assert data["domains"][0]["domain"] == "owned-domain.com"
    assert data["domains"][0]["is_purchased"] is True


@pytest.mark.asyncio
async def test_list_owned_domains_excludes_non_purchased(client):
    """Owned domains list only includes purchased domains -- non-purchased are excluded.

    Uses a single store to avoid plan-limit issues. Sets a non-purchased
    domain first, removes it, then purchases a domain on the same store.
    """
    token = await register_and_get_token(client, "mixed@example.com")
    store = await create_test_store(client, token, name="Mixed Store")

    # Set a domain (not purchased) on the store
    await client.post(
        f"/api/v1/stores/{store['id']}/domain",
        json={"domain": "not-purchased-list.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Owned domains should be empty (not-purchased domain excluded)
    resp = await client.get(
        "/api/v1/domains/owned",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(resp.json()["domains"]) == 0

    # Remove the non-purchased domain
    await client.delete(
        f"/api/v1/stores/{store['id']}/domain",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Purchase a domain on the same store
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "purchased-list.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        "/api/v1/domains/owned",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    assert len(data["domains"]) == 1
    assert data["domains"][0]["domain"] == "purchased-list.com"


# ---------------------------------------------------------------------------
# Full purchase lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_full_lifecycle(client):
    """Full lifecycle: search -> purchase -> check owned -> renew -> toggle auto-renew."""
    token = await register_and_get_token(client, "full-life@example.com")
    store = await create_test_store(client, token)

    # 1. Search
    search_resp = await client.get(
        "/api/v1/domains/search?q=fulllife&tlds=com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["results"][0]["available"] is True

    # 2. Purchase
    purchase_resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "fulllife.com", "years": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert purchase_resp.status_code == 201
    assert purchase_resp.json()["status"] == "success"

    # 3. Check owned
    owned_resp = await client.get(
        "/api/v1/domains/owned",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(owned_resp.json()["domains"]) == 1

    # 4. Renew
    renew_resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/renew",
        json={"years": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert renew_resp.status_code == 200
    assert renew_resp.json()["order_id"] is not None

    # 5. Toggle auto-renew
    auto_resp = await client.patch(
        f"/api/v1/stores/{store['id']}/domain/auto-renew",
        json={"auto_renew": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auto_resp.status_code == 200
    assert auto_resp.json()["auto_renew"] is True


@pytest.mark.asyncio
async def test_purchase_response_shape(client):
    """Purchase response includes all expected fields."""
    token = await register_and_get_token(client, "shape-p@example.com")
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/purchase",
        json={"domain": "shape-test.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    expected_keys = {
        "domain", "order_id", "status", "expiry_date",
        "auto_dns_configured", "ssl_provisioned",
    }
    assert set(data.keys()) == expected_keys
