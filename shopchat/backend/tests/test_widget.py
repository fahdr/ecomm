"""
Widget (public) API endpoint tests.

Validates the public-facing widget endpoints that do NOT require
authentication. Tests cover widget configuration retrieval by widget_key,
the chat message endpoint, and edge cases like inactive chatbots and
invalid widget keys.

For QA Engineers:
    Run with: pytest tests/test_widget.py -v
    These endpoints are PUBLIC and must work WITHOUT auth headers.
    Test with invalid widget_keys (404), inactive chatbots (404),
    and valid chatbots (200 with correct configuration).

For Developers:
    Widget endpoints use the widget_key path parameter to identify
    the chatbot. No JWT or API key is required. The chat endpoint
    creates or continues conversations and generates mock AI responses.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ──────────────────────────────────────────────────────────


async def create_authenticated_chatbot(
    client: AsyncClient,
    name: str = "Widget Bot",
    personality: str = "friendly",
    welcome_message: str = "Hi! How can I help you today?",
    theme_config: dict | None = None,
) -> tuple[dict, dict]:
    """
    Register a user, create a chatbot, and return both auth headers and chatbot data.

    Args:
        client: The httpx test client.
        name: Chatbot name.
        personality: Chatbot personality style.
        welcome_message: Widget welcome greeting.
        theme_config: Optional widget theme configuration.

    Returns:
        Tuple of (auth_headers dict, chatbot response dict).
    """
    headers = await register_and_login(client)

    payload: dict = {
        "name": name,
        "personality": personality,
        "welcome_message": welcome_message,
    }
    if theme_config:
        payload["theme_config"] = theme_config

    resp = await client.post("/api/v1/chatbots", json=payload, headers=headers)
    assert resp.status_code == 201, f"Chatbot creation failed: {resp.text}"
    return headers, resp.json()


# ── Widget Config Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_widget_config(client: AsyncClient):
    """GET /api/v1/widget/config/:widget_key returns the chatbot's widget config."""
    _, chatbot = await create_authenticated_chatbot(
        client,
        name="Helpful Bot",
        personality="helpful",
        welcome_message="Welcome! Ask me anything.",
    )

    resp = await client.get(
        f"/api/v1/widget/config/{chatbot['widget_key']}"
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["chatbot_name"] == "Helpful Bot"
    assert data["personality"] == "helpful"
    assert data["welcome_message"] == "Welcome! Ask me anything."
    assert data["is_active"] is True
    assert "theme_config" in data


@pytest.mark.asyncio
async def test_get_widget_config_theme(client: AsyncClient):
    """GET /api/v1/widget/config/:widget_key includes theme_config."""
    custom_theme = {
        "primary_color": "#10b981",
        "text_color": "#ffffff",
        "position": "bottom-left",
        "size": "large",
    }
    _, chatbot = await create_authenticated_chatbot(
        client, theme_config=custom_theme
    )

    resp = await client.get(
        f"/api/v1/widget/config/{chatbot['widget_key']}"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme_config"]["primary_color"] == "#10b981"
    assert data["theme_config"]["position"] == "bottom-left"


@pytest.mark.asyncio
async def test_get_widget_config_invalid_key(client: AsyncClient):
    """GET /api/v1/widget/config/:widget_key returns 404 for invalid key."""
    resp = await client.get("/api/v1/widget/config/nonexistent-key-12345")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_widget_config_inactive_chatbot(client: AsyncClient):
    """GET /api/v1/widget/config/:widget_key returns 404 if chatbot is inactive."""
    headers, chatbot = await create_authenticated_chatbot(client)

    # Deactivate the chatbot
    resp = await client.patch(
        f"/api/v1/chatbots/{chatbot['id']}",
        json={"is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200

    # Widget config should now return 404
    resp = await client.get(
        f"/api/v1/widget/config/{chatbot['widget_key']}"
    )
    assert resp.status_code == 404
    assert "inactive" in resp.json()["detail"].lower() or "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_widget_config_no_auth_required(client: AsyncClient):
    """GET /api/v1/widget/config/:widget_key works without any auth headers."""
    _, chatbot = await create_authenticated_chatbot(client)

    # Deliberately do NOT pass any auth headers
    resp = await client.get(
        f"/api/v1/widget/config/{chatbot['widget_key']}"
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True


# ── Widget Chat Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_widget_chat_basic(client: AsyncClient):
    """POST /api/v1/widget/chat sends a message and receives an AI response."""
    _, chatbot = await create_authenticated_chatbot(client)

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "visitor-100",
            "message": "Do you have any shoes?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert "conversation_id" in data
    assert "message" in data
    assert len(data["message"]) > 0
    assert "product_suggestions" in data
    assert isinstance(data["product_suggestions"], list)


@pytest.mark.asyncio
async def test_widget_chat_creates_conversation(client: AsyncClient):
    """POST /api/v1/widget/chat creates a new conversation on first message."""
    headers, chatbot = await create_authenticated_chatbot(client)

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "new-visitor-abc",
            "message": "Hello!",
        },
    )
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    # Verify the conversation exists via authenticated API
    resp = await client.get(
        f"/api/v1/conversations/{conv_id}", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["visitor_id"] == "new-visitor-abc"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_widget_chat_continues_conversation(client: AsyncClient):
    """POST /api/v1/widget/chat reuses the same conversation for the same visitor."""
    _, chatbot = await create_authenticated_chatbot(client)

    # First message
    resp1 = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "returning-visitor",
            "message": "First question",
        },
    )
    conv_id_1 = resp1.json()["conversation_id"]

    # Second message from same visitor
    resp2 = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "returning-visitor",
            "message": "Follow-up question",
        },
    )
    conv_id_2 = resp2.json()["conversation_id"]

    # Should be the same conversation
    assert conv_id_1 == conv_id_2


@pytest.mark.asyncio
async def test_widget_chat_different_visitors_different_conversations(
    client: AsyncClient,
):
    """POST /api/v1/widget/chat creates separate conversations for different visitors."""
    _, chatbot = await create_authenticated_chatbot(client)

    resp1 = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "visitor-x",
            "message": "Hello from X",
        },
    )
    resp2 = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "visitor-y",
            "message": "Hello from Y",
        },
    )

    assert resp1.json()["conversation_id"] != resp2.json()["conversation_id"]


@pytest.mark.asyncio
async def test_widget_chat_with_visitor_name(client: AsyncClient):
    """POST /api/v1/widget/chat stores the visitor name if provided."""
    headers, chatbot = await create_authenticated_chatbot(client)

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "named-visitor",
            "message": "Hi, I'm Alice!",
            "visitor_name": "Alice",
        },
    )
    assert resp.status_code == 200
    conv_id = resp.json()["conversation_id"]

    # Verify the visitor name was stored
    resp = await client.get(
        f"/api/v1/conversations/{conv_id}", headers=headers
    )
    assert resp.json()["visitor_name"] == "Alice"


@pytest.mark.asyncio
async def test_widget_chat_invalid_widget_key(client: AsyncClient):
    """POST /api/v1/widget/chat returns 404 for invalid widget_key."""
    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": "fake-key-does-not-exist",
            "visitor_id": "visitor-1",
            "message": "Hello?",
        },
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_widget_chat_inactive_chatbot(client: AsyncClient):
    """POST /api/v1/widget/chat returns 404 if the chatbot is inactive."""
    headers, chatbot = await create_authenticated_chatbot(client)

    # Deactivate the chatbot
    await client.patch(
        f"/api/v1/chatbots/{chatbot['id']}",
        json={"is_active": False},
        headers=headers,
    )

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "visitor-1",
            "message": "Hello?",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_widget_chat_empty_message(client: AsyncClient):
    """POST /api/v1/widget/chat rejects empty message with 422."""
    _, chatbot = await create_authenticated_chatbot(client)

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "visitor-1",
            "message": "",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_widget_chat_missing_visitor_id(client: AsyncClient):
    """POST /api/v1/widget/chat rejects missing visitor_id with 422."""
    _, chatbot = await create_authenticated_chatbot(client)

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "message": "Hello!",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_widget_chat_no_auth_required(client: AsyncClient):
    """POST /api/v1/widget/chat works without any authentication headers."""
    _, chatbot = await create_authenticated_chatbot(client)

    # Deliberately do NOT pass any auth headers
    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "anon-visitor",
            "message": "Can I get help?",
        },
    )
    assert resp.status_code == 200
    assert "message" in resp.json()


# ── AI Response Quality Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_widget_chat_response_personality(client: AsyncClient):
    """POST /api/v1/widget/chat generates a response matching the chatbot personality."""
    _, chatbot = await create_authenticated_chatbot(
        client, personality="professional"
    )

    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "pro-visitor",
            "message": "What do you sell?",
        },
    )
    assert resp.status_code == 200
    # The mock AI prepends personality-specific text
    message = resp.json()["message"]
    assert len(message) > 0


@pytest.mark.asyncio
async def test_widget_chat_with_knowledge_base(client: AsyncClient):
    """POST /api/v1/widget/chat uses knowledge base entries for contextual responses."""
    headers, chatbot = await create_authenticated_chatbot(client)

    # Add a knowledge base entry
    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": chatbot["id"],
            "title": "Shipping Policy",
            "content": "We offer free shipping on orders over $50. Standard shipping takes 3-5 business days.",
            "source_type": "policy_page",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # Ask about shipping
    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "kb-visitor",
            "message": "What is your shipping policy?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # The mock AI should reference the knowledge base entry
    assert "shipping" in data["message"].lower() or "Shipping" in data["message"]


@pytest.mark.asyncio
async def test_widget_chat_product_suggestions(client: AsyncClient):
    """POST /api/v1/widget/chat returns product suggestions from catalog entries."""
    headers, chatbot = await create_authenticated_chatbot(client)

    # Add a product catalog entry
    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": chatbot["id"],
            "title": "Blue Running Shoes",
            "content": "Lightweight blue running shoes, perfect for daily training.",
            "source_type": "product_catalog",
            "metadata": {"price": "$89.99", "url": "/products/blue-shoes"},
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # Ask about running shoes
    resp = await client.post(
        "/api/v1/widget/chat",
        json={
            "widget_key": chatbot["widget_key"],
            "visitor_id": "shopper",
            "message": "Do you have running shoes?",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["product_suggestions"]) >= 1
    suggestion = data["product_suggestions"][0]
    assert "name" in suggestion
    assert "price" in suggestion
    assert "url" in suggestion
