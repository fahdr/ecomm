"""
Platform webhook endpoint tests for FlowSend.

Tests cover HMAC-SHA256 signature verification and event routing for
platform lifecycle events dispatched by the dropshipping platform bridge.

For QA Engineers:
    - Verifies signature validation (valid, invalid, missing).
    - Verifies correct event routing:
        order.created   -> post_purchase_flow_queued
        order.shipped   -> shipping_notification_queued
        customer.created -> welcome_flow_queued
    - Verifies unknown events return empty actions.
    - Verifies malformed JSON returns 400.

For Developers:
    Uses the ``dev-platform-bridge-secret`` default from BaseServiceConfig
    to compute test signatures. The ``_sign`` helper generates valid
    HMAC-SHA256 signatures for test payloads.
"""

import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient

from app.config import settings


def _sign(payload: bytes) -> str:
    """Compute a valid HMAC-SHA256 signature for the given payload.

    Args:
        payload: Raw request body bytes.

    Returns:
        Signature string in ``sha256=<hex-digest>`` format.
    """
    digest = hmac.new(
        settings.platform_webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


@pytest.mark.asyncio
async def test_platform_webhook_order_created(client: AsyncClient):
    """POST /webhooks/platform-events with order.created returns post_purchase_flow_queued."""
    payload = json.dumps({
        "event": "order.created",
        "data": {"order_id": "ord_123", "customer_email": "test@example.com"},
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": _sign(payload),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "post_purchase_flow_queued" in data["actions"]


@pytest.mark.asyncio
async def test_platform_webhook_order_shipped(client: AsyncClient):
    """POST /webhooks/platform-events with order.shipped returns shipping_notification_queued."""
    payload = json.dumps({
        "event": "order.shipped",
        "data": {"order_id": "ord_123", "tracking_number": "1Z999AA10123456784"},
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": _sign(payload),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "shipping_notification_queued" in data["actions"]


@pytest.mark.asyncio
async def test_platform_webhook_customer_created(client: AsyncClient):
    """POST /webhooks/platform-events with customer.created returns welcome_flow_queued."""
    payload = json.dumps({
        "event": "customer.created",
        "data": {"customer_id": "cust_123", "email": "new@example.com"},
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": _sign(payload),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "welcome_flow_queued" in data["actions"]


@pytest.mark.asyncio
async def test_platform_webhook_unknown_event(client: AsyncClient):
    """POST /webhooks/platform-events with unknown event returns empty actions."""
    payload = json.dumps({
        "event": "product.created",
        "data": {"product_id": "prod_456"},
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": _sign(payload),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["actions"] == []


@pytest.mark.asyncio
async def test_platform_webhook_invalid_signature(client: AsyncClient):
    """POST /webhooks/platform-events with wrong signature returns 401."""
    payload = json.dumps({
        "event": "order.created",
        "data": {"order_id": "ord_123"},
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid platform signature"


@pytest.mark.asyncio
async def test_platform_webhook_missing_signature(client: AsyncClient):
    """POST /webhooks/platform-events without signature header returns 401."""
    payload = json.dumps({
        "event": "order.created",
        "data": {"order_id": "ord_123"},
    }).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_platform_webhook_malformed_signature_prefix(client: AsyncClient):
    """POST /webhooks/platform-events with wrong prefix returns 401."""
    payload = json.dumps({"event": "order.created", "data": {}}).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": "md5=abc123",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_platform_webhook_invalid_json(client: AsyncClient):
    """POST /webhooks/platform-events with invalid JSON returns 400."""
    payload = b"not valid json {"
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": _sign(payload),
        },
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid JSON payload"


@pytest.mark.asyncio
async def test_platform_webhook_empty_event(client: AsyncClient):
    """POST /webhooks/platform-events with no event field returns empty actions."""
    payload = json.dumps({"data": {}}).encode()
    resp = await client.post(
        "/api/v1/webhooks/platform-events",
        content=payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": _sign(payload),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["actions"] == []
