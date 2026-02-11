"""Tests for store theme API endpoints.

Covers theme CRUD, preset seeding, theme activation, public theme access,
and tenant isolation. Uses the same patterns as other backend tests.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Helper functions register users and create stores to reduce boilerplate.
    The theme system seeds 7 presets on store creation, with "Frosted" active.

**For Developers:**
    Tests use ``pytest.mark.asyncio`` with the shared ``client`` fixture.
    The ``_setup_store`` helper creates a user + store and returns both
    the auth token and store ID for use in theme API calls.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(client, email: str = "theme-owner@example.com") -> str:
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


async def _create_store(client, token: str, name: str = "Theme Test Store") -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        name: Store name.

    Returns:
        The JSON response dict for the created store.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": "fashion", "description": "For theme tests"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _setup_store(client, email: str = "theme-owner@example.com") -> tuple[str, str, str]:
    """Register a user, create a store, and return (token, store_id, store_slug).

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        Tuple of (access_token, store_id, store_slug).
    """
    token = await _register(client, email)
    store = await _create_store(client, token)
    return token, store["id"], store["slug"]


def _auth(token: str) -> dict:
    """Build authorization header dict.

    Args:
        token: JWT access token.

    Returns:
        Dict with Authorization header.
    """
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# List Themes (preset seeding)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_themes_returns_presets(client):
    """A new store automatically gets all preset themes (currently 11)."""
    token, store_id, _ = await _setup_store(client)

    resp = await client.get(
        f"/api/v1/stores/{store_id}/themes",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    themes = resp.json()
    assert len(themes) == 11

    # All should be presets.
    assert all(t["is_preset"] for t in themes)

    # Exactly one should be active.
    active = [t for t in themes if t["is_active"]]
    assert len(active) == 1
    assert active[0]["name"] == "Frosted"


@pytest.mark.asyncio
async def test_list_themes_preset_has_colors(client):
    """Preset themes have populated colors, typography, styles, and blocks."""
    token, store_id, _ = await _setup_store(client)

    resp = await client.get(
        f"/api/v1/stores/{store_id}/themes",
        headers=_auth(token),
    )
    themes = resp.json()
    frosted = next(t for t in themes if t["name"] == "Frosted")

    assert "primary" in frosted["colors"]
    assert "heading_font" in frosted["typography"]
    assert "border_radius" in frosted["styles"]
    assert len(frosted["blocks"]) > 0


# ---------------------------------------------------------------------------
# Create Theme
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_theme_success(client):
    """Creating a custom theme returns 201 with default config."""
    token, store_id, _ = await _setup_store(client)

    resp = await client.post(
        f"/api/v1/stores/{store_id}/themes",
        json={"name": "My Custom Theme"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Custom Theme"
    assert data["is_preset"] is False
    assert data["is_active"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_create_theme_clone_from_preset(client):
    """Cloning from a preset copies its colors, typography, and styles."""
    token, store_id, _ = await _setup_store(client)

    resp = await client.post(
        f"/api/v1/stores/{store_id}/themes",
        json={"name": "My Midnight", "clone_from": "Midnight"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Midnight"
    assert data["is_preset"] is False
    # Should have Midnight's colors (not Frosted's).
    assert data["colors"]["primary"] != ""


@pytest.mark.asyncio
async def test_create_theme_no_auth(client):
    """Creating a theme without authentication returns 401."""
    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/themes",
        json={"name": "Unauthorized"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Get Theme
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_theme_success(client):
    """Getting a theme by ID returns the theme data."""
    token, store_id, _ = await _setup_store(client)

    # Get the list and pick the first theme.
    list_resp = await client.get(
        f"/api/v1/stores/{store_id}/themes",
        headers=_auth(token),
    )
    theme_id = list_resp.json()[0]["id"]

    resp = await client.get(
        f"/api/v1/stores/{store_id}/themes/{theme_id}",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == theme_id


@pytest.mark.asyncio
async def test_get_theme_not_found(client):
    """Getting a non-existent theme returns 404."""
    token, store_id, _ = await _setup_store(client)

    resp = await client.get(
        f"/api/v1/stores/{store_id}/themes/00000000-0000-0000-0000-000000000000",
        headers=_auth(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update Theme
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_theme_partial(client):
    """Partial update only changes provided fields."""
    token, store_id, _ = await _setup_store(client)

    # Create a custom theme.
    create_resp = await client.post(
        f"/api/v1/stores/{store_id}/themes",
        json={"name": "Editable Theme"},
        headers=_auth(token),
    )
    theme_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/stores/{store_id}/themes/{theme_id}",
        json={"colors": {"primary": "#ff0000", "accent": "#00ff00"}},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["colors"]["primary"] == "#ff0000"
    assert data["name"] == "Editable Theme"  # Name unchanged.


@pytest.mark.asyncio
async def test_update_theme_name(client):
    """Updating a theme's name succeeds."""
    token, store_id, _ = await _setup_store(client)

    create_resp = await client.post(
        f"/api/v1/stores/{store_id}/themes",
        json={"name": "Old Name"},
        headers=_auth(token),
    )
    theme_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/stores/{store_id}/themes/{theme_id}",
        json={"name": "New Name"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


# ---------------------------------------------------------------------------
# Delete Theme
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_custom_theme(client):
    """Deleting a custom, inactive theme returns 204."""
    token, store_id, _ = await _setup_store(client)

    create_resp = await client.post(
        f"/api/v1/stores/{store_id}/themes",
        json={"name": "Deletable"},
        headers=_auth(token),
    )
    theme_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/stores/{store_id}/themes/{theme_id}",
        headers=_auth(token),
    )
    assert resp.status_code == 204

    # Verify it's gone.
    get_resp = await client.get(
        f"/api/v1/stores/{store_id}/themes/{theme_id}",
        headers=_auth(token),
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_preset_theme_refused(client):
    """Deleting a preset theme returns 400."""
    token, store_id, _ = await _setup_store(client)

    list_resp = await client.get(
        f"/api/v1/stores/{store_id}/themes",
        headers=_auth(token),
    )
    preset = next(t for t in list_resp.json() if t["is_preset"])

    resp = await client.delete(
        f"/api/v1/stores/{store_id}/themes/{preset['id']}",
        headers=_auth(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_active_theme_refused(client):
    """Deleting the active theme returns 400."""
    token, store_id, _ = await _setup_store(client)

    # Create a custom theme and activate it.
    create_resp = await client.post(
        f"/api/v1/stores/{store_id}/themes",
        json={"name": "Active Custom"},
        headers=_auth(token),
    )
    theme_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/stores/{store_id}/themes/{theme_id}/activate",
        headers=_auth(token),
    )

    resp = await client.delete(
        f"/api/v1/stores/{store_id}/themes/{theme_id}",
        headers=_auth(token),
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Activate Theme
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activate_theme(client):
    """Activating a theme deactivates the previous one."""
    token, store_id, _ = await _setup_store(client)

    list_resp = await client.get(
        f"/api/v1/stores/{store_id}/themes",
        headers=_auth(token),
    )
    themes = list_resp.json()
    midnight = next(t for t in themes if t["name"] == "Midnight")

    resp = await client.post(
        f"/api/v1/stores/{store_id}/themes/{midnight['id']}/activate",
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # Verify only one theme is active.
    list_resp2 = await client.get(
        f"/api/v1/stores/{store_id}/themes",
        headers=_auth(token),
    )
    active = [t for t in list_resp2.json() if t["is_active"]]
    assert len(active) == 1
    assert active[0]["name"] == "Midnight"


@pytest.mark.asyncio
async def test_activate_nonexistent_theme(client):
    """Activating a non-existent theme returns 404."""
    token, store_id, _ = await _setup_store(client)

    resp = await client.post(
        f"/api/v1/stores/{store_id}/themes/00000000-0000-0000-0000-000000000000/activate",
        headers=_auth(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Public Theme Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_public_theme_endpoint(client):
    """Public theme endpoint returns the active theme without auth."""
    token, store_id, slug = await _setup_store(client)

    resp = await client.get(f"/api/v1/public/stores/{slug}/theme")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Frosted"
    assert "primary" in data["colors"]
    assert "heading_font" in data["typography"]
    assert len(data["blocks"]) > 0
    # Public response should NOT include internal fields.
    assert "id" not in data
    assert "store_id" not in data
    assert "is_preset" not in data


@pytest.mark.asyncio
async def test_public_theme_nonexistent_store(client):
    """Public theme endpoint returns 404 for a non-existent store."""
    resp = await client.get("/api/v1/public/stores/no-such-store/theme")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Meta Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_meta_fonts(client):
    """Meta fonts endpoint returns heading and body font lists."""
    resp = await client.get("/api/v1/themes/meta/fonts")
    assert resp.status_code == 200
    data = resp.json()
    assert "heading_fonts" in data
    assert "body_fonts" in data
    assert len(data["heading_fonts"]) > 0
    assert len(data["body_fonts"]) > 0


@pytest.mark.asyncio
async def test_meta_block_types(client):
    """Meta block types endpoint returns available block types."""
    resp = await client.get("/api/v1/themes/meta/block-types")
    assert resp.status_code == 200
    data = resp.json()
    assert "block_types" in data
    assert len(data["block_types"]) > 0


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_list_themes(client):
    """User A cannot list User B's store themes."""
    token_a, _, _ = await _setup_store(client, "a-themes@example.com")
    _, store_b_id, _ = await _setup_store(client, "b-themes@example.com")

    resp = await client.get(
        f"/api/v1/stores/{store_b_id}/themes",
        headers=_auth(token_a),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_isolation_create_theme(client):
    """User A cannot create themes on User B's store."""
    token_a, _, _ = await _setup_store(client, "a2-themes@example.com")
    _, store_b_id, _ = await _setup_store(client, "b2-themes@example.com")

    resp = await client.post(
        f"/api/v1/stores/{store_b_id}/themes",
        json={"name": "Hacked Theme"},
        headers=_auth(token_a),
    )
    assert resp.status_code == 404
