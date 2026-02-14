"""
Conversation management API endpoint tests.

Validates listing, detail view (with messages), ending, and satisfaction
rating of conversations. Conversations are created indirectly via the
widget chat endpoint, then managed through the authenticated conversation
API.

For QA Engineers:
    Run with: pytest tests/test_conversations.py -v
    Tests cover conversation listing with pagination and chatbot filtering,
    detail view with message history, ending active conversations, and
    satisfaction rating validation.

For Developers:
    Conversations are created by posting chat messages through the public
    widget endpoint. The test helper `create_chatbot_and_conversation`
    wires up a chatbot, sends a message, and returns the IDs needed
    for further testing.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ──────────────────────────────────────────────────────────


async def create_test_chatbot(
    client: AsyncClient,
    headers: dict,
    name: str = "Conv Bot",
) -> dict:
    """
    Create a chatbot via the API and return the response JSON.

    Args:
        client: The httpx test client.
        headers: Authorization headers.
        name: Chatbot name.

    Returns:
        The created chatbot response as a dict.
    """
    resp = await client.post(
        "/api/v1/chatbots",
        json={
            "name": name,
            "personality": "friendly",
            "welcome_message": "Hello!",
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Chatbot creation failed: {resp.text}"
    return resp.json()


async def send_widget_message(
    client: AsyncClient,
    widget_key: str,
    visitor_id: str,
    message: str,
    visitor_name: str | None = None,
) -> dict:
    """
    Send a message through the public widget chat endpoint.

    This creates a conversation (on first message for a visitor) and
    returns the chat response containing the conversation_id.

    Args:
        client: The httpx test client.
        widget_key: The chatbot's widget key.
        visitor_id: Session-based visitor identifier.
        message: The visitor's message text.
        visitor_name: Optional visitor display name.

    Returns:
        The chat response dict with conversation_id and AI message.
    """
    payload: dict = {
        "widget_key": widget_key,
        "visitor_id": visitor_id,
        "message": message,
    }
    if visitor_name:
        payload["visitor_name"] = visitor_name

    resp = await client.post("/api/v1/widget/chat", json=payload)
    assert resp.status_code == 200, f"Widget chat failed: {resp.text}"
    return resp.json()


async def create_chatbot_and_conversation(
    client: AsyncClient,
    headers: dict,
    chatbot_name: str = "Conv Bot",
    visitor_id: str = "visitor-001",
    message: str = "Hi, I need help!",
) -> tuple[dict, str]:
    """
    Create a chatbot and start a conversation by sending a widget message.

    Args:
        client: The httpx test client.
        headers: Authorization headers.
        chatbot_name: Chatbot name.
        visitor_id: Visitor session identifier.
        message: Initial message from the visitor.

    Returns:
        Tuple of (chatbot dict, conversation_id string).
    """
    chatbot = await create_test_chatbot(client, headers, name=chatbot_name)
    chat_resp = await send_widget_message(
        client, chatbot["widget_key"], visitor_id, message
    )
    return chatbot, chat_resp["conversation_id"]


# ── List Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/conversations returns empty list for user with no conversations."""
    resp = await client.get("/api/v1/conversations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_conversations_with_data(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/conversations returns conversations from the user's chatbots."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    resp = await client.get("/api/v1/conversations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert conv_id in ids


@pytest.mark.asyncio
async def test_list_conversations_filter_by_chatbot(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/conversations?chatbot_id=X filters by chatbot."""
    chatbot_a, conv_a = await create_chatbot_and_conversation(
        client, auth_headers, chatbot_name="Bot A", visitor_id="v-a"
    )
    chatbot_b, conv_b = await create_chatbot_and_conversation(
        client, auth_headers, chatbot_name="Bot B", visitor_id="v-b"
    )

    # Filter by chatbot A
    resp = await client.get(
        f"/api/v1/conversations?chatbot_id={chatbot_a['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["chatbot_id"] == chatbot_a["id"]

    # Filter by chatbot B
    resp = await client.get(
        f"/api/v1/conversations?chatbot_id={chatbot_b['id']}",
        headers=auth_headers,
    )
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["chatbot_id"] == chatbot_b["id"]


@pytest.mark.asyncio
async def test_list_conversations_pagination(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/conversations supports pagination."""
    chatbot = await create_test_chatbot(client, auth_headers)

    # Create 4 conversations with different visitors
    for i in range(4):
        await send_widget_message(
            client, chatbot["widget_key"], f"visitor-{i}", f"Message {i}"
        )

    resp = await client.get(
        "/api/v1/conversations?page=1&page_size=2", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 4
    assert data["page"] == 1

    resp = await client.get(
        "/api/v1/conversations?page=2&page_size=2", headers=auth_headers
    )
    data = resp.json()
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_conversations_user_scoping(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/conversations does not return other users' conversations."""
    _, conv_id = await create_chatbot_and_conversation(
        client, auth_headers, visitor_id="user1-visitor"
    )

    user2_headers = await register_and_login(client, "conv-user2@example.com")
    resp = await client.get("/api/v1/conversations", headers=user2_headers)
    data = resp.json()
    assert data["total"] == 0
    assert conv_id not in [item["id"] for item in data["items"]]


# ── Detail Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_conversation_detail(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/conversations/:id returns the conversation with messages."""
    chatbot, conv_id = await create_chatbot_and_conversation(
        client, auth_headers, message="What products do you have?"
    )

    resp = await client.get(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == conv_id
    assert data["chatbot_id"] == chatbot["id"]
    assert data["status"] == "active"
    assert "messages" in data
    # Should have at least the user message and the AI response
    assert len(data["messages"]) >= 2

    # First message should be from the user
    user_msg = data["messages"][0]
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "What products do you have?"

    # Second message should be from the assistant
    ai_msg = data["messages"][1]
    assert ai_msg["role"] == "assistant"
    assert len(ai_msg["content"]) > 0


@pytest.mark.asyncio
async def test_get_conversation_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/conversations/:id returns 404 for nonexistent conversation."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/conversations/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_conversation_other_user(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/conversations/:id returns 404 for another user's conversation."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    user2_headers = await register_and_login(client, "conv-other@example.com")
    resp = await client.get(
        f"/api/v1/conversations/{conv_id}", headers=user2_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_conversation_message_count_increments(
    client: AsyncClient, auth_headers: dict
):
    """Sending multiple messages increments the conversation message_count."""
    chatbot = await create_test_chatbot(client, auth_headers)
    visitor_id = "repeat-visitor"

    # Send first message
    chat1 = await send_widget_message(
        client, chatbot["widget_key"], visitor_id, "First question"
    )
    conv_id = chat1["conversation_id"]

    # Send second message (same conversation)
    await send_widget_message(
        client, chatbot["widget_key"], visitor_id, "Follow-up question"
    )

    # Check message count
    resp = await client.get(
        f"/api/v1/conversations/{conv_id}", headers=auth_headers
    )
    data = resp.json()
    # 2 user messages + 2 AI messages = 4 total
    assert data["message_count"] == 4
    assert len(data["messages"]) == 4


# ── End Conversation Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_end_conversation(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/conversations/:id/end sets status to ended."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/end", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ended"
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_conversation_already_ended(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/conversations/:id/end returns 400 if already ended."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    # End it
    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/end", headers=auth_headers
    )
    assert resp.status_code == 200

    # Try ending again
    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/end", headers=auth_headers
    )
    assert resp.status_code == 400
    assert "not active" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_end_conversation_not_found(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/conversations/:id/end returns 404 for nonexistent conversation."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/conversations/{fake_id}/end", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Satisfaction Rating Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_conversation(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/conversations/:id/rate sets the satisfaction score."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/rate",
        json={"score": 4.5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["satisfaction_score"] == 4.5


@pytest.mark.asyncio
async def test_rate_conversation_boundaries(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/conversations/:id/rate accepts scores from 1.0 to 5.0."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    # Minimum valid score
    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/rate",
        json={"score": 1.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["satisfaction_score"] == 1.0

    # Maximum valid score
    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/rate",
        json={"score": 5.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["satisfaction_score"] == 5.0


@pytest.mark.asyncio
async def test_rate_conversation_invalid_score_too_low(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/conversations/:id/rate rejects scores below 1.0."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/rate",
        json={"score": 0.5},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rate_conversation_invalid_score_too_high(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/conversations/:id/rate rejects scores above 5.0."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/rate",
        json={"score": 5.5},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rate_conversation_not_found(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/conversations/:id/rate returns 404 for nonexistent conversation."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/conversations/{fake_id}/rate",
        json={"score": 3.0},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rate_conversation_other_user(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/conversations/:id/rate returns 404 for another user's conversation."""
    _, conv_id = await create_chatbot_and_conversation(client, auth_headers)

    user2_headers = await register_and_login(client, "rater@example.com")
    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/rate",
        json={"score": 5.0},
        headers=user2_headers,
    )
    assert resp.status_code == 404


# ── Conversation Response Fields ─────────────────────────────────────


@pytest.mark.asyncio
async def test_conversation_response_fields(
    client: AsyncClient, auth_headers: dict
):
    """Conversation responses contain all expected fields."""
    chatbot, conv_id = await create_chatbot_and_conversation(
        client, auth_headers, visitor_id="field-check"
    )

    resp = await client.get("/api/v1/conversations", headers=auth_headers)
    data = resp.json()
    conv = data["items"][0]

    assert "id" in conv
    assert "chatbot_id" in conv
    assert "visitor_id" in conv
    assert "started_at" in conv
    assert "ended_at" in conv
    assert "message_count" in conv
    assert "satisfaction_score" in conv
    assert "status" in conv
    assert conv["chatbot_id"] == chatbot["id"]
    assert conv["visitor_id"] == "field-check"
    assert conv["status"] == "active"
    assert conv["message_count"] >= 2  # user + assistant
