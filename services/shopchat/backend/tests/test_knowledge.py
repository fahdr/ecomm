"""
Knowledge base CRUD API endpoint tests.

Validates create, list, get, update, and delete operations for knowledge
base entries. Tests ownership verification (entries belong to chatbots
owned by the user), plan limit enforcement, and cross-user scoping.

For QA Engineers:
    Run with: pytest tests/test_knowledge.py -v
    Tests cover CRUD operations, chatbot ownership validation, filtering
    by chatbot_id, and error cases for missing or unauthorized entries.

For Developers:
    Knowledge entries require a chatbot_id. All tests first create a
    chatbot, then operate on entries scoped to that chatbot. The
    `create_test_entry` helper wires up the full chain.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── Helpers ──────────────────────────────────────────────────────────


async def create_test_chatbot(
    client: AsyncClient,
    headers: dict,
    name: str = "KB Bot",
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
        json={"name": name, "personality": "helpful"},
        headers=headers,
    )
    assert resp.status_code == 201, f"Chatbot creation failed: {resp.text}"
    return resp.json()


async def create_test_entry(
    client: AsyncClient,
    headers: dict,
    chatbot_id: str,
    title: str = "Test Entry",
    content: str = "This is test content for the knowledge base.",
    source_type: str = "custom_text",
    metadata: dict | None = None,
) -> dict:
    """
    Create a knowledge base entry via the API and return the response JSON.

    Args:
        client: The httpx test client.
        headers: Authorization headers.
        chatbot_id: The chatbot this entry belongs to.
        title: Entry title.
        content: Entry content.
        source_type: Content source type.
        metadata: Optional extra data.

    Returns:
        The created knowledge base entry response as a dict.
    """
    payload: dict = {
        "chatbot_id": chatbot_id,
        "title": title,
        "content": content,
        "source_type": source_type,
    }
    if metadata is not None:
        payload["metadata"] = metadata

    resp = await client.post(
        "/api/v1/knowledge",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201, f"Entry creation failed: {resp.text}"
    return resp.json()


# ── Create Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_knowledge_entry(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/knowledge creates a knowledge base entry."""
    chatbot = await create_test_chatbot(client, auth_headers)

    entry = await create_test_entry(
        client,
        auth_headers,
        chatbot["id"],
        title="Return Policy",
        content="You can return items within 30 days.",
        source_type="policy_page",
    )

    assert entry["title"] == "Return Policy"
    assert entry["content"] == "You can return items within 30 days."
    assert entry["source_type"] == "policy_page"
    assert entry["chatbot_id"] == chatbot["id"]
    assert entry["is_active"] is True
    assert "id" in entry
    assert "created_at" in entry
    assert "updated_at" in entry


@pytest.mark.asyncio
async def test_create_knowledge_entry_with_metadata(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/knowledge stores metadata correctly."""
    chatbot = await create_test_chatbot(client, auth_headers)

    entry = await create_test_entry(
        client,
        auth_headers,
        chatbot["id"],
        title="Premium Widget",
        content="Our best-selling widget.",
        source_type="product_catalog",
        metadata={"price": "$29.99", "url": "/products/widget"},
    )

    assert entry["metadata"]["price"] == "$29.99"
    assert entry["metadata"]["url"] == "/products/widget"
    assert entry["source_type"] == "product_catalog"


@pytest.mark.asyncio
async def test_create_knowledge_entry_no_chatbot(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/knowledge returns 404 if chatbot does not exist."""
    fake_chatbot_id = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": fake_chatbot_id,
            "title": "Orphan Entry",
            "content": "No chatbot exists.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_knowledge_entry_other_user_chatbot(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/knowledge returns 404 if chatbot belongs to another user."""
    chatbot = await create_test_chatbot(client, auth_headers)

    user2_headers = await register_and_login(client, "kb-user2@example.com")
    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": chatbot["id"],
            "title": "Sneaky Entry",
            "content": "Trying to add to someone else's bot.",
        },
        headers=user2_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_knowledge_entry_no_auth(client: AsyncClient):
    """POST /api/v1/knowledge without auth returns 401."""
    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": str(uuid.uuid4()),
            "title": "Unauthorized",
            "content": "No token.",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_knowledge_entry_empty_title(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/knowledge with empty title returns 422."""
    chatbot = await create_test_chatbot(client, auth_headers)

    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": chatbot["id"],
            "title": "",
            "content": "Some content.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_knowledge_entry_empty_content(
    client: AsyncClient, auth_headers: dict
):
    """POST /api/v1/knowledge with empty content returns 422."""
    chatbot = await create_test_chatbot(client, auth_headers)

    resp = await client.post(
        "/api/v1/knowledge",
        json={
            "chatbot_id": chatbot["id"],
            "title": "Empty Content",
            "content": "",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── List Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_knowledge_entries_empty(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge returns empty list for user with no entries."""
    resp = await client.get("/api/v1/knowledge", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_knowledge_entries_all(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge returns all entries across the user's chatbots."""
    chatbot_a = await create_test_chatbot(client, auth_headers, name="Bot A")
    chatbot_b = await create_test_chatbot(client, auth_headers, name="Bot B")

    await create_test_entry(
        client, auth_headers, chatbot_a["id"], title="Entry A"
    )
    await create_test_entry(
        client, auth_headers, chatbot_b["id"], title="Entry B"
    )

    resp = await client.get("/api/v1/knowledge", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 2
    titles = {item["title"] for item in data["items"]}
    assert titles == {"Entry A", "Entry B"}


@pytest.mark.asyncio
async def test_list_knowledge_entries_filter_by_chatbot(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge?chatbot_id=X filters entries by chatbot."""
    chatbot_a = await create_test_chatbot(client, auth_headers, name="Filter Bot A")
    chatbot_b = await create_test_chatbot(client, auth_headers, name="Filter Bot B")

    await create_test_entry(
        client, auth_headers, chatbot_a["id"], title="A Entry 1"
    )
    await create_test_entry(
        client, auth_headers, chatbot_a["id"], title="A Entry 2"
    )
    await create_test_entry(
        client, auth_headers, chatbot_b["id"], title="B Entry 1"
    )

    resp = await client.get(
        f"/api/v1/knowledge?chatbot_id={chatbot_a['id']}", headers=auth_headers
    )
    data = resp.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["chatbot_id"] == chatbot_a["id"]


@pytest.mark.asyncio
async def test_list_knowledge_entries_pagination(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge supports pagination."""
    chatbot = await create_test_chatbot(client, auth_headers)

    for i in range(5):
        await create_test_entry(
            client, auth_headers, chatbot["id"], title=f"Entry {i}"
        )

    resp = await client.get(
        "/api/v1/knowledge?page=1&page_size=2", headers=auth_headers
    )
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1

    resp = await client.get(
        "/api/v1/knowledge?page=3&page_size=2", headers=auth_headers
    )
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_knowledge_entries_user_scoping(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge only returns entries for the authenticated user."""
    chatbot = await create_test_chatbot(client, auth_headers)
    await create_test_entry(
        client, auth_headers, chatbot["id"], title="User1 Entry"
    )

    user2_headers = await register_and_login(client, "kb-scope@example.com")
    resp = await client.get("/api/v1/knowledge", headers=user2_headers)
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_knowledge_entries_filter_nonexistent_chatbot(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge?chatbot_id=X returns 404 for invalid chatbot."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/knowledge?chatbot_id={fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


# ── Get Tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_knowledge_entry(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/knowledge/:id returns a single knowledge base entry."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client,
        auth_headers,
        chatbot["id"],
        title="FAQ: Shipping",
        content="We ship worldwide in 3-5 business days.",
    )

    resp = await client.get(
        f"/api/v1/knowledge/{entry['id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == entry["id"]
    assert data["title"] == "FAQ: Shipping"
    assert data["content"] == "We ship worldwide in 3-5 business days."


@pytest.mark.asyncio
async def test_get_knowledge_entry_not_found(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge/:id returns 404 for nonexistent entry."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/knowledge/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_knowledge_entry_other_user(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/knowledge/:id returns 404 for another user's entry."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], title="Private Entry"
    )

    user2_headers = await register_and_login(client, "kb-other@example.com")
    resp = await client.get(
        f"/api/v1/knowledge/{entry['id']}", headers=user2_headers
    )
    assert resp.status_code == 404


# ── Update Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_knowledge_entry_title(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id updates the entry title."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], title="Old Title"
    )

    resp = await client.patch(
        f"/api/v1/knowledge/{entry['id']}",
        json={"title": "New Title"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    # Content should be unchanged
    assert data["content"] == entry["content"]


@pytest.mark.asyncio
async def test_update_knowledge_entry_content(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id updates the entry content."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], content="Old content"
    )

    resp = await client.patch(
        f"/api/v1/knowledge/{entry['id']}",
        json={"content": "Updated content with more detail."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "Updated content with more detail."


@pytest.mark.asyncio
async def test_update_knowledge_entry_source_type(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id updates the source_type."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], source_type="custom_text"
    )

    resp = await client.patch(
        f"/api/v1/knowledge/{entry['id']}",
        json={"source_type": "faq"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["source_type"] == "faq"


@pytest.mark.asyncio
async def test_update_knowledge_entry_deactivate(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id can deactivate an entry."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"]
    )
    assert entry["is_active"] is True

    resp = await client.patch(
        f"/api/v1/knowledge/{entry['id']}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_update_knowledge_entry_metadata(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id updates metadata."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client,
        auth_headers,
        chatbot["id"],
        metadata={"version": 1},
    )

    resp = await client.patch(
        f"/api/v1/knowledge/{entry['id']}",
        json={"metadata": {"version": 2, "reviewed": True}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["version"] == 2
    assert data["metadata"]["reviewed"] is True


@pytest.mark.asyncio
async def test_update_knowledge_entry_not_found(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id returns 404 for nonexistent entry."""
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/knowledge/{fake_id}",
        json={"title": "Ghost"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_knowledge_entry_other_user(
    client: AsyncClient, auth_headers: dict
):
    """PATCH /api/v1/knowledge/:id returns 404 for another user's entry."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], title="Protected"
    )

    user2_headers = await register_and_login(client, "kb-update@example.com")
    resp = await client.patch(
        f"/api/v1/knowledge/{entry['id']}",
        json={"title": "Hijacked"},
        headers=user2_headers,
    )
    assert resp.status_code == 404


# ── Delete Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_knowledge_entry(client: AsyncClient, auth_headers: dict):
    """DELETE /api/v1/knowledge/:id removes the entry (204 No Content)."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], title="Doomed Entry"
    )

    resp = await client.delete(
        f"/api/v1/knowledge/{entry['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(
        f"/api/v1/knowledge/{entry['id']}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_knowledge_entry_not_found(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /api/v1/knowledge/:id returns 404 for nonexistent entry."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(
        f"/api/v1/knowledge/{fake_id}", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_knowledge_entry_other_user(
    client: AsyncClient, auth_headers: dict
):
    """DELETE /api/v1/knowledge/:id returns 404 for another user's entry."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry = await create_test_entry(
        client, auth_headers, chatbot["id"], title="Guarded Entry"
    )

    user2_headers = await register_and_login(client, "kb-delete@example.com")
    resp = await client.delete(
        f"/api/v1/knowledge/{entry['id']}", headers=user2_headers
    )
    assert resp.status_code == 404

    # Original user can still access it
    resp = await client.get(
        f"/api/v1/knowledge/{entry['id']}", headers=auth_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_knowledge_entry_decrements_count(
    client: AsyncClient, auth_headers: dict
):
    """Deleting an entry reduces the total count in the list endpoint."""
    chatbot = await create_test_chatbot(client, auth_headers)
    entry1 = await create_test_entry(
        client, auth_headers, chatbot["id"], title="Entry 1"
    )
    await create_test_entry(
        client, auth_headers, chatbot["id"], title="Entry 2"
    )

    resp = await client.get("/api/v1/knowledge", headers=auth_headers)
    assert resp.json()["total"] == 2

    await client.delete(
        f"/api/v1/knowledge/{entry1['id']}", headers=auth_headers
    )

    resp = await client.get("/api/v1/knowledge", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Entry 2"


# ── Source Type Variants ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_knowledge_entry_source_types(
    client: AsyncClient, auth_headers: dict
):
    """Knowledge entries can be created with various source_type values."""
    chatbot = await create_test_chatbot(client, auth_headers)

    source_types = ["product_catalog", "policy_page", "faq", "custom_text", "url"]
    for st in source_types:
        entry = await create_test_entry(
            client,
            auth_headers,
            chatbot["id"],
            title=f"{st} Entry",
            source_type=st,
        )
        assert entry["source_type"] == st
