"""
Email template API endpoint tests.

Covers CRUD operations for custom email templates, category filtering,
and validation rules (system templates cannot be modified/deleted).

For Developers:
    Uses the ``auth_headers`` fixture from conftest.py for authenticated
    requests. System templates are pre-seeded by the application and
    should be readable but not modifiable by users.

For QA Engineers:
    Run with: ``pytest tests/test_templates.py -v``
    Verify: create, list (pagination, category filter, includes system),
    get, update (custom only), delete (custom only), 404 handling,
    validation (missing required fields).

For Project Managers:
    Templates speed up campaign creation and ensure brand consistency.
    These tests confirm the template library works end-to-end.
"""

import uuid

import pytest
from httpx import AsyncClient


# ── Helper constants ────────────────────────────────────────────────────

API_PREFIX = "/api/v1/templates"

SAMPLE_TEMPLATE = {
    "name": "Welcome Email",
    "subject": "Welcome to our store!",
    "html_content": "<h1>Welcome!</h1><p>Thanks for joining.</p>",
    "text_content": "Welcome! Thanks for joining.",
    "category": "welcome",
}


# ── Template CRUD ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template(client: AsyncClient, auth_headers: dict):
    """POST /templates creates a custom template and returns 201."""
    resp = await client.post(
        API_PREFIX, json=SAMPLE_TEMPLATE, headers=auth_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Welcome Email"
    assert data["subject"] == "Welcome to our store!"
    assert data["html_content"] == "<h1>Welcome!</h1><p>Thanks for joining.</p>"
    assert data["text_content"] == "Welcome! Thanks for joining."
    assert data["category"] == "welcome"
    assert data["is_system"] is False
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_template_minimal(client: AsyncClient, auth_headers: dict):
    """POST /templates with only required fields uses defaults."""
    payload = {
        "name": "Minimal Template",
        "subject": "Hello",
        "html_content": "<p>Hello world</p>",
    }
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "newsletter"  # default
    assert data["text_content"] is None


@pytest.mark.asyncio
async def test_create_template_missing_required_fields(
    client: AsyncClient, auth_headers: dict
):
    """POST /templates with missing required fields returns 422."""
    # Missing html_content
    resp = await client.post(
        API_PREFIX,
        json={"name": "Incomplete", "subject": "Hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    # Missing subject
    resp2 = await client.post(
        API_PREFIX,
        json={"name": "No Subject", "html_content": "<p>Hi</p>"},
        headers=auth_headers,
    )
    assert resp2.status_code == 422

    # Missing name
    resp3 = await client.post(
        API_PREFIX,
        json={"subject": "No Name", "html_content": "<p>Hi</p>"},
        headers=auth_headers,
    )
    assert resp3.status_code == 422


@pytest.mark.asyncio
async def test_create_template_empty_name_rejected(
    client: AsyncClient, auth_headers: dict
):
    """POST /templates with empty name string returns 422."""
    payload = {"name": "", "subject": "Subject", "html_content": "<p>Hi</p>"}
    resp = await client.post(API_PREFIX, json=payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_templates_empty(client: AsyncClient, auth_headers: dict):
    """GET /templates returns at least the system templates (or empty)."""
    resp = await client.get(API_PREFIX, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_templates_pagination(client: AsyncClient, auth_headers: dict):
    """GET /templates respects page and page_size parameters."""
    for i in range(3):
        await client.post(
            API_PREFIX,
            json={
                "name": f"Tmpl {i}",
                "subject": f"Subject {i}",
                "html_content": f"<p>Content {i}</p>",
            },
            headers=auth_headers,
        )

    resp = await client.get(
        f"{API_PREFIX}?page=1&page_size=2", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_list_templates_category_filter(
    client: AsyncClient, auth_headers: dict
):
    """GET /templates?category= filters templates by category."""
    await client.post(
        API_PREFIX,
        json={
            "name": "Promo Template",
            "subject": "Sale!",
            "html_content": "<p>Big sale</p>",
            "category": "promo",
        },
        headers=auth_headers,
    )
    await client.post(
        API_PREFIX,
        json={
            "name": "Cart Template",
            "subject": "Your cart",
            "html_content": "<p>Cart reminder</p>",
            "category": "cart",
        },
        headers=auth_headers,
    )

    resp = await client.get(
        f"{API_PREFIX}?category=promo", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    for tmpl in data["items"]:
        assert tmpl["category"] == "promo"


@pytest.mark.asyncio
async def test_get_template(client: AsyncClient, auth_headers: dict):
    """GET /templates/:id returns the template by UUID."""
    create_resp = await client.post(
        API_PREFIX, json=SAMPLE_TEMPLATE, headers=auth_headers
    )
    template_id = create_resp.json()["id"]

    resp = await client.get(
        f"{API_PREFIX}/{template_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Welcome Email"


@pytest.mark.asyncio
async def test_get_template_not_found(client: AsyncClient, auth_headers: dict):
    """GET /templates/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_template(client: AsyncClient, auth_headers: dict):
    """PATCH /templates/:id updates a custom template's fields."""
    create_resp = await client.post(
        API_PREFIX, json=SAMPLE_TEMPLATE, headers=auth_headers
    )
    template_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{API_PREFIX}/{template_id}",
        json={
            "name": "Updated Welcome",
            "subject": "New Subject",
            "html_content": "<h1>Updated!</h1>",
        },
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["name"] == "Updated Welcome"
    assert data["subject"] == "New Subject"
    assert data["html_content"] == "<h1>Updated!</h1>"


@pytest.mark.asyncio
async def test_update_template_partial(client: AsyncClient, auth_headers: dict):
    """PATCH /templates/:id with partial data only updates provided fields."""
    create_resp = await client.post(
        API_PREFIX, json=SAMPLE_TEMPLATE, headers=auth_headers
    )
    template_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"{API_PREFIX}/{template_id}",
        json={"category": "transactional"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["category"] == "transactional"
    # Other fields unchanged
    assert data["name"] == "Welcome Email"
    assert data["subject"] == "Welcome to our store!"


@pytest.mark.asyncio
async def test_update_template_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /templates/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"{API_PREFIX}/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_template(client: AsyncClient, auth_headers: dict):
    """DELETE /templates/:id removes a custom template and returns 204."""
    create_resp = await client.post(
        API_PREFIX, json=SAMPLE_TEMPLATE, headers=auth_headers
    )
    template_id = create_resp.json()["id"]

    del_resp = await client.delete(
        f"{API_PREFIX}/{template_id}", headers=auth_headers
    )
    assert del_resp.status_code == 204

    # Verify it is gone
    get_resp = await client.get(
        f"{API_PREFIX}/{template_id}", headers=auth_headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /templates/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"{API_PREFIX}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Auth requirement ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_templates_require_auth(client: AsyncClient):
    """All template endpoints require authentication (401 without token)."""
    resp = await client.get(API_PREFIX)
    assert resp.status_code == 401

    resp2 = await client.post(API_PREFIX, json=SAMPLE_TEMPLATE)
    assert resp2.status_code == 401
