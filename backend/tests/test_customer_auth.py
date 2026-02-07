"""Tests for customer authentication endpoints.

Covers customer registration, login, token refresh, profile retrieval,
profile update, and token isolation (customer tokens vs user tokens).

**For QA Engineers:**
    Each test is independent. Tests exercise per-store customer isolation,
    ensuring the same email can register on different stores independently.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_store(client) -> dict:
    """Register a user, create a store, and return store data + user token."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "ownerpass123"},
    )
    token = reg.json()["access_token"]
    store_resp = await client.post(
        "/api/v1/stores",
        json={"name": "Test Store", "niche": "Electronics"},
        headers={"Authorization": f"Bearer {token}"},
    )
    store = store_resp.json()
    return {"store": store, "user_token": token, "slug": store["slug"]}


async def _create_second_store(client) -> dict:
    """Register a second user, create a store, return store data + token."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner2@example.com", "password": "ownerpass123"},
    )
    token = reg.json()["access_token"]
    store_resp = await client.post(
        "/api/v1/stores",
        json={"name": "Second Store", "niche": "Fashion"},
        headers={"Authorization": f"Bearer {token}"},
    )
    store = store_resp.json()
    return {"store": store, "user_token": token, "slug": store["slug"]}


async def _register_customer(client, slug: str) -> dict:
    """Register a customer on a store and return tokens."""
    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": "customer@test.com", "password": "customer123"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_register_success(client):
    """Register a new customer on a store and receive tokens."""
    setup = await _create_store(client)
    resp = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/auth/register",
        json={
            "email": "cust@example.com",
            "password": "password123",
            "first_name": "Jane",
            "last_name": "Doe",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_customer_register_duplicate_email_same_store(client):
    """Duplicate email on the same store returns 409."""
    setup = await _create_store(client)
    slug = setup["slug"]
    payload = {"email": "dup@example.com", "password": "password123"}
    await client.post(f"/api/v1/public/stores/{slug}/auth/register", json=payload)

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/register", json=payload
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_customer_register_same_email_different_store(client):
    """Same email on different stores is allowed (per-store isolation)."""
    setup1 = await _create_store(client)
    setup2 = await _create_second_store(client)

    payload = {"email": "shared@example.com", "password": "password123"}

    resp1 = await client.post(
        f"/api/v1/public/stores/{setup1['slug']}/auth/register", json=payload
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/v1/public/stores/{setup2['slug']}/auth/register", json=payload
    )
    assert resp2.status_code == 201


@pytest.mark.asyncio
async def test_customer_register_short_password(client):
    """Password < 8 chars returns 422."""
    setup = await _create_store(client)
    resp = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_customer_register_nonexistent_store(client):
    """Registering on a non-existent store returns 404."""
    resp = await client.post(
        "/api/v1/public/stores/nonexistent-store/auth/register",
        json={"email": "cust@example.com", "password": "password123"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_login_success(client):
    """Login with valid credentials returns tokens."""
    setup = await _create_store(client)
    slug = setup["slug"]
    await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_customer_login_wrong_password(client):
    """Wrong password returns 401."""
    setup = await _create_store(client)
    slug = setup["slug"]
    await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/login",
        json={"email": "login@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_customer_login_wrong_store(client):
    """Customer registered on store A cannot login on store B."""
    setup1 = await _create_store(client)
    setup2 = await _create_second_store(client)

    await client.post(
        f"/api/v1/public/stores/{setup1['slug']}/auth/register",
        json={"email": "onlya@example.com", "password": "password123"},
    )

    resp = await client.post(
        f"/api/v1/public/stores/{setup2['slug']}/auth/login",
        json={"email": "onlya@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_refresh_success(client):
    """Refresh with a valid customer refresh token returns new tokens."""
    setup = await _create_store(client)
    slug = setup["slug"]
    reg = await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    refresh_token = reg.json()["refresh_token"]

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_customer_refresh_with_user_token(client):
    """Refreshing with a user (store owner) token returns 401."""
    setup = await _create_store(client)
    slug = setup["slug"]

    # Get user refresh token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "ownerpass123"},
    )
    user_refresh = login_resp.json()["refresh_token"]

    resp = await client.post(
        f"/api/v1/public/stores/{slug}/auth/refresh",
        json={"refresh_token": user_refresh},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Profile (GET /me, PATCH /me)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customer_me_success(client):
    """GET /me with valid customer token returns profile."""
    setup = await _create_store(client)
    slug = setup["slug"]
    reg = await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={
            "email": "me@example.com",
            "password": "password123",
            "first_name": "Jane",
        },
    )
    token = reg.json()["access_token"]

    resp = await client.get(
        f"/api/v1/public/stores/{slug}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@example.com"
    assert data["first_name"] == "Jane"


@pytest.mark.asyncio
async def test_customer_me_no_token(client):
    """GET /me without token returns 401."""
    setup = await _create_store(client)
    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/auth/me",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_customer_update_profile(client):
    """PATCH /me updates customer profile fields."""
    setup = await _create_store(client)
    slug = setup["slug"]
    reg = await client.post(
        f"/api/v1/public/stores/{slug}/auth/register",
        json={"email": "update@example.com", "password": "password123"},
    )
    token = reg.json()["access_token"]

    resp = await client.patch(
        f"/api/v1/public/stores/{slug}/auth/me",
        json={"first_name": "Updated", "phone": "+1234567890"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Updated"
    assert data["phone"] == "+1234567890"


# ---------------------------------------------------------------------------
# Token Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_token_rejected_on_customer_me(client):
    """User (store owner) token cannot access customer /me endpoint."""
    setup = await _create_store(client)
    resp = await client.get(
        f"/api/v1/public/stores/{setup['slug']}/auth/me",
        headers={"Authorization": f"Bearer {setup['user_token']}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_customer_token_rejected_on_user_me(client):
    """Customer token cannot access user /auth/me endpoint."""
    setup = await _create_store(client)
    reg = await client.post(
        f"/api/v1/public/stores/{setup['slug']}/auth/register",
        json={"email": "isolated@example.com", "password": "password123"},
    )
    customer_token = reg.json()["access_token"]

    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert resp.status_code == 401
