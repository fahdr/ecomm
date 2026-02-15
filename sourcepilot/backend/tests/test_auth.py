"""
Authentication endpoint tests.

For QA Engineers:
    Tests cover registration, login, token refresh, profile access,
    duplicate email handling, and invalid credentials.
"""

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """POST /auth/register creates a user and returns tokens."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """POST /auth/register with existing email returns 409."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password456"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """POST /auth/register with short password returns 422."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """POST /auth/login with valid credentials returns tokens."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """POST /auth/login with wrong password returns 401."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "password123"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """POST /auth/login with unknown email returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    """POST /auth/refresh with valid refresh token returns new tokens."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    refresh_token = reg_resp.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient):
    """POST /auth/refresh with access token (not refresh) returns 401."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "badrefresh@example.com", "password": "password123"},
    )
    access_token = reg_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient):
    """GET /auth/me returns user profile."""
    headers = await register_and_login(client, "profile@example.com")
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "profile@example.com"
    assert data["plan"] == "free"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient):
    """GET /auth/me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
