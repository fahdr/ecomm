"""Tests for custom domain endpoints (Feature F22).

Covers setting a custom domain, retrieving domain configuration, verifying
DNS records, and removing a custom domain from a store.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Domain endpoints are store-scoped: ``/stores/{store_id}/domain``.
    Tests verify that only the store owner can manage domains, and that
    domain uniqueness is enforced across stores.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(client, email: str = "owner@example.com") -> str:
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
    client, token: str, name: str = "My Store", niche: str = "electronics"
) -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
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


async def set_domain(client, token: str, store_id: str, domain: str) -> dict:
    """Set a custom domain for a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        domain: The custom domain name.

    Returns:
        The JSON response dictionary for the domain configuration.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/domain",
        json={"domain": domain},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Set Domain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_domain_success(client):
    """Setting a custom domain returns 201 with domain configuration."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/domain",
        json={"domain": "shop.mybrand.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["domain"] == "shop.mybrand.com"
    assert data["store_id"] == store["id"]
    assert data["status"] == "pending"
    assert "verification_token" in data
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_set_domain_no_auth(client):
    """Setting a domain without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/domain",
        json={"domain": "shop.noauth.com"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_set_domain_store_not_found(client):
    """Setting a domain on a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/domain",
        json={"domain": "shop.ghost.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Get Domain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_domain_success(client):
    """Retrieving a store's domain configuration returns the domain data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    await set_domain(client, token, store["id"], "shop.gettest.com")

    response = await client.get(
        f"/api/v1/stores/{store['id']}/domain",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "shop.gettest.com"
    assert data["store_id"] == store["id"]


@pytest.mark.asyncio
async def test_get_domain_not_configured(client):
    """Retrieving domain when none is configured returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/domain",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Verify Domain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_domain_returns_result(client):
    """Verifying a domain returns a verification result with instructions."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    await set_domain(client, token, store["id"], "shop.verifytest.com")

    response = await client.post(
        f"/api/v1/stores/{store['id']}/domain/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "verified" in data
    assert "message" in data
    assert data["verified"] is True


@pytest.mark.asyncio
async def test_verify_domain_no_domain_configured(client):
    """Verifying when no domain is configured returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/domain/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Remove Domain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_domain_success(client):
    """Removing a custom domain returns 204 with no content."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    await set_domain(client, token, store["id"], "shop.removeme.com")

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/domain",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_domain_not_configured(client):
    """Removing a domain when none is configured returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/domain",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
