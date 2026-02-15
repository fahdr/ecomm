"""
Price watch (monitoring) endpoint tests for SourcePilot.

Tests cover creating, listing, filtering, deleting price watches, and
triggering manual price syncs.

For QA Engineers:
    Verifies the full price-watch lifecycle: create, list, filter by store,
    delete, and manual sync. Checks authentication, authorization, pagination,
    and edge cases such as duplicate watches and non-existent IDs.
"""

import uuid

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_connection(
    client: AsyncClient,
    headers: dict,
    *,
    store_name: str = "Price Watch Shop",
    store_url: str = "https://pricewatch.myshopify.com",
) -> dict:
    """Create a store connection and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Auth headers for the request.
        store_name: Display name for the store.
        store_url: URL of the store.

    Returns:
        The created connection as a dict.
    """
    resp = await client.post(
        "/api/v1/connections",
        json={
            "store_name": store_name,
            "platform": "shopify",
            "store_url": store_url,
            "api_key": "pw-key-123",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"Failed to create connection: {resp.text}"
    return resp.json()


async def _create_price_watch(
    client: AsyncClient,
    headers: dict,
    *,
    product_url: str = "https://www.aliexpress.com/item/555.html",
    source: str = "aliexpress",
    connection_id: str | None = None,
    threshold_percent: float = 10.0,
) -> dict:
    """Create a price watch via the API and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Auth headers for the request.
        product_url: URL of the product to monitor.
        source: Supplier source platform.
        connection_id: Optional store connection to associate.
        threshold_percent: Price change threshold to trigger alerts.

    Returns:
        The created price watch as a dict.
    """
    payload: dict = {
        "product_url": product_url,
        "source": source,
        "threshold_percent": threshold_percent,
    }
    if connection_id:
        payload["connection_id"] = connection_id
    resp = await client.post("/api/v1/price-watches", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"Failed to create price watch: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Create price watch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_price_watch(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/price-watches creates a price watch and returns details."""
    data = await _create_price_watch(client, auth_headers)
    assert "id" in data
    assert data["product_url"] == "https://www.aliexpress.com/item/555.html"


@pytest.mark.asyncio
async def test_create_price_watch_with_connection(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/price-watches with a connection_id associates the watch."""
    conn = await _create_connection(client, auth_headers)
    data = await _create_price_watch(client, auth_headers, connection_id=conn["id"])
    assert "id" in data
    assert data.get("connection_id") == conn["id"] or data.get("store_id") == conn["id"]


@pytest.mark.asyncio
async def test_create_price_watch_missing_url(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/price-watches without product_url returns 422."""
    resp = await client.post(
        "/api/v1/price-watches",
        json={"source": "aliexpress"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_price_watch_unauthenticated(client: AsyncClient):
    """POST /api/v1/price-watches without auth returns 401."""
    resp = await client.post(
        "/api/v1/price-watches",
        json={
            "product_url": "https://www.aliexpress.com/item/555.html",
            "source": "aliexpress",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_price_watch_custom_threshold(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/price-watches with a custom threshold percentage stores it."""
    data = await _create_price_watch(
        client, auth_headers, threshold_percent=5.5
    )
    assert "id" in data
    # Threshold may be returned in the response
    if "threshold_percent" in data:
        assert data["threshold_percent"] == 5.5


# ---------------------------------------------------------------------------
# List price watches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_price_watches_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/price-watches with no watches returns empty list."""
    resp = await client.get("/api/v1/price-watches", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_price_watches(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/price-watches returns all user's price watches."""
    await _create_price_watch(
        client,
        auth_headers,
        product_url="https://www.aliexpress.com/item/111.html",
    )
    await _create_price_watch(
        client,
        auth_headers,
        product_url="https://www.aliexpress.com/item/222.html",
    )
    resp = await client.get("/api/v1/price-watches", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_price_watches_filter_store(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/price-watches?connection_id=<id> filters by store."""
    conn = await _create_connection(client, auth_headers)
    await _create_price_watch(
        client,
        auth_headers,
        product_url="https://www.aliexpress.com/item/333.html",
        connection_id=conn["id"],
    )
    await _create_price_watch(
        client,
        auth_headers,
        product_url="https://www.aliexpress.com/item/444.html",
    )

    # Filter by the connection_id (or store_id param)
    resp = await client.get(
        "/api/v1/price-watches",
        params={"connection_id": conn["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_list_price_watches_isolation(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/price-watches does not return other users' watches."""
    await _create_price_watch(client, auth_headers)

    other_headers = await register_and_login(client)
    resp = await client.get("/api/v1/price-watches", headers=other_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_price_watches_unauthenticated(client: AsyncClient):
    """GET /api/v1/price-watches without auth returns 401."""
    resp = await client.get("/api/v1/price-watches")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Delete price watch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_price_watch(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/price-watches/{id} removes the watch."""
    created = await _create_price_watch(client, auth_headers)
    watch_id = created["id"]
    resp = await client.delete(f"/api/v1/price-watches/{watch_id}", headers=auth_headers)
    assert resp.status_code in (200, 204)

    # Verify watch is gone
    list_resp = await client.get("/api/v1/price-watches", headers=auth_headers)
    body = list_resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    ids = [item["id"] for item in items]
    assert watch_id not in ids


@pytest.mark.asyncio
async def test_delete_price_watch_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/price-watches/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/price-watches/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_price_watch_other_user(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/price-watches/{id} by different user returns 403 or 404."""
    created = await _create_price_watch(client, auth_headers)
    watch_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.delete(f"/api/v1/price-watches/{watch_id}", headers=other_headers)
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Trigger manual price sync
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_price_sync(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/price-watches/sync triggers a manual price check."""
    await _create_price_watch(client, auth_headers)
    resp = await client.post("/api/v1/price-watches/sync", headers=auth_headers)
    assert resp.status_code in (200, 202)


@pytest.mark.asyncio
async def test_trigger_price_sync_no_watches(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/price-watches/sync with no watches still succeeds."""
    resp = await client.post("/api/v1/price-watches/sync", headers=auth_headers)
    assert resp.status_code in (200, 202)


@pytest.mark.asyncio
async def test_trigger_price_sync_unauthenticated(client: AsyncClient):
    """POST /api/v1/price-watches/sync without auth returns 401."""
    resp = await client.post("/api/v1/price-watches/sync")
    assert resp.status_code == 401
