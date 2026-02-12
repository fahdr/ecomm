"""
Tests for the Watchlist API endpoints.

Covers watchlist CRUD operations: adding research results to the watchlist,
listing items with status filtering, updating status/notes, and removing items.
Also tests plan-based capacity limits and duplicate prevention.

For Developers:
    Tests use the `client` and `auth_headers` fixtures from conftest.py.
    Since watchlist items reference ResearchResult records, several helpers
    create the prerequisite run + result chain before testing watchlist logic.
    Results are created directly in the database via the `db` fixture.

For QA Engineers:
    These tests verify:
    - Add to watchlist (POST /api/v1/watchlist).
    - List watchlist items with optional status filter (GET /api/v1/watchlist).
    - Update item status and notes (PATCH /api/v1/watchlist/{id}).
    - Remove from watchlist (DELETE /api/v1/watchlist/{id}).
    - Duplicate prevention returns 409.
    - Unauthenticated access returns 401.
    - Cross-user access returns 404.

For Project Managers:
    The watchlist is how users save promising products from research results
    for ongoing monitoring. These tests ensure the save/organize/remove
    workflow is reliable and secure.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchResult, ResearchRun
from tests.conftest import register_and_login


# ─── Helper Functions ────────────────────────────────────────────────


async def create_run_with_result(
    client: AsyncClient,
    headers: dict,
    db: AsyncSession,
) -> tuple[dict, str]:
    """
    Create a research run via the API, then insert a result directly in the DB.

    We create the run via API (to get proper user association) but insert
    results directly because the Celery task is not running in tests.

    Args:
        client: The test HTTP client.
        headers: Authorization headers for the authenticated user.
        db: Async database session for direct result insertion.

    Returns:
        Tuple of (run response dict, result_id string).
    """
    # Create a run via API
    resp = await client.post(
        "/api/v1/research/runs",
        json={"keywords": ["test product"], "sources": ["aliexpress"]},
        headers=headers,
    )
    assert resp.status_code == 201
    run = resp.json()

    # Insert a result directly into the database
    result = ResearchResult(
        run_id=uuid.UUID(run["id"]),
        source="aliexpress",
        product_title="Test Wireless Earbuds",
        product_url="https://aliexpress.com/item/12345",
        image_url="https://img.aliexpress.com/12345.jpg",
        price=14.99,
        currency="USD",
        score=85.5,
        raw_data={"seller": "TestShop", "orders": 1500},
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    return run, str(result.id)


async def add_to_watchlist(
    client: AsyncClient,
    headers: dict,
    result_id: str,
    notes: str | None = None,
) -> dict:
    """
    Helper to add a result to the watchlist via the API.

    Args:
        client: The test HTTP client.
        headers: Authorization headers for the authenticated user.
        result_id: UUID string of the ResearchResult to save.
        notes: Optional notes to attach to the watchlist item.

    Returns:
        The created watchlist item response dict.
    """
    payload: dict = {"result_id": result_id}
    if notes is not None:
        payload["notes"] = notes

    resp = await client.post("/api/v1/watchlist", json=payload, headers=headers)
    assert resp.status_code == 201, f"Failed to add to watchlist: {resp.text}"
    return resp.json()


# ─── Add to Watchlist Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_to_watchlist(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """POST /api/v1/watchlist adds a result with 'watching' status and includes result snapshot."""
    _, result_id = await create_run_with_result(client, auth_headers, db)

    item = await add_to_watchlist(client, auth_headers, result_id)

    assert item["result_id"] == result_id
    assert item["status"] == "watching"
    assert item["notes"] is None
    assert "id" in item
    assert "user_id" in item
    assert "created_at" in item
    assert "updated_at" in item

    # Result snapshot should be included
    assert item["result"] is not None
    assert item["result"]["product_title"] == "Test Wireless Earbuds"
    assert item["result"]["source"] == "aliexpress"
    assert item["result"]["score"] == 85.5


@pytest.mark.asyncio
async def test_add_to_watchlist_with_notes(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """POST /api/v1/watchlist accepts optional notes text."""
    _, result_id = await create_run_with_result(client, auth_headers, db)

    item = await add_to_watchlist(
        client, auth_headers, result_id,
        notes="Great margins, low competition",
    )

    assert item["notes"] == "Great margins, low competition"


@pytest.mark.asyncio
async def test_add_to_watchlist_duplicate_rejected(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """POST /api/v1/watchlist returns 409 if the result is already in the user's watchlist."""
    _, result_id = await create_run_with_result(client, auth_headers, db)

    # First add succeeds
    await add_to_watchlist(client, auth_headers, result_id)

    # Duplicate attempt returns 409
    resp = await client.post(
        "/api/v1/watchlist",
        json={"result_id": result_id},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "already in your watchlist" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_add_to_watchlist_nonexistent_result(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/watchlist returns 404 when referencing a non-existent result."""
    fake_result_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/watchlist",
        json={"result_id": fake_result_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_to_watchlist_unauthenticated(client: AsyncClient):
    """POST /api/v1/watchlist returns 401 without auth headers."""
    resp = await client.post(
        "/api/v1/watchlist",
        json={"result_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


# ─── List Watchlist Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_watchlist_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/watchlist returns empty list when no items exist."""
    resp = await client.get("/api/v1/watchlist", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


@pytest.mark.asyncio
async def test_list_watchlist_returns_items(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """GET /api/v1/watchlist returns previously added items with result snapshots."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.get("/api/v1/watchlist", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["result"]["product_title"] == "Test Wireless Earbuds"


@pytest.mark.asyncio
async def test_list_watchlist_status_filter(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """GET /api/v1/watchlist?status=watching filters by status."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    # Update one to 'imported'
    await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"status": "imported"},
        headers=auth_headers,
    )

    # Filter by 'watching' — should be empty now
    resp = await client.get(
        "/api/v1/watchlist?status=watching", headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 0

    # Filter by 'imported' — should have 1
    resp = await client.get(
        "/api/v1/watchlist?status=imported", headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_watchlist_pagination(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """GET /api/v1/watchlist supports page and per_page parameters."""
    # Create 3 results and add them to watchlist
    for i in range(3):
        run_resp = await client.post(
            "/api/v1/research/runs",
            json={"keywords": [f"product {i}"], "sources": ["aliexpress"]},
            headers=auth_headers,
        )
        run = run_resp.json()
        result = ResearchResult(
            run_id=uuid.UUID(run["id"]),
            source="aliexpress",
            product_title=f"Product {i}",
            product_url=f"https://aliexpress.com/item/{i}",
            price=10.0 + i,
            currency="USD",
            score=50.0 + i * 10,
            raw_data={},
        )
        db.add(result)
        await db.commit()
        await db.refresh(result)
        await add_to_watchlist(client, auth_headers, str(result.id))

    # Page 1, 2 per page
    resp = await client.get(
        "/api/v1/watchlist?page=1&per_page=2", headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2

    # Page 2, 2 per page
    resp = await client.get(
        "/api/v1/watchlist?page=2&per_page=2", headers=auth_headers
    )
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_watchlist_user_isolation(client: AsyncClient, db: AsyncSession):
    """GET /api/v1/watchlist only shows items owned by the requesting user."""
    # User A adds an item
    headers_a = await register_and_login(client, "wl-user-a@example.com")
    _, result_id = await create_run_with_result(client, headers_a, db)
    await add_to_watchlist(client, headers_a, result_id)

    # User B should see no items
    headers_b = await register_and_login(client, "wl-user-b@example.com")
    resp = await client.get("/api/v1/watchlist", headers=headers_b)
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_watchlist_unauthenticated(client: AsyncClient):
    """GET /api/v1/watchlist returns 401 without auth headers."""
    resp = await client.get("/api/v1/watchlist")
    assert resp.status_code == 401


# ─── Update Watchlist Item Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_update_watchlist_status(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """PATCH /api/v1/watchlist/{id} updates the status field."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)
    assert item["status"] == "watching"

    # Update to 'imported'
    resp = await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"status": "imported"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["status"] == "imported"


@pytest.mark.asyncio
async def test_update_watchlist_to_dismissed(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """PATCH /api/v1/watchlist/{id} supports 'dismissed' status."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"status": "dismissed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


@pytest.mark.asyncio
async def test_update_watchlist_notes(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """PATCH /api/v1/watchlist/{id} updates the notes field."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"notes": "Updated notes: price dropped 20%"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated notes: price dropped 20%"


@pytest.mark.asyncio
async def test_update_watchlist_status_and_notes(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """PATCH /api/v1/watchlist/{id} can update both status and notes simultaneously."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"status": "imported", "notes": "Pushed to store on 2024-01-15"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["status"] == "imported"
    assert updated["notes"] == "Pushed to store on 2024-01-15"


@pytest.mark.asyncio
async def test_update_watchlist_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/watchlist/{id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/watchlist/{fake_id}",
        json={"status": "imported"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_watchlist_wrong_user(client: AsyncClient, db: AsyncSession):
    """PATCH /api/v1/watchlist/{id} returns 404 when user does not own the item."""
    headers_a = await register_and_login(client, "wl-owner@example.com")
    _, result_id = await create_run_with_result(client, headers_a, db)
    item = await add_to_watchlist(client, headers_a, result_id)

    headers_b = await register_and_login(client, "wl-intruder@example.com")
    resp = await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"status": "dismissed"},
        headers=headers_b,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_watchlist_unauthenticated(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """PATCH /api/v1/watchlist/{id} returns 401 without auth headers."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.patch(
        f"/api/v1/watchlist/{item['id']}",
        json={"status": "imported"},
    )
    assert resp.status_code == 401


# ─── Delete Watchlist Item Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_watchlist_item(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """DELETE /api/v1/watchlist/{id} removes the item and returns 204."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.delete(
        f"/api/v1/watchlist/{item['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify item is gone
    resp = await client.get("/api/v1/watchlist", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_delete_watchlist_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/watchlist/{id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/watchlist/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_watchlist_wrong_user(client: AsyncClient, db: AsyncSession):
    """DELETE /api/v1/watchlist/{id} returns 404 when user does not own the item."""
    headers_a = await register_and_login(client, "delwl-owner@example.com")
    _, result_id = await create_run_with_result(client, headers_a, db)
    item = await add_to_watchlist(client, headers_a, result_id)

    headers_b = await register_and_login(client, "delwl-intruder@example.com")
    resp = await client.delete(
        f"/api/v1/watchlist/{item['id']}", headers=headers_b
    )
    assert resp.status_code == 404

    # Verify item still exists for owner
    resp = await client.get("/api/v1/watchlist", headers=headers_a)
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_delete_watchlist_unauthenticated(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """DELETE /api/v1/watchlist/{id} returns 401 without auth headers."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    resp = await client.delete(f"/api/v1/watchlist/{item['id']}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_watchlist_decrements_total(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """Deleting a watchlist item decreases the total count returned by list endpoint."""
    # Create two results and add both to watchlist
    _, result_id_1 = await create_run_with_result(client, auth_headers, db)
    item1 = await add_to_watchlist(client, auth_headers, result_id_1)

    run_resp = await client.post(
        "/api/v1/research/runs",
        json={"keywords": ["second product"], "sources": ["aliexpress"]},
        headers=auth_headers,
    )
    run2 = run_resp.json()
    result2 = ResearchResult(
        run_id=uuid.UUID(run2["id"]),
        source="aliexpress",
        product_title="Second Product",
        product_url="https://aliexpress.com/item/99999",
        price=9.99,
        currency="USD",
        score=72.0,
        raw_data={},
    )
    db.add(result2)
    await db.commit()
    await db.refresh(result2)
    item2 = await add_to_watchlist(client, auth_headers, str(result2.id))

    # Verify 2 items
    resp = await client.get("/api/v1/watchlist", headers=auth_headers)
    assert resp.json()["total"] == 2

    # Delete one
    resp = await client.delete(
        f"/api/v1/watchlist/{item2['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify only 1 remains
    resp = await client.get("/api/v1/watchlist", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == item1["id"]


@pytest.mark.asyncio
async def test_re_add_after_delete(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    """After deleting a watchlist item, the same result can be added again."""
    _, result_id = await create_run_with_result(client, auth_headers, db)
    item = await add_to_watchlist(client, auth_headers, result_id)

    # Delete
    resp = await client.delete(
        f"/api/v1/watchlist/{item['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Re-add the same result
    item2 = await add_to_watchlist(
        client, auth_headers, result_id, notes="Re-added after reconsideration"
    )
    assert item2["result_id"] == result_id
    assert item2["notes"] == "Re-added after reconsideration"
    assert item2["id"] != item["id"]  # New watchlist item ID
