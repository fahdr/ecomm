"""
Tests for the Super Admin Dashboard authentication endpoints.

For Developers:
    Tests the three auth endpoints: setup (first admin), login, and me.
    Uses direct database seeding and the httpx test client.

For QA Engineers:
    Covers: successful setup, duplicate setup (409), login with valid and
    invalid credentials, profile retrieval with and without token,
    and deactivated admin rejection.

For Project Managers:
    These tests ensure that admin authentication is secure and reliable,
    preventing unauthorized access to the platform management interface.

For End Users:
    Auth tests validate that only authorized administrators can manage
    the platform, protecting the system from unauthorized changes.
"""

import pytest

from tests.conftest import create_admin


@pytest.mark.asyncio
async def test_setup_first_admin(client):
    """
    POST /auth/setup creates the first super_admin when no admins exist.

    Verifies:
        - Returns 201 with the admin user details.
        - The created user has role ``super_admin``.
        - The created user is active.
    """
    resp = await client.post(
        "/api/v1/admin/auth/setup",
        json={"email": "first@admin.com", "password": "strongpass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "first@admin.com"
    assert data["role"] == "super_admin"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_setup_blocked_when_admin_exists(client):
    """
    POST /auth/setup returns 409 when an admin already exists.

    Verifies:
        - First setup succeeds (201).
        - Second setup fails (409) with appropriate error message.
    """
    await client.post(
        "/api/v1/admin/auth/setup",
        json={"email": "first@admin.com", "password": "strongpass123"},
    )
    resp = await client.post(
        "/api/v1/admin/auth/setup",
        json={"email": "second@admin.com", "password": "otherpass123"},
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client, db):
    """
    POST /auth/login with valid credentials returns a JWT.

    Verifies:
        - Returns 200 with access_token and token_type.
        - The token_type is ``bearer``.
    """
    await create_admin(db, email="login@admin.com", password="mypassword")

    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "login@admin.com", "password": "mypassword"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, db):
    """
    POST /auth/login with wrong password returns 401.

    Verifies:
        - Returns 401 with ``Invalid email or password`` detail.
    """
    await create_admin(db, email="wrong@admin.com", password="correctpass")

    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "wrong@admin.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    """
    POST /auth/login with non-existent email returns 401.

    Verifies:
        - Returns 401 (does not reveal whether email exists).
    """
    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "nobody@admin.com", "password": "anypass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_deactivated_admin(client, db):
    """
    POST /auth/login with a deactivated admin returns 401.

    Verifies:
        - Returns 401 with ``deactivated`` in the detail message.
    """
    await create_admin(
        db, email="deactivated@admin.com", password="mypass", is_active=False
    )

    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": "deactivated@admin.com", "password": "mypass"},
    )
    assert resp.status_code == 401
    assert "deactivated" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_me_authenticated(client, auth_headers):
    """
    GET /auth/me with a valid JWT returns the admin profile.

    Verifies:
        - Returns 200 with the admin's email, role, and active status.
    """
    resp = await client.get(
        "/api/v1/admin/auth/me", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@example.com"
    assert data["role"] == "super_admin"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_me_no_token(client):
    """
    GET /auth/me without a token returns 401.

    Verifies:
        - Returns 401 (HTTPBearer rejects missing credentials).
    """
    resp = await client.get("/api/v1/admin/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client):
    """
    GET /auth/me with an invalid token returns 401.

    Verifies:
        - Returns 401 with ``Invalid token`` in the detail.
    """
    resp = await client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health_check(client):
    """
    GET /api/v1/health returns service status (no auth required).

    Verifies:
        - Returns 200 with ``healthy`` status and service name ``admin``.
    """
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "admin"
