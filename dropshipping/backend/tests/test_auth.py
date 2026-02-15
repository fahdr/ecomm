"""Tests for authentication endpoints.

Covers user registration, login, token refresh, forgot-password (stubbed),
and the ``/auth/me`` protected endpoint.

**For QA Engineers:**
    Each test is independent — the database is reset between tests. Tests
    exercise both happy paths and error cases (duplicate email, wrong
    password, invalid tokens, missing auth).
"""

import pytest


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client):
    """Register a new user and receive access + refresh tokens."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "securepass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering with an existing email returns 409 Conflict."""
    payload = {"email": "dup@example.com", "password": "securepass123"}
    await client.post("/api/v1/auth/register", json=payload)

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(client):
    """Password shorter than 8 characters returns 422 validation error."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    """Invalid email format returns 422 validation error."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "securepass123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client):
    """Login with valid credentials returns tokens."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "securepass123"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Login with wrong password returns 401."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "securepass123"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Login with a non-existent email returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "securepass123"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(client):
    """Refreshing with a valid refresh token returns new tokens."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "securepass123"},
    )
    refresh_token = reg.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    """Refreshing with an invalid token returns 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.jwt.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token(client):
    """Using an access token for refresh returns 401 (wrong token type)."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongtype@example.com", "password": "securepass123"},
    )
    access_token = reg.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Get Current User (/me)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_success(client):
    """Authenticated request to /me returns user profile."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "securepass123"},
    )
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_me_no_token(client):
    """Request to /me without a token returns 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    """Request to /me with an invalid token returns 401."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_refresh_token(client):
    """Using a refresh token on /me returns 401 (wrong token type)."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "refreshme@example.com", "password": "securepass123"},
    )
    refresh_token = reg.json()["refresh_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Forgot Password (Stubbed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forgot_password(client):
    """Forgot-password always returns a success message (stubbed)."""
    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "forgot@example.com"},
    )
    assert response.status_code == 200
    assert "reset link" in response.json()["message"].lower()
