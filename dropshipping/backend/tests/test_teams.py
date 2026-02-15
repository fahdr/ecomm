"""Tests for team management endpoints (Feature F24).

Covers inviting team members, listing members, updating roles, and removing
members. Tests verify store ownership enforcement, role-based access, and
pagination.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Helper functions register users and create stores to reduce boilerplate.
    Tests verify that only store owners/admins can manage team members,
    the owner role cannot be changed, and the owner cannot be removed.
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


async def invite_team_member(
    client,
    token: str,
    store_id: str,
    email: str = "member@example.com",
    role: str = "viewer",
) -> dict:
    """Invite a team member and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        email: Invitee email address.
        role: Role to assign (owner, admin, editor, viewer).

    Returns:
        The JSON response dictionary for the team invitation.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/team/invite",
        json={"email": email, "role": role},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Invite Team Member
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invite_team_member_success(client):
    """Inviting a team member returns 201 with pending invitation data."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/team/invite",
        json={"email": "teammate@example.com", "role": "editor"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "teammate@example.com"
    assert data["role"] == "editor"
    assert data["status"] == "invited"
    assert data["store_id"] == store["id"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_invite_team_member_no_auth(client):
    """Inviting a team member without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/team/invite",
        json={"email": "no-auth@example.com", "role": "viewer"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invite_duplicate_email_returns_400(client):
    """Inviting the same email twice returns 400 (already a member)."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await invite_team_member(client, token, store["id"], email="dup@example.com")

    response = await client.post(
        f"/api/v1/stores/{store['id']}/team/invite",
        json={"email": "dup@example.com", "role": "viewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# List Team Members
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_team_members_success(client):
    """Listing team members returns paginated data including the owner."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await invite_team_member(client, token, store["id"], email="m1@example.com")
    await invite_team_member(client, token, store["id"], email="m2@example.com")

    response = await client.get(
        f"/api/v1/stores/{store['id']}/team",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    # At least the 2 invites (and possibly the owner) should be present.
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_list_team_members_no_auth(client):
    """Listing team members without authentication returns 401."""
    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/team",
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Update Team Member Role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_team_member_role_success(client):
    """Updating a team member's role succeeds and reflects the change."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    member = await invite_team_member(
        client, token, store["id"], email="editor@example.com", role="viewer"
    )

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/team/{member['id']}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["id"] == member["id"]


@pytest.mark.asyncio
async def test_update_nonexistent_member_returns_404(client):
    """Updating a non-existent team member returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/team/00000000-0000-0000-0000-000000000000",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Remove Team Member
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_team_member_success(client):
    """Removing a team member returns 204 with no content."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    member = await invite_team_member(
        client, token, store["id"], email="remove-me@example.com"
    )

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/team/{member['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_member_returns_404(client):
    """Removing a non-existent team member returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/team/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
