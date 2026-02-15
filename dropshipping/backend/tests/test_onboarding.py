"""Tests for the onboarding checklist endpoint.

Verifies that the onboarding checklist correctly reflects a user's progress
through the key setup milestones: creating a store, adding products,
customizing a theme, connecting a domain, and receiving an order.

**For Developers:**
    Uses the standard test helpers to register users, create stores, and
    add products. The conftest.py schema-based isolation ensures each test
    starts with a clean database.

**For QA Engineers:**
    - A new user with no stores should see 0% completion (all false).
    - A user with a store should see 20% (1 of 5 steps).
    - A user with a store and products should see 40% (2 of 5 steps).
    - The endpoint requires authentication (401 without token).
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(
    client, email: str = "onboard@example.com"
) -> str:
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
    assert resp.status_code in (200, 201), f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


async def create_test_store(
    client, token: str, name: str = "Onboard Store", niche: str = "general"
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
    assert resp.status_code == 201, f"Store creation failed: {resp.text}"
    return resp.json()


async def create_test_product(
    client,
    token: str,
    store_id: str,
    title: str = "Test Product",
    price: float = 19.99,
) -> dict:
    """Create a product in the given store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.

    Returns:
        The JSON response dictionary for the created product.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json={"title": title, "price": price},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Product creation failed: {resp.text}"
    return resp.json()


async def get_checklist(client, token: str) -> dict:
    """Fetch the onboarding checklist for the authenticated user.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.

    Returns:
        The JSON response dictionary with checklist data.
    """
    resp = await client.get(
        "/api/v1/onboarding/checklist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Checklist fetch failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checklist_requires_auth(client):
    """GET /onboarding/checklist without a token returns 401."""
    resp = await client.get("/api/v1/onboarding/checklist")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Checklist Progress Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checklist_no_stores(client):
    """A new user with no stores sees all steps as false and 0% completion."""
    token = await register_and_get_token(client, email="new@example.com")

    data = await get_checklist(client, token)

    # All steps should be false
    assert data["checklist"]["create_store"]["done"] is False
    assert data["checklist"]["add_products"]["done"] is False
    assert data["checklist"]["customize_theme"]["done"] is False
    assert data["checklist"]["connect_domain"]["done"] is False
    assert data["checklist"]["first_order"]["done"] is False

    # Completion metrics
    assert data["completed"] == 0
    assert data["total"] == 5
    assert data["completion_percentage"] == 0


@pytest.mark.asyncio
async def test_checklist_with_store_only(client):
    """A user with a store but nothing else sees 20% completion."""
    token = await register_and_get_token(client, email="store@example.com")
    await create_test_store(client, token)

    data = await get_checklist(client, token)

    # create_store + customize_theme are done (store creation auto-creates a theme)
    assert data["checklist"]["create_store"]["done"] is True
    assert data["checklist"]["add_products"]["done"] is False
    assert data["checklist"]["customize_theme"]["done"] is True
    assert data["checklist"]["connect_domain"]["done"] is False
    assert data["checklist"]["first_order"]["done"] is False

    assert data["completed"] == 2
    assert data["total"] == 5
    assert data["completion_percentage"] == 40


@pytest.mark.asyncio
async def test_checklist_with_store_and_products(client):
    """A user with a store and products sees 60% completion."""
    token = await register_and_get_token(client, email="products@example.com")
    store = await create_test_store(client, token)
    await create_test_product(client, token, store["id"], title="Widget A")

    data = await get_checklist(client, token)

    # create_store, add_products, and customize_theme done (auto-created theme)
    assert data["checklist"]["create_store"]["done"] is True
    assert data["checklist"]["add_products"]["done"] is True
    assert data["checklist"]["customize_theme"]["done"] is True
    assert data["checklist"]["connect_domain"]["done"] is False
    assert data["checklist"]["first_order"]["done"] is False

    assert data["completed"] == 3
    assert data["total"] == 5
    assert data["completion_percentage"] == 60


@pytest.mark.asyncio
async def test_checklist_response_structure(client):
    """The checklist response has the expected shape and labels."""
    token = await register_and_get_token(client, email="struct@example.com")

    data = await get_checklist(client, token)

    # Verify all expected keys exist
    assert "checklist" in data
    assert "completed" in data
    assert "total" in data
    assert "completion_percentage" in data

    # Verify checklist steps
    checklist = data["checklist"]
    expected_steps = [
        "create_store",
        "add_products",
        "customize_theme",
        "connect_domain",
        "first_order",
    ]
    for step in expected_steps:
        assert step in checklist
        assert "done" in checklist[step]
        assert "label" in checklist[step]
        assert isinstance(checklist[step]["done"], bool)
        assert isinstance(checklist[step]["label"], str)

    # Labels should be human-readable
    assert checklist["create_store"]["label"] == "Create your first store"
    assert checklist["add_products"]["label"] == "Add your first product"
    assert checklist["customize_theme"]["label"] == "Customize your store theme"
    assert checklist["connect_domain"]["label"] == "Connect a custom domain"
    assert checklist["first_order"]["label"] == "Receive your first order"
