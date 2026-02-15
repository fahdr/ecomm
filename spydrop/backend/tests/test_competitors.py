"""
Competitor CRUD and scanning endpoint tests.

Tests the full lifecycle of competitor management: creation, listing,
retrieval, updating, deletion, and plan limit enforcement. Also tests
the per-competitor product listing sub-resource.

For Developers:
    Each test uses the `client` and `auth_headers` fixtures from conftest.py.
    The `register_and_login` helper creates a fresh user with a JWT token.
    Tests run against the real database with table truncation between tests,
    ensuring full isolation.

For QA Engineers:
    These tests verify:
    - Competitor CRUD operations return correct status codes and payloads.
    - Plan limit enforcement prevents exceeding the free-tier limit of 3.
    - Authorization isolation: users cannot access other users' competitors.
    - Pagination works correctly for list endpoints.
    - Invalid IDs return 400, missing resources return 404.
    - Partial updates via PATCH only modify provided fields.

For Project Managers:
    Competitors are the core resource in SpyDrop. These tests ensure
    that the API contract is reliable and that billing-related plan
    limits are properly enforced.

For End Users:
    These tests guarantee that your competitor management actions
    (add, edit, pause, delete) work correctly and securely.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helper ──────────────────────────────────────────────────────────


async def create_competitor_via_api(
    client: AsyncClient,
    headers: dict,
    name: str = "Test Store",
    url: str = "https://teststore.example.com",
    platform: str = "shopify",
) -> dict:
    """
    Helper to create a competitor via the API and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Authorization headers with JWT token.
        name: Competitor store name.
        url: Competitor store URL.
        platform: E-commerce platform identifier.

    Returns:
        Dict containing the competitor response data.
    """
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": name, "url": url, "platform": platform},
        headers=headers,
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ── Create Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_competitor_success(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/competitors/ creates a competitor and returns 201 with correct fields."""
    data = await create_competitor_via_api(
        client,
        auth_headers,
        name="Rival Store",
        url="https://rival.example.com",
        platform="woocommerce",
    )

    assert data["name"] == "Rival Store"
    assert data["url"] == "https://rival.example.com"
    assert data["platform"] == "woocommerce"
    assert data["status"] == "active"
    assert data["product_count"] == 0
    assert data["last_scanned"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_competitor_default_platform(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/competitors/ with no platform defaults to 'custom'."""
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Custom Store", "url": "https://custom.example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "custom"


@pytest.mark.asyncio
async def test_create_competitor_missing_name_returns_422(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/competitors/ without a name returns 422 validation error."""
    resp = await client.post(
        "/api/v1/competitors/",
        json={"url": "https://noname.example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_competitor_missing_url_returns_422(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/competitors/ without a URL returns 422 validation error."""
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "No URL Store"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_competitor_empty_name_returns_422(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/competitors/ with empty string name returns 422."""
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "", "url": "https://empty.example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_competitor_unauthenticated_returns_401(client: AsyncClient):
    """POST /api/v1/competitors/ without auth returns 401."""
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "No Auth Store", "url": "https://noauth.example.com"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_competitor_plan_limit_free_tier(client: AsyncClient):
    """
    Free-tier users are limited to 3 competitors.

    Creating a 4th competitor should return 403 with a plan limit message.
    """
    headers = await register_and_login(client)

    # Create 3 competitors (at the free-tier limit)
    for i in range(3):
        await create_competitor_via_api(
            client, headers, name=f"Store {i}", url=f"https://store{i}.example.com"
        )

    # The 4th should be rejected
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Over Limit Store", "url": "https://overlimit.example.com"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "plan limit" in resp.json()["detail"].lower() or "limit" in resp.json()["detail"].lower()


# ── List Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_competitors_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/competitors/ returns empty list for new user."""
    resp = await client.get("/api/v1/competitors/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


@pytest.mark.asyncio
async def test_list_competitors_with_data(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/competitors/ returns competitors after creation."""
    await create_competitor_via_api(client, auth_headers, name="Store Alpha")
    await create_competitor_via_api(client, auth_headers, name="Store Beta")

    resp = await client.get("/api/v1/competitors/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    names = {item["name"] for item in data["items"]}
    assert "Store Alpha" in names
    assert "Store Beta" in names


@pytest.mark.asyncio
async def test_list_competitors_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/competitors/?page=1&per_page=1 returns paginated results."""
    await create_competitor_via_api(client, auth_headers, name="Page Store A")
    await create_competitor_via_api(client, auth_headers, name="Page Store B")

    # Page 1 with 1 item per page
    resp = await client.get(
        "/api/v1/competitors/?page=1&per_page=1", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["per_page"] == 1

    # Page 2
    resp2 = await client.get(
        "/api/v1/competitors/?page=2&per_page=1", headers=auth_headers
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["page"] == 2


@pytest.mark.asyncio
async def test_list_competitors_isolation(client: AsyncClient):
    """Users cannot see other users' competitors."""
    headers_a = await register_and_login(client, email="usera@example.com")
    headers_b = await register_and_login(client, email="userb@example.com")

    await create_competitor_via_api(client, headers_a, name="User A Store")

    # User B should see zero competitors
    resp = await client.get("/api/v1/competitors/", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Get Single Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_competitor_success(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/competitors/{id} returns the correct competitor."""
    created = await create_competitor_via_api(client, auth_headers, name="Get Test Store")
    competitor_id = created["id"]

    resp = await client.get(f"/api/v1/competitors/{competitor_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == competitor_id
    assert data["name"] == "Get Test Store"


@pytest.mark.asyncio
async def test_get_competitor_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/competitors/{id} with non-existent ID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/competitors/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_competitor_invalid_id_returns_400(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/competitors/{id} with invalid UUID returns 400."""
    resp = await client.get("/api/v1/competitors/not-a-uuid", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_competitor_wrong_user_returns_404(client: AsyncClient):
    """GET /api/v1/competitors/{id} returns 404 if owned by another user."""
    headers_owner = await register_and_login(client, email="owner@example.com")
    headers_other = await register_and_login(client, email="other@example.com")

    created = await create_competitor_via_api(client, headers_owner, name="Owner Store")
    competitor_id = created["id"]

    resp = await client.get(
        f"/api/v1/competitors/{competitor_id}", headers=headers_other
    )
    assert resp.status_code == 404


# ── Update Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_competitor_name(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/competitors/{id} can update the name."""
    created = await create_competitor_via_api(client, auth_headers, name="Old Name")
    competitor_id = created["id"]

    resp = await client.patch(
        f"/api/v1/competitors/{competitor_id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    # URL should remain unchanged
    assert data["url"] == created["url"]


@pytest.mark.asyncio
async def test_update_competitor_status(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/competitors/{id} can change status to 'paused'."""
    created = await create_competitor_via_api(client, auth_headers, name="Pause Test")
    competitor_id = created["id"]

    resp = await client.patch(
        f"/api/v1/competitors/{competitor_id}",
        json={"status": "paused"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_update_competitor_multiple_fields(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/competitors/{id} can update multiple fields at once."""
    created = await create_competitor_via_api(
        client, auth_headers, name="Multi Update", url="https://old.example.com"
    )
    competitor_id = created["id"]

    resp = await client.patch(
        f"/api/v1/competitors/{competitor_id}",
        json={"name": "Updated Multi", "url": "https://new.example.com", "platform": "woocommerce"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Multi"
    assert data["url"] == "https://new.example.com"
    assert data["platform"] == "woocommerce"


@pytest.mark.asyncio
async def test_update_competitor_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/competitors/{id} with non-existent ID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(
        f"/api/v1/competitors/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_competitor_wrong_user(client: AsyncClient):
    """PATCH /api/v1/competitors/{id} returns 404 if owned by another user."""
    headers_owner = await register_and_login(client, email="patchowner@example.com")
    headers_other = await register_and_login(client, email="patchother@example.com")

    created = await create_competitor_via_api(client, headers_owner, name="Private Store")
    competitor_id = created["id"]

    resp = await client.patch(
        f"/api/v1/competitors/{competitor_id}",
        json={"name": "Hacked Name"},
        headers=headers_other,
    )
    assert resp.status_code == 404


# ── Delete Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_competitor_success(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/competitors/{id} removes the competitor and returns 204."""
    created = await create_competitor_via_api(client, auth_headers, name="Delete Me")
    competitor_id = created["id"]

    resp = await client.delete(
        f"/api/v1/competitors/{competitor_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it is gone
    get_resp = await client.get(
        f"/api/v1/competitors/{competitor_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_competitor_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/competitors/{id} with non-existent ID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(
        f"/api/v1/competitors/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_competitor_wrong_user(client: AsyncClient):
    """DELETE /api/v1/competitors/{id} returns 404 if owned by another user."""
    headers_owner = await register_and_login(client, email="delowner@example.com")
    headers_other = await register_and_login(client, email="delother@example.com")

    created = await create_competitor_via_api(client, headers_owner, name="Keep Me")
    competitor_id = created["id"]

    resp = await client.delete(
        f"/api/v1/competitors/{competitor_id}", headers=headers_other
    )
    assert resp.status_code == 404

    # Verify it still exists for the owner
    get_resp = await client.get(
        f"/api/v1/competitors/{competitor_id}", headers=headers_owner
    )
    assert get_resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_competitor_reduces_count(client: AsyncClient, auth_headers: dict):
    """Deleting a competitor reduces the list total count."""
    created = await create_competitor_via_api(client, auth_headers, name="Count Store")

    resp_before = await client.get("/api/v1/competitors/", headers=auth_headers)
    assert resp_before.json()["total"] == 1

    await client.delete(
        f"/api/v1/competitors/{created['id']}", headers=auth_headers
    )

    resp_after = await client.get("/api/v1/competitors/", headers=auth_headers)
    assert resp_after.json()["total"] == 0


# ── Competitor Products Sub-resource Tests ──────────────────────────


@pytest.mark.asyncio
async def test_list_competitor_products_empty(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/competitors/{id}/products returns empty list for new competitor."""
    created = await create_competitor_via_api(client, auth_headers, name="Empty Products Store")
    competitor_id = created["id"]

    resp = await client.get(
        f"/api/v1/competitors/{competitor_id}/products", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_competitor_products_invalid_id(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/competitors/{id}/products with invalid UUID returns 400."""
    resp = await client.get(
        "/api/v1/competitors/not-valid/products", headers=auth_headers
    )
    assert resp.status_code == 400
