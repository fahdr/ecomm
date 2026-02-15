"""Tests for store CRUD endpoints.

Covers store creation, listing, retrieval, update, soft-delete, slug generation,
and tenant isolation (user A cannot access user B's stores).

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Helper functions register users and create stores to reduce boilerplate.
    Tenant isolation tests verify that one user cannot read, update, or
    delete another user's store.
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


async def upgrade_to_starter(client, token: str) -> None:
    """Subscribe the user to the starter plan (allows 3 stores).

    Used by tests that need to create more than 1 store.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
    """
    await client.post(
        "/api/v1/subscriptions/checkout",
        json={"plan": "starter"},
        headers={"Authorization": f"Bearer {token}"},
    )


async def create_test_store(client, token: str, name: str = "My Store", niche: str = "electronics") -> dict:
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
        json={"name": name, "niche": niche, "description": "A test store"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_store_success(client):
    """Creating a store returns 201 with store data and auto-generated slug."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores",
        json={"name": "My Awesome Store", "niche": "fashion", "description": "Trendy stuff"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Awesome Store"
    assert data["slug"] == "my-awesome-store"
    assert data["niche"] == "fashion"
    assert data["description"] == "Trendy stuff"
    assert data["status"] == "active"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_store_without_description(client):
    """Creating a store without a description succeeds (description is optional)."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores",
        json={"name": "Minimal Store", "niche": "tech"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.asyncio
async def test_create_store_duplicate_name_gets_unique_slug(client):
    """Two stores with the same name get different slugs (suffix appended)."""
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)

    store1 = await create_test_store(client, token, name="Cool Store")
    store2 = await create_test_store(client, token, name="Cool Store")

    assert store1["slug"] == "cool-store"
    assert store2["slug"] == "cool-store-2"


@pytest.mark.asyncio
async def test_create_store_no_auth(client):
    """Creating a store without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores",
        json={"name": "No Auth Store", "niche": "test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_store_missing_name(client):
    """Creating a store without a name returns 422 validation error."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores",
        json={"niche": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# List Stores
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_stores_success(client):
    """Listing stores returns all non-deleted stores for the user."""
    token = await register_and_get_token(client)
    await upgrade_to_starter(client, token)
    await create_test_store(client, token, name="Store A")
    await create_test_store(client, token, name="Store B")

    response = await client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_stores_empty(client):
    """Listing stores with no stores returns an empty list."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_stores_excludes_deleted(client):
    """Deleted stores are not included in the list response."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="To Delete")

    # Soft-delete the store.
    await client.delete(
        f"/api/v1/stores/{store['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


# ---------------------------------------------------------------------------
# Get Store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_store_success(client):
    """Retrieving a store by ID returns the store data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == store["id"]


@pytest.mark.asyncio
async def test_get_store_not_found(client):
    """Retrieving a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update Store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_store_success(client):
    """Updating a store's name and niche succeeds and reflects changes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}",
        json={"name": "Updated Store", "niche": "home-goods"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Store"
    assert data["niche"] == "home-goods"
    assert data["slug"] == "updated-store"


@pytest.mark.asyncio
async def test_update_store_partial(client):
    """Partial update — only the provided fields change."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Original Name")

    response = await client.patch(
        f"/api/v1/stores/{store['id']}",
        json={"description": "New description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Original Name"
    assert data["description"] == "New description"
    assert data["slug"] == "original-name"  # Slug unchanged since name unchanged.


@pytest.mark.asyncio
async def test_update_store_not_found(client):
    """Updating a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.patch(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Store (Soft Delete)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_store_success(client):
    """Soft-deleting a store sets its status to 'deleted'."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_delete_store_not_found(client):
    """Deleting a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.delete(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_deleted_store_returns_404(client):
    """A deleted store cannot be retrieved via GET."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await client.delete(
        f"/api/v1/stores/{store['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get(
        f"/api/v1/stores/{store['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_list(client):
    """User A cannot see User B's stores in the list endpoint."""
    token_a = await register_and_get_token(client, email="a@example.com")
    token_b = await register_and_get_token(client, email="b@example.com")

    await create_test_store(client, token_a, name="A's Store")
    await create_test_store(client, token_b, name="B's Store")

    response = await client.get(
        "/api/v1/stores",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    stores = response.json()
    assert len(stores) == 1
    assert stores[0]["name"] == "A's Store"


@pytest.mark.asyncio
async def test_tenant_isolation_get(client):
    """User A cannot retrieve User B's store by ID."""
    token_a = await register_and_get_token(client, email="a2@example.com")
    token_b = await register_and_get_token(client, email="b2@example.com")

    store_b = await create_test_store(client, token_b, name="B's Secret Store")

    response = await client.get(
        f"/api/v1/stores/{store_b['id']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_update(client):
    """User A cannot update User B's store."""
    token_a = await register_and_get_token(client, email="a3@example.com")
    token_b = await register_and_get_token(client, email="b3@example.com")

    store_b = await create_test_store(client, token_b, name="B's Store")

    response = await client.patch(
        f"/api/v1/stores/{store_b['id']}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_delete(client):
    """User A cannot delete User B's store."""
    token_a = await register_and_get_token(client, email="a4@example.com")
    token_b = await register_and_get_token(client, email="b4@example.com")

    store_b = await create_test_store(client, token_b, name="B's Store")

    response = await client.delete(
        f"/api/v1/stores/{store_b['id']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404
