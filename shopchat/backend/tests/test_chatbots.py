"""
Chatbot CRUD API endpoint tests.

Validates create, list, get, update, and delete operations for chatbots.
Ensures proper authentication enforcement, user scoping (users cannot
access other users' chatbots), and field validation.

For QA Engineers:
    Run with: pytest tests/test_chatbots.py -v
    Tests cover the happy path for all CRUD operations, plus error cases
    like accessing nonexistent chatbots and unauthorized access.

For Developers:
    All tests use the `client` and `auth_headers` fixtures from conftest.py.
    A second user is created inline via `register_and_login` to test scoping.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ──────────────────────────────────────────────────────────


async def create_test_chatbot(
    client: AsyncClient,
    headers: dict,
    name: str = "Test Bot",
    personality: str = "friendly",
    welcome_message: str = "Hello! How can I help?",
) -> dict:
    """
    Create a chatbot via the API and return the response JSON.

    Args:
        client: The httpx test client.
        headers: Authorization headers.
        name: Chatbot name.
        personality: Chatbot personality style.
        welcome_message: Widget welcome greeting.

    Returns:
        The created chatbot response as a dict.
    """
    resp = await client.post(
        "/api/v1/chatbots",
        json={
            "name": name,
            "personality": personality,
            "welcome_message": welcome_message,
            "theme_config": {
                "primary_color": "#6366f1",
                "text_color": "#ffffff",
                "position": "bottom-right",
                "size": "medium",
            },
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ── Create Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_chatbot(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/chatbots creates a chatbot and returns it with a widget_key."""
    data = await create_test_chatbot(client, auth_headers, name="My Support Bot")

    assert data["name"] == "My Support Bot"
    assert data["personality"] == "friendly"
    assert data["welcome_message"] == "Hello! How can I help?"
    assert data["is_active"] is True
    assert "widget_key" in data
    assert len(data["widget_key"]) > 0
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_chatbot_custom_personality(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/chatbots respects custom personality and welcome_message."""
    data = await create_test_chatbot(
        client,
        auth_headers,
        name="Pro Bot",
        personality="professional",
        welcome_message="Welcome. How may I assist you?",
    )

    assert data["personality"] == "professional"
    assert data["welcome_message"] == "Welcome. How may I assist you?"


@pytest.mark.asyncio
async def test_create_chatbot_with_theme(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/chatbots stores theme_config correctly."""
    resp = await client.post(
        "/api/v1/chatbots",
        json={
            "name": "Themed Bot",
            "theme_config": {
                "primary_color": "#ff5500",
                "text_color": "#000000",
                "position": "bottom-left",
                "size": "large",
            },
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["theme_config"]["primary_color"] == "#ff5500"
    assert data["theme_config"]["position"] == "bottom-left"


@pytest.mark.asyncio
async def test_create_chatbot_no_auth(client: AsyncClient):
    """POST /api/v1/chatbots without auth returns 401."""
    resp = await client.post(
        "/api/v1/chatbots",
        json={"name": "Unauthorized Bot"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_chatbot_empty_name(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/chatbots with empty name returns 422 validation error."""
    resp = await client.post(
        "/api/v1/chatbots",
        json={"name": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── List Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_chatbots_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots returns empty paginated list for new user."""
    resp = await client.get("/api/v1/chatbots", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_chatbots_with_data(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots returns all chatbots created by the user."""
    await create_test_chatbot(client, auth_headers, name="Bot A")
    await create_test_chatbot(client, auth_headers, name="Bot B")
    await create_test_chatbot(client, auth_headers, name="Bot C")

    resp = await client.get("/api/v1/chatbots", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    names = {item["name"] for item in data["items"]}
    assert names == {"Bot A", "Bot B", "Bot C"}


@pytest.mark.asyncio
async def test_list_chatbots_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots supports pagination parameters."""
    for i in range(5):
        await create_test_chatbot(client, auth_headers, name=f"Bot {i}")

    # Page 1, 2 per page
    resp = await client.get(
        "/api/v1/chatbots?page=1&page_size=2", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Page 3, 2 per page (should have 1 remaining item)
    resp = await client.get(
        "/api/v1/chatbots?page=3&page_size=2", headers=auth_headers
    )
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_chatbots_user_scoping(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots only returns chatbots for the authenticated user."""
    await create_test_chatbot(client, auth_headers, name="User1 Bot")

    # Create a second user
    user2_headers = await register_and_login(client, "user2@example.com")
    await create_test_chatbot(client, user2_headers, name="User2 Bot")

    # User 1 should only see their bot
    resp = await client.get("/api/v1/chatbots", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "User1 Bot"

    # User 2 should only see their bot
    resp = await client.get("/api/v1/chatbots", headers=user2_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "User2 Bot"


# ── Get Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_chatbot(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots/:id returns the chatbot details."""
    created = await create_test_chatbot(client, auth_headers, name="Detail Bot")
    chatbot_id = created["id"]

    resp = await client.get(f"/api/v1/chatbots/{chatbot_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == chatbot_id
    assert data["name"] == "Detail Bot"
    assert data["widget_key"] == created["widget_key"]


@pytest.mark.asyncio
async def test_get_chatbot_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots/:id returns 404 for nonexistent chatbot."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/chatbots/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_chatbot_other_user(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/chatbots/:id returns 404 when accessing another user's chatbot."""
    created = await create_test_chatbot(client, auth_headers, name="Owner Bot")
    chatbot_id = created["id"]

    user2_headers = await register_and_login(client, "other@example.com")
    resp = await client.get(f"/api/v1/chatbots/{chatbot_id}", headers=user2_headers)
    assert resp.status_code == 404


# ── Update Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_chatbot_name(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/chatbots/:id updates the chatbot name."""
    created = await create_test_chatbot(client, auth_headers, name="Old Name")
    chatbot_id = created["id"]

    resp = await client.patch(
        f"/api/v1/chatbots/{chatbot_id}",
        json={"name": "New Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    # Other fields should be unchanged
    assert data["personality"] == created["personality"]


@pytest.mark.asyncio
async def test_update_chatbot_personality(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/chatbots/:id updates the personality."""
    created = await create_test_chatbot(client, auth_headers)
    chatbot_id = created["id"]

    resp = await client.patch(
        f"/api/v1/chatbots/{chatbot_id}",
        json={"personality": "casual"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["personality"] == "casual"


@pytest.mark.asyncio
async def test_update_chatbot_deactivate(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/chatbots/:id can deactivate a chatbot."""
    created = await create_test_chatbot(client, auth_headers)
    chatbot_id = created["id"]
    assert created["is_active"] is True

    resp = await client.patch(
        f"/api/v1/chatbots/{chatbot_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_chatbot_theme_config(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/chatbots/:id updates the theme configuration."""
    created = await create_test_chatbot(client, auth_headers)
    chatbot_id = created["id"]

    new_theme = {
        "primary_color": "#10b981",
        "text_color": "#111827",
        "position": "bottom-left",
        "size": "small",
    }
    resp = await client.patch(
        f"/api/v1/chatbots/{chatbot_id}",
        json={"theme_config": new_theme},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["theme_config"]["primary_color"] == "#10b981"


@pytest.mark.asyncio
async def test_update_chatbot_not_found(client: AsyncClient, auth_headers: dict):
    """PATCH /api/v1/chatbots/:id returns 404 for nonexistent chatbot."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/chatbots/{fake_id}",
        json={"name": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_chatbot_welcome_message(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/chatbots/:id updates the welcome message."""
    created = await create_test_chatbot(client, auth_headers)
    chatbot_id = created["id"]

    resp = await client.patch(
        f"/api/v1/chatbots/{chatbot_id}",
        json={"welcome_message": "Hey there! What can I do for you?"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["welcome_message"] == "Hey there! What can I do for you?"


# ── Delete Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_chatbot(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/chatbots/:id removes the chatbot (204 No Content)."""
    created = await create_test_chatbot(client, auth_headers, name="Doomed Bot")
    chatbot_id = created["id"]

    resp = await client.delete(
        f"/api/v1/chatbots/{chatbot_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(
        f"/api/v1/chatbots/{chatbot_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_chatbot_not_found(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/chatbots/:id returns 404 for nonexistent chatbot."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/chatbots/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_chatbot_other_user(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/chatbots/:id returns 404 when deleting another user's chatbot."""
    created = await create_test_chatbot(client, auth_headers, name="Protected Bot")
    chatbot_id = created["id"]

    user2_headers = await register_and_login(client, "intruder@example.com")
    resp = await client.delete(
        f"/api/v1/chatbots/{chatbot_id}", headers=user2_headers
    )
    assert resp.status_code == 404

    # Original user can still see it
    resp = await client.get(
        f"/api/v1/chatbots/{chatbot_id}", headers=auth_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_chatbot_decrements_count(
    client: AsyncClient, auth_headers: dict
):
    """Deleting a chatbot reduces the total count in the list endpoint."""
    bot1 = await create_test_chatbot(client, auth_headers, name="Bot 1")
    await create_test_chatbot(client, auth_headers, name="Bot 2")

    resp = await client.get("/api/v1/chatbots", headers=auth_headers)
    assert resp.json()["total"] == 2

    await client.delete(f"/api/v1/chatbots/{bot1['id']}", headers=auth_headers)

    resp = await client.get("/api/v1/chatbots", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Bot 2"


# ── Widget Key Uniqueness ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_widget_keys_are_unique(client: AsyncClient, auth_headers: dict):
    """Each chatbot receives a unique widget_key."""
    bot1 = await create_test_chatbot(client, auth_headers, name="Bot A")
    bot2 = await create_test_chatbot(client, auth_headers, name="Bot B")

    assert bot1["widget_key"] != bot2["widget_key"]
    assert len(bot1["widget_key"]) >= 8
    assert len(bot2["widget_key"]) >= 8
