"""Tests for tax rate CRUD and tax calculation endpoints (Feature 16 - Tax).

Covers creating, listing, updating, deleting tax rates, and calculating
tax for a cart. All endpoints require authentication and enforce store
ownership.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Tax rates are scoped to a store. The calculation endpoint applies
    matching tax rates to cart items based on country/state. DELETE returns
    204 with no content body.
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


async def create_test_tax_rate(
    client,
    token: str,
    store_id: str,
    name: str = "US Sales Tax",
    country: str = "US",
    state: str | None = None,
    rate: float = 8.25,
) -> dict:
    """Create a tax rate and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        name: Tax rate display name.
        country: ISO 3166-1 alpha-2 country code.
        state: Optional state/province code.
        rate: Tax rate as a percentage.

    Returns:
        The JSON response dictionary for the created tax rate.
    """
    payload = {
        "name": name,
        "country": country,
        "rate": rate,
    }
    if state is not None:
        payload["state"] = state
    resp = await client.post(
        f"/api/v1/stores/{store_id}/tax-rates",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Tax Rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tax_rate_success(client):
    """Creating a tax rate returns 201 with the tax rate data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/tax-rates",
        json={
            "name": "California Sales Tax",
            "country": "US",
            "state": "CA",
            "rate": 7.25,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "California Sales Tax"
    assert data["country"] == "US"
    assert data["state"] == "CA"
    assert float(data["rate"]) == 7.25
    assert data["is_inclusive"] is False
    assert data["store_id"] == store["id"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_tax_rate_no_auth(client):
    """Creating a tax rate without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/tax-rates",
        json={"name": "VAT", "country": "GB", "rate": 20.0},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List Tax Rates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tax_rates_success(client):
    """Listing tax rates returns paginated results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_tax_rate(client, token, store["id"], name="US Tax", country="US")
    await create_test_tax_rate(client, token, store["id"], name="UK VAT", country="GB", rate=20.0)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/tax-rates",
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
async def test_list_tax_rates_empty(client):
    """Listing tax rates with none returns an empty paginated result."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/tax-rates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Update Tax Rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_tax_rate_success(client):
    """Updating a tax rate changes the specified fields."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    tax_rate = await create_test_tax_rate(client, token, store["id"])

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/tax-rates/{tax_rate['id']}",
        json={"name": "Updated Tax", "rate": 9.5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Tax"
    assert float(data["rate"]) == 9.5


@pytest.mark.asyncio
async def test_update_tax_rate_not_found(client):
    """Updating a non-existent tax rate returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/tax-rates/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost Rate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Tax Rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_tax_rate_success(client):
    """Deleting a tax rate returns 204 and removes it from the list."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    tax_rate = await create_test_tax_rate(client, token, store["id"])

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/tax-rates/{tax_rate['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Confirm it was removed from the list.
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/tax-rates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_tax_rate_not_found(client):
    """Deleting a non-existent tax rate returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/tax-rates/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Calculate Tax
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_tax_success(client):
    """Calculating tax applies matching rates and returns breakdown."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Create a US tax rate.
    await create_test_tax_rate(
        client, token, store["id"], name="US Tax", country="US", rate=10.0
    )

    response = await client.post(
        f"/api/v1/stores/{store['id']}/tax/calculate",
        json={
            "country": "US",
            "items": [
                {
                    "product_id": "00000000-0000-0000-0000-000000000001",
                    "quantity": 2,
                    "unit_price": 50.0,
                }
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "subtotal" in data
    assert "tax_total" in data
    assert "total" in data
    assert "line_items" in data
    assert "applied_rates" in data


@pytest.mark.asyncio
async def test_calculate_tax_no_auth(client):
    """Calculating tax without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/tax/calculate",
        json={
            "country": "US",
            "items": [
                {
                    "product_id": "00000000-0000-0000-0000-000000000001",
                    "quantity": 1,
                    "unit_price": 10.0,
                }
            ],
        },
    )
    assert response.status_code == 401
