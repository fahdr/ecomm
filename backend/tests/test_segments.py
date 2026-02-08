"""Tests for customer segment endpoints (Feature 19 - Customer Segments).

Covers creating, listing, getting, updating, deleting segments, and
managing customer membership within segments. All endpoints require
authentication and enforce store ownership.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Segment routes are at ``/api/v1/stores/{store_id}/segments/...``.
    POST create returns 201, DELETE returns 204.
    Adding a customer to a segment is idempotent (duplicates are skipped).
    Segments can be ``manual`` (hand-picked) or ``auto`` (rule-based).
    Customer IDs reference platform users (``users.id``).
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


async def register_and_get_user(client, email: str = "owner@example.com") -> dict:
    """Register a user and return both the access token and user info.

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        A dict with ``token`` (access token string) and ``user``
        (user profile dict including ``id``).
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    data = resp.json()
    token = data["access_token"]
    # Fetch the user profile to get the user ID.
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"token": token, "user": me_resp.json()}


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


async def create_test_segment(
    client,
    token: str,
    store_id: str,
    name: str = "VIP Customers",
    segment_type: str = "manual",
) -> dict:
    """Create a segment and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        name: Segment display name.
        segment_type: Type of segment (manual or auto).

    Returns:
        The JSON response dictionary for the created segment.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/segments",
        json={"name": name, "segment_type": segment_type},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Segment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_segment_success(client):
    """Creating a segment returns 201 with the segment data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/segments",
        json={
            "name": "Repeat Buyers",
            "description": "Customers who purchased more than once",
            "segment_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Repeat Buyers"
    assert data["description"] == "Customers who purchased more than once"
    assert data["segment_type"] == "manual"
    assert data["store_id"] == store["id"]
    assert data["customer_count"] == 0
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_segment_no_auth(client):
    """Creating a segment without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/segments",
        json={"name": "Test Segment"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List Segments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_segments_success(client):
    """Listing segments returns paginated results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_segment(client, token, store["id"], name="Segment A")
    await create_test_segment(client, token, store["id"], name="Segment B")

    response = await client.get(
        f"/api/v1/stores/{store['id']}/segments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert "per_page" in data
    assert "pages" in data


@pytest.mark.asyncio
async def test_list_segments_empty(client):
    """Listing segments with none returns an empty paginated result."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/segments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Get Segment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_segment_success(client):
    """Retrieving a segment by ID returns the segment data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    segment = await create_test_segment(client, token, store["id"])

    response = await client.get(
        f"/api/v1/stores/{store['id']}/segments/{segment['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == segment["id"]
    assert data["name"] == segment["name"]


@pytest.mark.asyncio
async def test_get_segment_not_found(client):
    """Retrieving a non-existent segment returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/segments/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Segment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_segment_success(client):
    """Deleting a segment returns 204 and removes it from the list."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    segment = await create_test_segment(client, token, store["id"])

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/segments/{segment['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Confirm it was removed.
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/segments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Add Customers to Segment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_customers_to_segment_success(client):
    """Adding customers to a segment returns 201 with added count."""
    owner = await register_and_get_user(client, email="owner@example.com")
    customer = await register_and_get_user(client, email="customer@example.com")

    store = await create_test_store(client, owner["token"])
    segment = await create_test_segment(client, owner["token"], store["id"])

    response = await client.post(
        f"/api/v1/stores/{store['id']}/segments/{segment['id']}/customers",
        json={"customer_ids": [customer["user"]["id"]]},
        headers={"Authorization": f"Bearer {owner['token']}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["added"] == 1
    assert "message" in data


# ---------------------------------------------------------------------------
# Remove Customer from Segment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_customer_from_segment_success(client):
    """Removing a customer from a segment returns 204."""
    owner = await register_and_get_user(client, email="owner2@example.com")
    customer = await register_and_get_user(client, email="cust2@example.com")

    store = await create_test_store(client, owner["token"])
    segment = await create_test_segment(client, owner["token"], store["id"])

    # Add the customer first.
    await client.post(
        f"/api/v1/stores/{store['id']}/segments/{segment['id']}/customers",
        json={"customer_ids": [customer["user"]["id"]]},
        headers={"Authorization": f"Bearer {owner['token']}"},
    )

    # Remove the customer.
    response = await client.delete(
        f"/api/v1/stores/{store['id']}/segments/{segment['id']}/customers/{customer['user']['id']}",
        headers={"Authorization": f"Bearer {owner['token']}"},
    )
    assert response.status_code == 204
