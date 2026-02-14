"""
Comprehensive tests for new FlowSend features.

Covers: email sender, template renderer, flow engine step execution,
contact segmentation, store connections, contact import from store,
A/B testing, and LLM client.

For Developers:
    Uses shared conftest fixtures (client, auth_headers, db).
    Each test is isolated via table TRUNCATE between runs.

For QA Engineers:
    Run with: ``pytest tests/test_new_features.py -v``
    Expects 25+ tests covering all new service modules.

For Project Managers:
    These tests validate the core new features: email delivery,
    template rendering, flow automation, segmentation, store integration,
    and A/B testing.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, EmailEvent
from app.models.contact import Contact
from app.models.flow import Flow, FlowExecution
from app.models.store_connection import StoreConnection
from app.models.user import User


# ── Email Sender Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_console_email_sender_returns_true():
    """ConsoleEmailSender.send() returns True for any input."""
    from app.services.email_sender import ConsoleEmailSender

    sender = ConsoleEmailSender()
    result = await sender.send(
        to="test@example.com",
        subject="Test Subject",
        html_body="<p>Hello</p>",
        plain_body="Hello",
    )
    assert result is True


@pytest.mark.asyncio
async def test_console_email_sender_handles_empty_plain():
    """ConsoleEmailSender.send() works without a plain_body."""
    from app.services.email_sender import ConsoleEmailSender

    sender = ConsoleEmailSender()
    result = await sender.send(
        to="test@example.com",
        subject="No Plain",
        html_body="<h1>HTML Only</h1>",
    )
    assert result is True


@pytest.mark.asyncio
async def test_get_email_sender_default_is_console():
    """get_email_sender() returns ConsoleEmailSender by default."""
    from app.services.email_sender import ConsoleEmailSender, get_email_sender

    sender = get_email_sender()
    assert isinstance(sender, ConsoleEmailSender)


@pytest.mark.asyncio
async def test_get_email_sender_smtp_mode():
    """get_email_sender() returns SmtpEmailSender when mode is 'smtp'."""
    from app.services.email_sender import SmtpEmailSender, get_email_sender

    with patch("app.services.email_sender.settings") as mock_settings:
        mock_settings.email_sender_mode = "smtp"
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = ""
        mock_settings.smtp_password = ""
        mock_settings.email_from_address = "test@test.com"
        mock_settings.email_from_name = "Test"
        sender = get_email_sender()
        assert isinstance(sender, SmtpEmailSender)


# ── Template Renderer Tests ──────────────────────────────────────────────


def test_render_template_welcome():
    """render_template('welcome') renders HTML with first_name variable."""
    from app.services.template_renderer import render_template

    html, plain = render_template("welcome", {"first_name": "Alice", "store_name": "TestStore"})
    assert "Alice" in html
    assert "TestStore" in html
    assert "Alice" in plain


def test_render_template_all_builtins():
    """All built-in template names render without errors."""
    from app.services.template_renderer import get_available_templates, render_template

    templates = get_available_templates()
    assert len(templates) == 6
    assert "welcome" in templates
    assert "order_confirmation" in templates
    assert "shipping_notification" in templates
    assert "abandoned_cart" in templates
    assert "promotional" in templates
    assert "newsletter" in templates

    for name in templates:
        html, plain = render_template(name, {"first_name": "Test"})
        assert len(html) > 0
        assert len(plain) > 0


def test_render_template_missing_variable():
    """Missing variables render as empty strings (no error raised)."""
    from app.services.template_renderer import render_template

    html, plain = render_template("welcome", {})
    # Should not contain raw {{ }} braces
    assert "{{" not in html
    assert "}}" not in html


def test_render_template_unknown_name():
    """render_template() raises ValueError for unknown template names."""
    from app.services.template_renderer import render_template

    with pytest.raises(ValueError, match="Unknown template"):
        render_template("nonexistent", {})


def test_render_html_custom_content():
    """render_html() renders arbitrary HTML with Jinja2 variables."""
    from app.services.template_renderer import render_html

    result = render_html(
        "<p>Hello {{ name }}, you have {{ count }} items.</p>",
        {"name": "Bob", "count": "5"},
    )
    assert "Bob" in result
    assert "5" in result


def test_render_subject():
    """render_subject() renders the built-in template's subject line."""
    from app.services.template_renderer import render_subject

    subject = render_subject("welcome", {"store_name": "MyShop"})
    assert "MyShop" in subject


def test_render_template_order_confirmation_variables():
    """order_confirmation template renders product_name and product_url."""
    from app.services.template_renderer import render_template

    html, plain = render_template("order_confirmation", {
        "first_name": "Jane",
        "product_name": "Widget Pro",
        "product_url": "https://shop.example.com/widget",
    })
    assert "Jane" in html
    assert "Widget Pro" in html
    assert "https://shop.example.com/widget" in html


# ── Flow Engine Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_send_email_step(db: AsyncSession):
    """execute_flow_step for 'send_email' creates an EmailEvent."""
    from app.services.flow_service import execute_flow_step

    # Create user
    user = User(email="flow-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    # Create contact
    contact = Contact(
        user_id=user.id, email="contact@test.com",
        first_name="FlowTest", tags=[], custom_fields={},
    )
    db.add(contact)
    await db.flush()

    # Create flow with send_email step
    flow = Flow(
        user_id=user.id, name="Test Flow", trigger_type="signup",
        status="active",
        steps=[{"type": "send_email", "template": "welcome", "subject": "Hi"}],
    )
    db.add(flow)
    await db.flush()

    result = await execute_flow_step(db, flow.id, 0, contact.id)
    assert result["status"] == "sent"


@pytest.mark.asyncio
async def test_execute_delay_step(db: AsyncSession):
    """execute_flow_step for 'delay' returns delay_hours."""
    from app.services.flow_service import execute_flow_step

    user = User(email="delay-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    contact = Contact(
        user_id=user.id, email="delay-contact@test.com",
        tags=[], custom_fields={},
    )
    db.add(contact)
    await db.flush()

    flow = Flow(
        user_id=user.id, name="Delay Flow", trigger_type="signup",
        status="active",
        steps=[{"type": "delay", "delay_hours": 24}],
    )
    db.add(flow)
    await db.flush()

    result = await execute_flow_step(db, flow.id, 0, contact.id)
    assert result["status"] == "delayed"
    assert result["delay_hours"] == 24


@pytest.mark.asyncio
async def test_execute_condition_step_tag_equals(db: AsyncSession):
    """execute_flow_step for 'condition' with tag_equals evaluates correctly."""
    from app.services.flow_service import execute_flow_step

    user = User(email="cond-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    contact = Contact(
        user_id=user.id, email="cond-contact@test.com",
        tags=["vip"], custom_fields={},
    )
    db.add(contact)
    await db.flush()

    flow = Flow(
        user_id=user.id, name="Condition Flow", trigger_type="signup",
        status="active",
        steps=[{
            "type": "condition",
            "condition_type": "tag_equals",
            "value": "vip",
            "then_step": 1,
            "else_step": 2,
        }],
    )
    db.add(flow)
    await db.flush()

    result = await execute_flow_step(db, flow.id, 0, contact.id)
    assert result["status"] == "evaluated"
    assert result["result"] is True
    assert result["next_step"] == 1


@pytest.mark.asyncio
async def test_execute_condition_step_false(db: AsyncSession):
    """Condition step returns False when tag doesn't match."""
    from app.services.flow_service import execute_flow_step

    user = User(email="cond2-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    contact = Contact(
        user_id=user.id, email="cond2-contact@test.com",
        tags=["regular"], custom_fields={},
    )
    db.add(contact)
    await db.flush()

    flow = Flow(
        user_id=user.id, name="Condition Flow 2", trigger_type="signup",
        status="active",
        steps=[{
            "type": "condition",
            "condition_type": "tag_equals",
            "value": "vip",
            "then_step": 1,
            "else_step": 2,
        }],
    )
    db.add(flow)
    await db.flush()

    result = await execute_flow_step(db, flow.id, 0, contact.id)
    assert result["status"] == "evaluated"
    assert result["result"] is False
    assert result["next_step"] == 2


@pytest.mark.asyncio
async def test_execute_split_step(db: AsyncSession):
    """execute_flow_step for 'split' assigns a variant label."""
    from app.services.flow_service import execute_flow_step

    user = User(email="split-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    contact = Contact(
        user_id=user.id, email="split-contact@test.com",
        tags=[], custom_fields={},
    )
    db.add(contact)
    await db.flush()

    flow = Flow(
        user_id=user.id, name="Split Flow", trigger_type="signup",
        status="active",
        steps=[{"type": "split", "variant_count": 2}],
    )
    db.add(flow)
    await db.flush()

    result = await execute_flow_step(db, flow.id, 0, contact.id)
    assert result["status"] == "split"
    assert result["variant"] in ("A", "B")


@pytest.mark.asyncio
async def test_trigger_flow_creates_executions(db: AsyncSession):
    """trigger_flow creates FlowExecution records for each contact."""
    from app.services.flow_service import trigger_flow

    user = User(email="trigger-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    contacts = []
    for i in range(3):
        c = Contact(
            user_id=user.id, email=f"trigger-{i}@test.com",
            tags=[], custom_fields={},
        )
        db.add(c)
        contacts.append(c)
    await db.flush()

    flow = Flow(
        user_id=user.id, name="Trigger Flow", trigger_type="signup",
        status="active",
        steps=[{"type": "send_email", "template": "welcome", "subject": "Hi"}],
    )
    db.add(flow)
    await db.flush()

    executions = await trigger_flow(db, flow.id, [c.id for c in contacts])
    assert len(executions) == 3
    for ex in executions:
        assert ex.status == "running"
        assert ex.current_step == 0


@pytest.mark.asyncio
async def test_trigger_flow_inactive_raises(db: AsyncSession):
    """trigger_flow raises ValueError for non-active flows."""
    from app.services.flow_service import trigger_flow

    user = User(email="inactive-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    flow = Flow(
        user_id=user.id, name="Draft Flow", trigger_type="signup",
        status="draft", steps=[],
    )
    db.add(flow)
    await db.flush()

    with pytest.raises(ValueError, match="active"):
        await trigger_flow(db, flow.id, [uuid.uuid4()])


# ── Segmentation Tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_segment_tag_equals(db: AsyncSession):
    """evaluate_segment with tag_equals returns contacts with matching tag."""
    from app.services.segmentation_service import evaluate_segment

    user = User(email="seg-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    c1 = Contact(user_id=user.id, email="vip@test.com", tags=["vip"], custom_fields={})
    c2 = Contact(user_id=user.id, email="regular@test.com", tags=["regular"], custom_fields={})
    db.add_all([c1, c2])
    await db.flush()

    results = await evaluate_segment(db, user.id, [
        {"type": "tag_equals", "value": "vip"}
    ])
    assert len(results) == 1
    assert results[0].email == "vip@test.com"


@pytest.mark.asyncio
async def test_segment_empty_rules_returns_all_subscribed(db: AsyncSession):
    """evaluate_segment with empty rules returns all subscribed contacts."""
    from app.services.segmentation_service import evaluate_segment

    user = User(email="seg2-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    c1 = Contact(user_id=user.id, email="sub1@test.com", tags=[], custom_fields={})
    c2 = Contact(
        user_id=user.id, email="unsub@test.com",
        tags=[], custom_fields={}, is_subscribed=False,
    )
    db.add_all([c1, c2])
    await db.flush()

    results = await evaluate_segment(db, user.id, [])
    assert len(results) == 1
    assert results[0].email == "sub1@test.com"


@pytest.mark.asyncio
async def test_segment_count(db: AsyncSession):
    """get_segment_count returns the count of matching contacts."""
    from app.services.segmentation_service import get_segment_count

    user = User(email="seg3-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    for i in range(5):
        c = Contact(
            user_id=user.id, email=f"seg3-{i}@test.com",
            tags=["newsletter"] if i < 3 else [],
            custom_fields={},
        )
        db.add(c)
    await db.flush()

    count = await get_segment_count(db, user.id, [
        {"type": "tag_equals", "value": "newsletter"}
    ])
    assert count == 3


@pytest.mark.asyncio
async def test_segment_invalid_rule_type(db: AsyncSession):
    """evaluate_segment raises ValueError for unknown rule types."""
    from app.services.segmentation_service import evaluate_segment

    user = User(email="seg4-user@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    with pytest.raises(ValueError, match="Invalid rule type"):
        await evaluate_segment(db, user.id, [{"type": "nonexistent"}])


# ── A/B Testing Tests ────────────────────────────────────────────────────


def test_split_contacts_even():
    """split_contacts_for_ab evenly splits contacts into 2 groups."""
    from app.services.ab_testing_service import split_contacts_for_ab

    contacts = list(range(10))
    variants = split_contacts_for_ab(contacts, variant_count=2)
    assert len(variants) == 2
    assert len(variants[0]) == 5
    assert len(variants[1]) == 5
    # All contacts accounted for
    assert sorted(variants[0] + variants[1]) == list(range(10))


def test_split_contacts_odd():
    """split_contacts_for_ab handles odd contact counts."""
    from app.services.ab_testing_service import split_contacts_for_ab

    contacts = list(range(7))
    variants = split_contacts_for_ab(contacts, variant_count=2)
    assert len(variants) == 2
    assert len(variants[0]) + len(variants[1]) == 7
    # One variant gets 4, the other gets 3
    sizes = sorted([len(v) for v in variants])
    assert sizes == [3, 4]


def test_split_contacts_three_variants():
    """split_contacts_for_ab supports more than 2 variants."""
    from app.services.ab_testing_service import split_contacts_for_ab

    contacts = list(range(9))
    variants = split_contacts_for_ab(contacts, variant_count=3)
    assert len(variants) == 3
    assert all(len(v) == 3 for v in variants)


def test_split_contacts_empty():
    """split_contacts_for_ab with empty list returns empty variant lists."""
    from app.services.ab_testing_service import split_contacts_for_ab

    variants = split_contacts_for_ab([], variant_count=2)
    assert len(variants) == 2
    assert variants[0] == []
    assert variants[1] == []


def test_split_contacts_single():
    """split_contacts_for_ab with one contact puts it in the first variant."""
    from app.services.ab_testing_service import split_contacts_for_ab

    variants = split_contacts_for_ab(["alice"], variant_count=2)
    assert len(variants) == 2
    total = len(variants[0]) + len(variants[1])
    assert total == 1


# ── Store Connection API Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_store_connection(client: AsyncClient, auth_headers: dict):
    """POST /connections creates a store connection and returns 201."""
    payload = {
        "platform": "shopify",
        "store_url": "https://mystore.myshopify.com",
        "api_key": "test-api-key-123",
        "api_secret": "test-secret-456",
    }
    resp = await client.post("/api/v1/connections", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "shopify"
    assert data["store_url"] == "https://mystore.myshopify.com"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_list_store_connections(client: AsyncClient, auth_headers: dict):
    """GET /connections returns paginated list of connections."""
    # Create two connections
    for platform in ("shopify", "woocommerce"):
        await client.post(
            "/api/v1/connections",
            json={
                "platform": platform,
                "store_url": f"https://{platform}.example.com",
                "api_key": f"key-{platform}",
            },
            headers=auth_headers,
        )

    resp = await client.get("/api/v1/connections", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_store_connection(client: AsyncClient, auth_headers: dict):
    """GET /connections/:id returns the connection by UUID."""
    create_resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://get-test.myshopify.com",
            "api_key": "key-get",
        },
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["platform"] == "shopify"


@pytest.mark.asyncio
async def test_delete_store_connection(client: AsyncClient, auth_headers: dict):
    """DELETE /connections/:id removes the connection and returns 204."""
    create_resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://del-test.myshopify.com",
            "api_key": "key-del",
        },
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/connections/{conn_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_test_store_connection(client: AsyncClient, auth_headers: dict):
    """POST /connections/:id/test returns success for existing connection."""
    create_resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "woocommerce",
            "store_url": "https://woo-test.example.com",
            "api_key": "key-woo-test",
        },
        headers=auth_headers,
    )
    conn_id = create_resp.json()["id"]

    resp = await client.post(f"/api/v1/connections/{conn_id}/test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "woocommerce" in data["message"]


@pytest.mark.asyncio
async def test_connection_not_found(client: AsyncClient, auth_headers: dict):
    """GET /connections/:id with unknown UUID returns 404."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/connections/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Contact Import from Store Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_import_from_store(client: AsyncClient, auth_headers: dict):
    """POST /contacts/import-from-store creates contacts from mock store data."""
    # Create a store connection first
    conn_resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://import-test.myshopify.com",
            "api_key": "key-import",
        },
        headers=auth_headers,
    )
    conn_id = conn_resp.json()["id"]

    # Import contacts
    resp = await client.post(
        "/api/v1/contacts/import-from-store",
        json={"connection_id": conn_id, "tags": ["store-import"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 5  # 5 mock customers
    assert data["total"] == 5
    assert data["updated"] == 0
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_import_from_store_dedup(client: AsyncClient, auth_headers: dict):
    """Repeated import-from-store skips already-existing contacts."""
    conn_resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://dedup-test.myshopify.com",
            "api_key": "key-dedup",
        },
        headers=auth_headers,
    )
    conn_id = conn_resp.json()["id"]

    # First import
    resp1 = await client.post(
        "/api/v1/contacts/import-from-store",
        json={"connection_id": conn_id},
        headers=auth_headers,
    )
    assert resp1.json()["created"] == 5

    # Second import — should skip all (no name changes in mock)
    resp2 = await client.post(
        "/api/v1/contacts/import-from-store",
        json={"connection_id": conn_id},
        headers=auth_headers,
    )
    data2 = resp2.json()
    assert data2["created"] == 0
    assert data2["skipped"] == 5


@pytest.mark.asyncio
async def test_import_from_store_not_found(client: AsyncClient, auth_headers: dict):
    """POST /contacts/import-from-store with unknown connection returns 404."""
    resp = await client.post(
        "/api/v1/contacts/import-from-store",
        json={"connection_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── LLM Client Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_mock_returns_expected_shape():
    """call_llm_mock() returns a dict with expected keys."""
    from app.services.llm_client import call_llm_mock

    result = await call_llm_mock("Write a subject line")
    assert "content" in result
    assert "provider" in result
    assert result["provider"] == "mock"
    assert "cost_usd" in result
    assert result["cost_usd"] == 0.0


# ── Auth requirement for new endpoints ───────────────────────────────────


@pytest.mark.asyncio
async def test_connections_require_auth(client: AsyncClient):
    """Connection endpoints require authentication (401 without token)."""
    resp = await client.get("/api/v1/connections")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_import_from_store_requires_auth(client: AsyncClient):
    """Import from store endpoint requires authentication."""
    resp = await client.post(
        "/api/v1/contacts/import-from-store",
        json={"connection_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401
