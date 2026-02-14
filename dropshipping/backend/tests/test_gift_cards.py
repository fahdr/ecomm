"""Tests for gift card endpoints (Feature 20 - Gift Cards).

Covers creating, listing, validating, and disabling gift cards.
All endpoints require authentication and enforce store ownership.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Gift card routes are at ``/api/v1/stores/{store_id}/gift-cards/...``.
    POST create returns 201 with auto-generated or custom code.
    Validate endpoint checks balance, expiry, and active status.
    Disabled gift cards cannot be used for purchases.
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


async def create_test_gift_card(
    client,
    token: str,
    store_id: str,
    initial_balance: float = 50.0,
) -> dict:
    """Create a gift card and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        initial_balance: Starting balance for the gift card.

    Returns:
        The JSON response dictionary for the created gift card.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/gift-cards",
        json={"initial_balance": initial_balance},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create Gift Card
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_gift_card_success(client):
    """Creating a gift card returns 201 with auto-generated code and balance."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards",
        json={
            "initial_balance": 100.0,
            "customer_email": "customer@example.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert float(data["initial_balance"]) == 100.0
    assert float(data["current_balance"]) == 100.0
    assert data["status"] == "active"
    assert data["store_id"] == store["id"]
    assert data["customer_email"] == "customer@example.com"
    assert "code" in data
    assert len(data["code"]) > 0
    assert "id" in data


@pytest.mark.asyncio
async def test_create_gift_card_auto_code(client):
    """Creating a gift card auto-generates a unique code in GC-XXXX-XXXX-XXXX format."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards",
        json={"initial_balance": 25.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    code = response.json()["code"]
    assert code.startswith("GC-")
    assert len(code) == 17  # GC-XXXX-XXXX-XXXX (3+4+1+4+1+4)


@pytest.mark.asyncio
async def test_create_gift_card_no_auth(client):
    """Creating a gift card without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/gift-cards",
        json={"initial_balance": 50.0},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List Gift Cards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_gift_cards_success(client):
    """Listing gift cards returns paginated results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_gift_card(client, token, store["id"], initial_balance=50.0)
    await create_test_gift_card(client, token, store["id"], initial_balance=100.0)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/gift-cards",
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
async def test_list_gift_cards_empty(client):
    """Listing gift cards with none returns an empty paginated result."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/gift-cards",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------------------
# Validate Gift Card
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_gift_card_valid(client):
    """Validating a valid gift card returns valid=True with balance."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    card = await create_test_gift_card(
        client, token, store["id"], initial_balance=75.0
    )

    response = await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards/validate",
        json={"code": card["code"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert float(data["balance"]) == 75.0
    assert "message" in data


@pytest.mark.asyncio
async def test_validate_gift_card_invalid_code(client):
    """Validating a non-existent gift card code returns valid=False."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards/validate",
        json={"code": "NONEXISTENT-CODE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "message" in data


# ---------------------------------------------------------------------------
# Disable Gift Card
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disable_gift_card_success(client):
    """Disabling a gift card sets is_active to False."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    card = await create_test_gift_card(client, token, store["id"])

    response = await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards/{card['id']}/disable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disabled"
    assert data["id"] == card["id"]


@pytest.mark.asyncio
async def test_disable_gift_card_already_disabled(client):
    """Disabling an already disabled gift card returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    card = await create_test_gift_card(client, token, store["id"])

    # Disable once.
    await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards/{card['id']}/disable",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Attempt to disable again.
    response = await client.post(
        f"/api/v1/stores/{store['id']}/gift-cards/{card['id']}/disable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
