"""
Supplier account endpoint tests for SourcePilot.

Tests cover creating, listing, updating, and deleting supplier accounts
(e.g., AliExpress, CJ Dropshipping credentials).

For QA Engineers:
    Verifies CRUD operations on supplier accounts, including duplicate
    detection, authorization checks, and validation of required fields.
"""

import uuid

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_supplier_account(
    client: AsyncClient,
    headers: dict,
    *,
    name: str = "My AliExpress Account",
    platform: str = "aliexpress",
    credentials: dict | None = None,
) -> dict:
    """Create a supplier account via the API and return the response JSON.

    Args:
        client: The test HTTP client.
        headers: Auth headers for the request.
        name: Display name for the supplier account.
        platform: Supplier platform identifier.
        credentials: Platform-specific credentials.

    Returns:
        The created supplier account as a dict.
    """
    payload = {
        "name": name,
        "platform": platform,
        "credentials": credentials or {"api_key": "test-supplier-key-123"},
    }
    resp = await client.post("/api/v1/suppliers/accounts", json=payload, headers=headers)
    assert resp.status_code in (200, 201), f"Failed to create supplier account: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Create supplier account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_supplier_account(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/suppliers/accounts creates an account and returns details."""
    data = await _create_supplier_account(client, auth_headers)
    assert "id" in data
    assert data["name"] == "My AliExpress Account"
    assert data["platform"] == "aliexpress"


@pytest.mark.asyncio
async def test_create_supplier_account_different_platform(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/suppliers/accounts works for different supplier platforms."""
    data = await _create_supplier_account(
        client,
        auth_headers,
        name="CJ Account",
        platform="cjdropshipping",
        credentials={"api_key": "cj-key-456"},
    )
    assert "id" in data
    assert data["platform"] == "cjdropshipping"


@pytest.mark.asyncio
async def test_create_supplier_account_duplicate(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/suppliers/accounts with same name/platform returns 409 or 400."""
    await _create_supplier_account(client, auth_headers)
    resp = await client.post(
        "/api/v1/suppliers/accounts",
        json={
            "name": "My AliExpress Account",
            "platform": "aliexpress",
            "credentials": {"api_key": "another-key"},
        },
        headers=auth_headers,
    )
    assert resp.status_code in (400, 409)


@pytest.mark.asyncio
async def test_create_supplier_account_missing_fields(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/suppliers/accounts with missing name returns 422."""
    resp = await client.post(
        "/api/v1/suppliers/accounts",
        json={"platform": "aliexpress"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_supplier_account_unauthenticated(client: AsyncClient):
    """POST /api/v1/suppliers/accounts without auth returns 401."""
    resp = await client.post(
        "/api/v1/suppliers/accounts",
        json={
            "name": "Test",
            "platform": "aliexpress",
            "credentials": {"api_key": "key"},
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List supplier accounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_supplier_accounts_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/suppliers/accounts with no accounts returns empty list."""
    resp = await client.get("/api/v1/suppliers/accounts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_supplier_accounts(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/suppliers/accounts returns all user's supplier accounts."""
    await _create_supplier_account(client, auth_headers, name="Account A")
    await _create_supplier_account(
        client, auth_headers, name="Account B", platform="cjdropshipping"
    )
    resp = await client.get("/api/v1/suppliers/accounts", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_list_supplier_accounts_isolation(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/suppliers/accounts does not return other users' accounts."""
    await _create_supplier_account(client, auth_headers, name="User1 Account")

    other_headers = await register_and_login(client)
    resp = await client.get("/api/v1/suppliers/accounts", headers=other_headers)
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) == 0


@pytest.mark.asyncio
async def test_list_supplier_accounts_unauthenticated(client: AsyncClient):
    """GET /api/v1/suppliers/accounts without auth returns 401."""
    resp = await client.get("/api/v1/suppliers/accounts")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Update supplier account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_supplier_account(client: AsyncClient, auth_headers: dict):
    """PUT /api/v1/suppliers/accounts/{id} updates the account details."""
    created = await _create_supplier_account(client, auth_headers)
    account_id = created["id"]
    resp = await client.put(
        f"/api/v1/suppliers/accounts/{account_id}",
        json={"name": "Updated Name", "credentials": {"api_key": "new-key"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_supplier_account_not_found(client: AsyncClient, auth_headers: dict):
    """PUT /api/v1/suppliers/accounts/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.put(
        f"/api/v1/suppliers/accounts/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_supplier_account_other_user(client: AsyncClient, auth_headers: dict):
    """PUT /api/v1/suppliers/accounts/{id} by different user returns 403 or 404."""
    created = await _create_supplier_account(client, auth_headers)
    account_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.put(
        f"/api/v1/suppliers/accounts/{account_id}",
        json={"name": "Stolen Name"},
        headers=other_headers,
    )
    assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Delete supplier account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_supplier_account(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/suppliers/accounts/{id} removes the account."""
    created = await _create_supplier_account(client, auth_headers)
    account_id = created["id"]
    resp = await client.delete(
        f"/api/v1/suppliers/accounts/{account_id}", headers=auth_headers
    )
    assert resp.status_code in (200, 204)

    # Verify account is gone
    get_resp = await client.get("/api/v1/suppliers/accounts", headers=auth_headers)
    body = get_resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    ids = [item["id"] for item in items]
    assert account_id not in ids


@pytest.mark.asyncio
async def test_delete_supplier_account_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/suppliers/accounts/{id} with non-existent ID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/suppliers/accounts/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_supplier_account_other_user(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/suppliers/accounts/{id} by different user returns 403 or 404."""
    created = await _create_supplier_account(client, auth_headers)
    account_id = created["id"]

    other_headers = await register_and_login(client)
    resp = await client.delete(
        f"/api/v1/suppliers/accounts/{account_id}", headers=other_headers
    )
    assert resp.status_code in (403, 404)
