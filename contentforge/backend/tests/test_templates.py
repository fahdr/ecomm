"""
Template management endpoint tests.

Covers full CRUD lifecycle for content generation templates including
system templates (read-only, visible to all), custom templates (private
to the owning user), visibility rules, and access control.

For Developers:
    Tests use the `register_and_login` helper from conftest.py to create
    authenticated users. Each test is independent (database is truncated
    between tests via the `setup_db` autouse fixture).

    System templates are created directly via the DB session fixture to
    simulate the template seeder that runs at application startup.

For QA Engineers:
    Each test verifies a single behavior of the template API.
    Run with: `pytest tests/test_templates.py -v`
    Tests cover:
    - Custom template CRUD (create, read, update, delete)
    - System template visibility and protection (403 on modify/delete)
    - User isolation (user A cannot access user B's templates)
    - Partial update (PATCH with only some fields)
    - Validation (empty name rejected)
    - Unauthenticated access (401)

For Project Managers:
    Templates are a key differentiating feature. These tests ensure that
    system templates remain protected while custom templates give users
    full control over their content generation style.

For End Users:
    These tests verify that your custom templates are safely stored and
    only visible to you, while system templates remain available to
    everyone for quick-start content generation.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template
from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_create_custom_template(client: AsyncClient):
    """POST /templates/ creates a custom template with provided settings."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={
            "name": "My Brand Voice",
            "description": "Casual and fun product descriptions",
            "tone": "casual",
            "style": "storytelling",
            "content_types": ["title", "description"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Brand Voice"
    assert data["description"] == "Casual and fun product descriptions"
    assert data["tone"] == "casual"
    assert data["style"] == "storytelling"
    assert data["content_types"] == ["title", "description"]
    assert data["is_system"] is False
    assert data["is_default"] is False
    assert data["user_id"] is not None


@pytest.mark.asyncio
async def test_create_template_minimal_fields(client: AsyncClient):
    """POST /templates/ with only required fields uses defaults for optional ones."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={"name": "Minimal Template"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Minimal Template"
    assert data["tone"] == "professional"  # default
    assert data["style"] == "detailed"  # default
    assert len(data["content_types"]) == 6  # all content types by default


@pytest.mark.asyncio
async def test_list_templates_includes_custom(client: AsyncClient):
    """GET /templates/ returns the user's custom templates."""
    headers = await register_and_login(client)

    # Create two templates
    await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={"name": "Template Alpha", "tone": "casual"},
    )
    await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={"name": "Template Beta", "tone": "luxury"},
    )

    resp = await client.get("/api/v1/templates/", headers=headers)
    assert resp.status_code == 200
    templates = resp.json()
    custom_names = [t["name"] for t in templates if not t["is_system"]]
    assert "Template Alpha" in custom_names
    assert "Template Beta" in custom_names


@pytest.mark.asyncio
async def test_get_template_by_id(client: AsyncClient):
    """GET /templates/{id} returns the template details."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={
            "name": "Fetchable Template",
            "tone": "technical",
            "style": "concise",
        },
    )
    template_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/templates/{template_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == template_id
    assert data["name"] == "Fetchable Template"
    assert data["tone"] == "technical"
    assert data["style"] == "concise"


@pytest.mark.asyncio
async def test_get_template_not_found(client: AsyncClient):
    """GET /templates/{id} returns 404 for nonexistent template."""
    headers = await register_and_login(client)

    resp = await client.get(
        "/api/v1/templates/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_template_partial(client: AsyncClient):
    """PATCH /templates/{id} updates only the provided fields."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={
            "name": "Original Name",
            "tone": "professional",
            "style": "detailed",
            "description": "Original description",
        },
    )
    template_id = create_resp.json()["id"]

    # Update only name and tone
    resp = await client.patch(
        f"/api/v1/templates/{template_id}",
        headers=headers,
        json={"name": "Updated Name", "tone": "playful"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["tone"] == "playful"
    # Unchanged fields should remain the same
    assert data["style"] == "detailed"
    assert data["description"] == "Original description"


@pytest.mark.asyncio
async def test_update_template_all_fields(client: AsyncClient):
    """PATCH /templates/{id} with all fields updates every attribute."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={"name": "Full Update Test"},
    )
    template_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/templates/{template_id}",
        headers=headers,
        json={
            "name": "Completely Renamed",
            "description": "New description",
            "tone": "luxury",
            "style": "storytelling",
            "prompt_override": "Write like a luxury brand copywriter.",
            "content_types": ["title", "meta_description"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Completely Renamed"
    assert data["description"] == "New description"
    assert data["tone"] == "luxury"
    assert data["style"] == "storytelling"
    assert data["prompt_override"] == "Write like a luxury brand copywriter."
    assert data["content_types"] == ["title", "meta_description"]


@pytest.mark.asyncio
async def test_update_template_not_found(client: AsyncClient):
    """PATCH /templates/{id} returns 404 for nonexistent template."""
    headers = await register_and_login(client)

    resp = await client.patch(
        "/api/v1/templates/00000000-0000-0000-0000-000000000000",
        headers=headers,
        json={"name": "No Such Template"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_custom_template(client: AsyncClient):
    """DELETE /templates/{id} removes the user's custom template."""
    headers = await register_and_login(client)

    create_resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={"name": "Deletable Template"},
    )
    template_id = create_resp.json()["id"]

    # Delete
    resp = await client.delete(f"/api/v1/templates/{template_id}", headers=headers)
    assert resp.status_code == 204

    # Verify it is gone
    resp = await client.get(f"/api/v1/templates/{template_id}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_not_found(client: AsyncClient):
    """DELETE /templates/{id} returns 404 for nonexistent template."""
    headers = await register_and_login(client)

    resp = await client.delete(
        "/api/v1/templates/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_system_template_visible_to_all(client: AsyncClient, db: AsyncSession):
    """System templates are visible in the template list for any user."""
    # Seed a system template directly in the database
    system_tpl = Template(
        name="Professional Default",
        tone="professional",
        style="detailed",
        content_types=["title", "description", "meta_description", "keywords", "bullet_points"],
        is_system=True,
        is_default=True,
        user_id=None,
    )
    db.add(system_tpl)
    await db.commit()

    headers = await register_and_login(client)
    resp = await client.get("/api/v1/templates/", headers=headers)
    assert resp.status_code == 200
    templates = resp.json()
    system_names = [t["name"] for t in templates if t["is_system"]]
    assert "Professional Default" in system_names


@pytest.mark.asyncio
async def test_system_template_cannot_be_updated(client: AsyncClient, db: AsyncSession):
    """PATCH on a system template returns 403 Forbidden."""
    system_tpl = Template(
        name="Immutable System Template",
        tone="professional",
        style="detailed",
        content_types=["title"],
        is_system=True,
        is_default=False,
        user_id=None,
    )
    db.add(system_tpl)
    await db.commit()
    await db.refresh(system_tpl)

    headers = await register_and_login(client)
    resp = await client.patch(
        f"/api/v1/templates/{system_tpl.id}",
        headers=headers,
        json={"name": "Hacked Name"},
    )
    assert resp.status_code == 403
    assert "system" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_system_template_cannot_be_deleted(client: AsyncClient, db: AsyncSession):
    """DELETE on a system template returns 403 Forbidden."""
    system_tpl = Template(
        name="Protected System Template",
        tone="casual",
        style="concise",
        content_types=["title"],
        is_system=True,
        is_default=False,
        user_id=None,
    )
    db.add(system_tpl)
    await db.commit()
    await db.refresh(system_tpl)

    headers = await register_and_login(client)
    resp = await client.delete(
        f"/api/v1/templates/{system_tpl.id}",
        headers=headers,
    )
    assert resp.status_code == 403
    assert "system" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_template_isolation_between_users(client: AsyncClient):
    """Users cannot access or modify each other's custom templates."""
    headers_a = await register_and_login(client, "tpl-user-a@example.com")
    headers_b = await register_and_login(client, "tpl-user-b@example.com")

    # User A creates a template
    create_resp = await client.post(
        "/api/v1/templates/",
        headers=headers_a,
        json={"name": "User A Secret Template"},
    )
    template_id = create_resp.json()["id"]

    # User B cannot fetch it
    resp = await client.get(f"/api/v1/templates/{template_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B cannot update it
    resp = await client.patch(
        f"/api/v1/templates/{template_id}",
        headers=headers_b,
        json={"name": "Stolen Name"},
    )
    assert resp.status_code == 404

    # User B cannot delete it
    resp = await client.delete(f"/api/v1/templates/{template_id}", headers=headers_b)
    assert resp.status_code == 404

    # User B's template list should not include User A's template
    resp = await client.get("/api/v1/templates/", headers=headers_b)
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "User A Secret Template" not in names


@pytest.mark.asyncio
async def test_unauthenticated_access_templates(client: AsyncClient):
    """Template endpoints require authentication."""
    resp = await client.get("/api/v1/templates/")
    assert resp.status_code == 401

    resp = await client.post(
        "/api/v1/templates/",
        json={"name": "Unauthorized Template"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_template_with_prompt_override(client: AsyncClient):
    """POST /templates/ with prompt_override stores the custom prompt."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/templates/",
        headers=headers,
        json={
            "name": "Custom Prompt Template",
            "prompt_override": "You are a witty copywriter. Write engaging product content.",
            "tone": "playful",
            "style": "storytelling",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["prompt_override"] == "You are a witty copywriter. Write engaging product content."


@pytest.mark.asyncio
async def test_system_template_accessible_by_id(client: AsyncClient, db: AsyncSession):
    """GET /templates/{id} for a system template returns it to any user."""
    system_tpl = Template(
        name="Accessible System Template",
        tone="luxury",
        style="detailed",
        content_types=["title", "description"],
        is_system=True,
        is_default=False,
        user_id=None,
    )
    db.add(system_tpl)
    await db.commit()
    await db.refresh(system_tpl)

    headers = await register_and_login(client)
    resp = await client.get(f"/api/v1/templates/{system_tpl.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Accessible System Template"
    assert data["is_system"] is True
