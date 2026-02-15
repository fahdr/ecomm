"""Tests for discount CRUD and validation endpoints (Feature F8).

Covers discount creation, listing (pagination), retrieval by ID, update,
deletion, discount code validation, and expired discount handling.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Helper functions register users and create stores/discounts to reduce
    boilerplate. Tests verify CRUD operations, duplicate code rejection,
    and validation logic (valid code, expired code, minimum order amount).
"""

import pytest
from datetime import datetime, timedelta, timezone


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


async def create_test_discount(
    client,
    token: str,
    store_id: str,
    code: str = "SAVE20",
    discount_type: str = "percentage",
    value: float = 20.0,
    **kwargs,
) -> dict:
    """Create a discount and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        code: The coupon code string.
        discount_type: 'percentage' or 'fixed'.
        value: The discount value.
        **kwargs: Additional discount fields (expires_at, max_uses, etc.).

    Returns:
        The JSON response dictionary for the created discount.
    """
    if "starts_at" not in kwargs:
        kwargs["starts_at"] = datetime.now(timezone.utc).isoformat()
    data = {"code": code, "discount_type": discount_type, "value": value, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/discounts",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Discount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_discount_success(client):
    """Creating a discount returns 201 with the discount data and default active status."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    starts_at = datetime.now(timezone.utc).isoformat()
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/discounts",
        json={
            "code": "WELCOME10",
            "discount_type": "percentage",
            "value": 10.0,
            "minimum_order_amount": 50.0,
            "max_uses": 100,
            "starts_at": starts_at,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "WELCOME10"
    assert data["discount_type"] == "percentage"
    assert float(data["value"]) == 10.0
    assert float(data["minimum_order_amount"]) == 50.0
    assert data["max_uses"] == 100
    assert data["status"] == "active"
    assert data["times_used"] == 0
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_discount_duplicate_code(client):
    """Creating a discount with a duplicate code in the same store returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_discount(client, token, store["id"], code="DUPE")

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/discounts",
        json={"code": "DUPE", "discount_type": "fixed", "value": 5.0, "starts_at": datetime.now(timezone.utc).isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# List Discounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_discounts_pagination(client):
    """Listing discounts returns paginated results with correct metadata."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_discount(client, token, store["id"], code="CODE1")
    await create_test_discount(client, token, store["id"], code="CODE2")
    await create_test_discount(client, token, store["id"], code="CODE3")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/discounts?page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["pages"] == 2


# ---------------------------------------------------------------------------
# Get Discount by ID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_discount_by_id(client):
    """Retrieving a discount by ID returns the full discount data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    discount = await create_test_discount(client, token, store["id"])

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/discounts/{discount['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == discount["id"]
    assert data["code"] == "SAVE20"


@pytest.mark.asyncio
async def test_get_discount_not_found(client):
    """Retrieving a non-existent discount returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/discounts/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update Discount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_discount_success(client):
    """Updating a discount's value and status succeeds and reflects changes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    discount = await create_test_discount(client, token, store["id"])

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/discounts/{discount['id']}",
        json={"value": 30.0, "status": "disabled"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["value"]) == 30.0
    assert data["status"] == "disabled"


# ---------------------------------------------------------------------------
# Validate Discount Code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_discount_code_valid(client):
    """Validating a valid active discount code returns valid=true with computed amount."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    await create_test_discount(
        client, token, store["id"], code="TAKE20", discount_type="percentage", value=20.0
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/discounts/validate",
        json={"code": "TAKE20", "order_total": 100.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["message"] == "Discount applied successfully"
    assert data["discount_amount"] is not None


@pytest.mark.asyncio
async def test_validate_discount_code_expired(client):
    """Validating an expired discount code returns valid=false."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Create a discount that expired yesterday.
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    await create_test_discount(
        client,
        token,
        store["id"],
        code="OLDCODE",
        expires_at=yesterday,
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/discounts/validate",
        json={"code": "OLDCODE", "order_total": 100.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False


# ---------------------------------------------------------------------------
# Delete Discount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_discount_success(client):
    """Deleting a discount returns 204 and the discount is no longer retrievable."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    discount = await create_test_discount(client, token, store["id"])

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/discounts/{discount['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Verify it is gone.
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/discounts/{discount['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
