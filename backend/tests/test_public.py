"""Tests for public (unauthenticated) API endpoints.

Covers the ``GET /api/v1/public/stores/{slug}`` endpoint used by the
storefront to resolve store data by slug without authentication.

**For Developers:**
    Tests create stores via the authenticated API first, then verify
    they are accessible via the public endpoint.

**For QA Engineers:**
    - Active stores are returned with public-facing fields only.
    - Paused and deleted stores return 404.
    - Unknown slugs return 404.
    - The ``user_id`` field must never appear in public responses.
"""

import pytest


async def register_and_get_token(client, email="user@example.com", password="testpass123"):
    """Register a user and return the access token.

    Args:
        client: The httpx AsyncClient.
        email: Email for registration.
        password: Password for registration.

    Returns:
        str: The JWT access token.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    return resp.json()["access_token"]


async def create_test_store(client, token, name="Test Store", niche="electronics"):
    """Create a store via the authenticated API and return the response data.

    Args:
        client: The httpx AsyncClient.
        token: JWT access token.
        name: Store name.
        niche: Store niche.

    Returns:
        dict: The store response data including slug, id, etc.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": niche, "description": "A test store"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# --- GET /api/v1/public/stores/{slug} ---


@pytest.mark.anyio
async def test_get_public_store_by_slug(client):
    """Active store should be accessible by slug without auth."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(f"/api/v1/public/stores/{store['slug']}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["name"] == "Test Store"
    assert data["slug"] == store["slug"]
    assert data["niche"] == "electronics"
    assert data["description"] == "A test store"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.anyio
async def test_public_store_excludes_user_id(client):
    """Public store response must not contain user_id."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(f"/api/v1/public/stores/{store['slug']}")
    assert resp.status_code == 200

    data = resp.json()
    assert "user_id" not in data


@pytest.mark.anyio
async def test_public_store_not_found_unknown_slug(client):
    """Unknown slug should return 404."""
    resp = await client.get("/api/v1/public/stores/nonexistent-store")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Store not found"


@pytest.mark.anyio
async def test_public_store_not_found_paused(client):
    """Paused stores should not be publicly accessible."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Pause the store
    await client.patch(
        f"/api/v1/stores/{store['id']}",
        json={"status": "paused"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(f"/api/v1/public/stores/{store['slug']}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_public_store_not_found_deleted(client):
    """Deleted stores should not be publicly accessible."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Soft-delete the store
    await client.delete(
        f"/api/v1/stores/{store['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(f"/api/v1/public/stores/{store['slug']}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_public_store_no_auth_required(client):
    """Public endpoint should work without any Authorization header."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Request without any auth header
    resp = await client.get(
        f"/api/v1/public/stores/{store['slug']}",
    )
    assert resp.status_code == 200
    assert resp.json()["slug"] == store["slug"]
