"""
Contact API endpoint tests.

Covers CRUD operations for contacts and contact lists, including
bulk import, tag management, pagination, search, and plan limit behavior.

For Developers:
    Uses the ``auth_headers`` fixture from conftest.py for authenticated
    requests. Each test is isolated via TRUNCATE between runs.

For QA Engineers:
    Run with: ``pytest tests/test_contacts.py -v``
    Verify: create, list (pagination, search, tag), get, update, delete,
    import (email list + CSV), contact lists CRUD, 404 handling.

For Project Managers:
    Contact management is foundational — every campaign and flow targets
    contacts. These tests ensure the contact pipeline is reliable.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helper constants ────────────────────────────────────────────────────

API_PREFIX = "/api/v1/contacts"


# ── Contact CRUD ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_contact(client: AsyncClient, auth_headers: dict):
    """POST /contacts creates a contact and returns 201 with full payload."""
    payload = {
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "tags": ["vip", "beta"],
        "custom_fields": {"source": "website"},
    }
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Smith"
    assert data["tags"] == ["vip", "beta"]
    assert data["custom_fields"] == {"source": "website"}
    assert data["is_subscribed"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_contact_minimal(client: AsyncClient, auth_headers: dict):
    """POST /contacts with only the required email field succeeds."""
    payload = {"email": "minimal@example.com"}
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "minimal@example.com"
    assert data["first_name"] is None
    assert data["last_name"] is None
    assert data["tags"] == []
    assert data["custom_fields"] == {}


@pytest.mark.asyncio
async def test_create_contact_invalid_email(client: AsyncClient, auth_headers: dict):
    """POST /contacts with an invalid email returns 422 validation error."""
    payload = {"email": "not-an-email"}
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_duplicate_email(client: AsyncClient, auth_headers: dict):
    """POST /contacts with a duplicate email returns 400."""
    payload = {"email": "dup@example.com"}
    resp1 = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp1.status_code == 201

    resp2 = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_list_contacts_empty(client: AsyncClient, auth_headers: dict):
    """GET /contacts with no data returns empty paginated response."""
    resp = await client.get(API_PREFIX, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_contacts_pagination(client: AsyncClient, auth_headers: dict):
    """GET /contacts respects page and page_size parameters."""
    # Create 3 contacts
    for i in range(3):
        await client.post(
            API_PREFIX,
            json={"email": f"page-{i}@example.com"},
            headers=auth_headers,
        )

    # Request page 1 with page_size=2
    resp = await client.get(
        f"{API_PREFIX}?page=1&page_size=2", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Request page 2
    resp2 = await client.get(
        f"{API_PREFIX}?page=2&page_size=2", headers=auth_headers
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1


@pytest.mark.asyncio
async def test_list_contacts_search(client: AsyncClient, auth_headers: dict):
    """GET /contacts?search= filters contacts by email or name match."""
    await client.post(
        API_PREFIX,
        json={"email": "searchable@example.com", "first_name": "Findme"},
        headers=auth_headers,
    )
    await client.post(
        API_PREFIX,
        json={"email": "other@example.com", "first_name": "Nope"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"{API_PREFIX}?search=searchable", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    emails = [c["email"] for c in data["items"]]
    assert "searchable@example.com" in emails


@pytest.mark.asyncio
async def test_list_contacts_tag_filter(client: AsyncClient, auth_headers: dict):
    """GET /contacts?tag= filters contacts that have the specified tag."""
    await client.post(
        API_PREFIX,
        json={"email": "tagged@example.com", "tags": ["premium"]},
        headers=auth_headers,
    )
    await client.post(
        API_PREFIX,
        json={"email": "untagged@example.com", "tags": []},
        headers=auth_headers,
    )

    resp = await client.get(
        f"{API_PREFIX}?tag=premium", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for contact in data["items"]:
        assert "premium" in contact["tags"]


@pytest.mark.asyncio
async def test_get_contact(client: AsyncClient, auth_headers: dict):
    """GET /contacts/:id returns the contact by UUID."""
    create_resp = await client.post(
        API_PREFIX,
        json={"email": "getme@example.com", "first_name": "GetMe"},
        headers=auth_headers,
    )
    contact_id = create_resp.json()["id"]

    resp = await client.get(f"{API_PREFIX}/{contact_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "getme@example.com"


@pytest.mark.asyncio
async def test_get_contact_not_found(client: AsyncClient, auth_headers: dict):
    """GET /contacts/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_contact(client: AsyncClient, auth_headers: dict):
    """PATCH /contacts/:id updates only the provided fields."""
    create_resp = await client.post(
        API_PREFIX,
        json={"email": "update-me@example.com", "first_name": "Old"},
        headers=auth_headers,
    )
    contact_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{API_PREFIX}/{contact_id}",
        json={"first_name": "New", "tags": ["updated"]},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["first_name"] == "New"
    assert data["tags"] == ["updated"]
    # Email should remain unchanged
    assert data["email"] == "update-me@example.com"


@pytest.mark.asyncio
async def test_update_contact_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /contacts/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"{API_PREFIX}/{fake_id}",
        json={"first_name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_unsubscribe(client: AsyncClient, auth_headers: dict):
    """PATCH /contacts/:id can toggle is_subscribed to false."""
    create_resp = await client.post(
        API_PREFIX,
        json={"email": "unsub@example.com"},
        headers=auth_headers,
    )
    contact_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{API_PREFIX}/{contact_id}",
        json={"is_subscribed": False},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_subscribed"] is False


@pytest.mark.asyncio
async def test_delete_contact(client: AsyncClient, auth_headers: dict):
    """DELETE /contacts/:id removes the contact and returns 204."""
    create_resp = await client.post(
        API_PREFIX,
        json={"email": "delete-me@example.com"},
        headers=auth_headers,
    )
    contact_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"{API_PREFIX}/{contact_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    # Verify it is gone
    get_resp = await client.get(
        f"{API_PREFIX}/{contact_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_contact_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /contacts/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_contact_count(client: AsyncClient, auth_headers: dict):
    """GET /contacts/count returns the total contact count for the user."""
    # Initially zero
    resp = await client.get(f"{API_PREFIX}/count", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 0

    # Create one contact
    await client.post(
        API_PREFIX,
        json={"email": "counted@example.com"},
        headers=auth_headers,
    )

    resp2 = await client.get(f"{API_PREFIX}/count", headers=auth_headers)
    assert resp2.status_code == 200
    assert resp2.json()["count"] == 1


# ── Bulk Import ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_import_contacts_email_list(client: AsyncClient, auth_headers: dict):
    """POST /contacts/import with an email list creates new contacts."""
    payload = {
        "emails": [
            "import1@example.com",
            "import2@example.com",
            "import3@example.com",
        ],
        "tags": ["imported"],
    }
    resp = await client.post(
        f"{API_PREFIX}/import", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 3
    assert data["skipped"] == 0
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_import_contacts_deduplication(client: AsyncClient, auth_headers: dict):
    """POST /contacts/import skips emails that already exist."""
    # Pre-create one contact
    await client.post(
        API_PREFIX,
        json={"email": "existing@example.com"},
        headers=auth_headers,
    )

    payload = {
        "emails": ["existing@example.com", "brand-new@example.com"],
    }
    resp = await client.post(
        f"{API_PREFIX}/import", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert data["skipped"] == 1
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_import_contacts_csv(client: AsyncClient, auth_headers: dict):
    """POST /contacts/import with csv_data parses and creates contacts."""
    csv_data = "email,first_name,last_name\ncsv1@example.com,Csv,One\ncsv2@example.com,Csv,Two"
    payload = {"csv_data": csv_data, "tags": ["csv-import"]}
    resp = await client.post(
        f"{API_PREFIX}/import", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] >= 2
    assert data["total"] >= 2


# ── Contact Lists ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_contact_list(client: AsyncClient, auth_headers: dict):
    """POST /contacts/lists creates a new contact list and returns 201."""
    payload = {
        "name": "VIP Customers",
        "description": "High-value repeat buyers",
        "list_type": "static",
    }
    resp = await client.post(
        f"{API_PREFIX}/lists", json=payload, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "VIP Customers"
    assert data["description"] == "High-value repeat buyers"
    assert data["list_type"] == "static"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_dynamic_contact_list(client: AsyncClient, auth_headers: dict):
    """POST /contacts/lists with dynamic type and rules succeeds."""
    payload = {
        "name": "Active Subscribers",
        "list_type": "dynamic",
        "rules": {"tag": "active", "subscribed": True},
    }
    resp = await client.post(
        f"{API_PREFIX}/lists", json=payload, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["list_type"] == "dynamic"
    assert data["rules"] == {"tag": "active", "subscribed": True}


@pytest.mark.asyncio
async def test_list_contact_lists(client: AsyncClient, auth_headers: dict):
    """GET /contacts/lists returns a paginated list of contact lists."""
    # Create two lists
    await client.post(
        f"{API_PREFIX}/lists",
        json={"name": "List A"},
        headers=auth_headers,
    )
    await client.post(
        f"{API_PREFIX}/lists",
        json={"name": "List B"},
        headers=auth_headers,
    )

    resp = await client.get(f"{API_PREFIX}/lists", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_delete_contact_list(client: AsyncClient, auth_headers: dict):
    """DELETE /contacts/lists/:id removes the list and returns 204."""
    create_resp = await client.post(
        f"{API_PREFIX}/lists",
        json={"name": "Deletable List"},
        headers=auth_headers,
    )
    list_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"{API_PREFIX}/lists/{list_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_contact_list_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /contacts/lists/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"{API_PREFIX}/lists/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Auth requirement ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_contacts_require_auth(client: AsyncClient):
    """All contact endpoints require authentication (401 without token)."""
    resp = await client.get(API_PREFIX)
    assert resp.status_code == 401

    resp2 = await client.post(API_PREFIX, json={"email": "noauth@example.com"})
    assert resp2.status_code == 401
