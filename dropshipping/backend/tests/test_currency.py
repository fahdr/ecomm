"""Tests for currency endpoints (Feature F21).

Covers listing supported currencies, converting between currencies,
getting store currency settings, and updating store currency settings.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    The ``/currencies`` list endpoint is public (no auth required).
    The ``/currencies/convert`` endpoint requires authentication.
    Store currency settings are scoped to ``/stores/{store_id}/currency``.
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


# ---------------------------------------------------------------------------
# List Currencies (Public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_currencies_public(client):
    """Listing currencies does not require auth and returns supported currencies."""
    response = await client.get("/api/v1/currencies")
    assert response.status_code == 200
    data = response.json()
    assert "currencies" in data
    assert isinstance(data["currencies"], list)
    # Should have at least USD in the supported currencies.
    if len(data["currencies"]) > 0:
        currency = data["currencies"][0]
        assert "code" in currency
        assert "name" in currency
        assert "symbol" in currency


# ---------------------------------------------------------------------------
# Convert Currency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_convert_currency_success(client):
    """Converting between currencies returns the converted amount and rate."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/currencies/convert",
        json={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "EUR",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "original_amount" in data
    assert "converted_amount" in data
    assert "original_currency" in data
    assert "target_currency" in data
    assert "rate" in data
    assert data["original_currency"] == "USD"
    assert data["target_currency"] == "EUR"


@pytest.mark.asyncio
async def test_convert_currency_no_auth(client):
    """Converting currencies without authentication returns 401."""
    response = await client.post(
        "/api/v1/currencies/convert",
        json={
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "EUR",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_convert_currency_same_currency(client):
    """Converting same currency to itself returns the same amount."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/currencies/convert",
        json={
            "amount": 50,
            "from_currency": "USD",
            "to_currency": "USD",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Same currency: converted amount should equal original.
    assert float(data["converted_amount"]) == float(data["original_amount"])


# ---------------------------------------------------------------------------
# Get Store Currency Settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_store_currency_settings(client):
    """Getting store currency settings returns the base currency config."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/currency",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["store_id"] == store["id"]
    assert "base_currency" in data
    assert "display_currencies" in data
    assert "auto_convert" in data
    assert "rounding_method" in data


@pytest.mark.asyncio
async def test_get_store_currency_no_auth(client):
    """Getting store currency settings without auth returns 401."""
    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/currency",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_store_currency_store_not_found(client):
    """Getting currency settings for a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/currency",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Update Store Currency Settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_store_currency_settings(client):
    """Updating store currency settings applies the changes."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/currency",
        json={
            "base_currency": "EUR",
            "auto_convert": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["base_currency"] == "EUR"
    assert data["auto_convert"] is True


@pytest.mark.asyncio
async def test_update_store_currency_store_not_found(client):
    """Updating currency settings for a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.patch(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/currency",
        json={"base_currency": "GBP"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Exchange Rates Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_exchange_rates_success(client):
    """Getting exchange rates returns base, rates dict, and updated_at."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/currencies/rates",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["base"] == "USD"
    assert isinstance(data["rates"], dict)
    assert "USD" in data["rates"]
    assert "EUR" in data["rates"]
    assert data["rates"]["USD"] == 1.0
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_exchange_rates_no_auth(client):
    """Getting exchange rates without authentication returns 401."""
    response = await client.get("/api/v1/currencies/rates")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_store_currency_persists(client):
    """Updating currency to EUR persists on subsequent GET."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Update to EUR
    await client.patch(
        f"/api/v1/stores/{store['id']}/currency",
        json={"base_currency": "EUR"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Verify persistence
    response = await client.get(
        f"/api/v1/stores/{store['id']}/currency",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["base_currency"] == "EUR"
