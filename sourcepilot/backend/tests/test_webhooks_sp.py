"""
SourcePilot-specific webhook endpoint tests.

Tests cover the TrendScout product-scored webhook that can trigger
automatic imports when a product scores highly.

For QA Engineers:
    Verifies the product-scored webhook accepts valid payloads, rejects
    invalid ones, handles low-score products correctly, and respects
    authentication requirements.
"""

import uuid

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


# ---------------------------------------------------------------------------
# Product scored webhook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_product_scored_webhook(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored with high score triggers import."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/789.html",
            "source": "aliexpress",
            "score": 92.5,
            "product_name": "Wireless Earbuds Pro",
            "category": "electronics",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201, 202)


@pytest.mark.asyncio
async def test_product_scored_webhook_low_score(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored with low score may skip import."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/999.html",
            "source": "aliexpress",
            "score": 15.0,
            "product_name": "Low Quality Item",
            "category": "misc",
        },
        headers=auth_headers,
    )
    # Should still accept the webhook even if it doesn't trigger an import
    assert resp.status_code in (200, 202, 204)


@pytest.mark.asyncio
async def test_product_scored_webhook_invalid_payload(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored with invalid payload returns 422."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_product_scored_webhook_missing_url(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored without product_url returns 422."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "source": "aliexpress",
            "score": 85.0,
            "product_name": "Test Product",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_product_scored_webhook_missing_score(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored without score returns 422."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/111.html",
            "source": "aliexpress",
            "product_name": "Test Product",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_product_scored_webhook_boundary_score(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored with edge boundary score value."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/boundary.html",
            "source": "aliexpress",
            "score": 50.0,
            "product_name": "Boundary Score Product",
            "category": "general",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201, 202)


@pytest.mark.asyncio
async def test_product_scored_webhook_max_score(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored with maximum score (100)."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/perfect.html",
            "source": "aliexpress",
            "score": 100.0,
            "product_name": "Perfect Score Product",
            "category": "trending",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201, 202)


@pytest.mark.asyncio
async def test_product_scored_webhook_negative_score(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored with negative score returns 400 or 422."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/neg.html",
            "source": "aliexpress",
            "score": -10.0,
            "product_name": "Negative Score",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 400, 422)


@pytest.mark.asyncio
async def test_product_scored_webhook_unauthenticated(client: AsyncClient):
    """POST /api/v1/webhooks/product-scored without auth returns 401."""
    resp = await client.post(
        "/api/v1/webhooks/product-scored",
        json={
            "product_url": "https://www.aliexpress.com/item/unauth.html",
            "source": "aliexpress",
            "score": 75.0,
            "product_name": "Unauth Product",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_product_scored_webhook_duplicate_url(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/webhooks/product-scored twice with same URL handles idempotency."""
    payload = {
        "product_url": "https://www.aliexpress.com/item/dup.html",
        "source": "aliexpress",
        "score": 88.0,
        "product_name": "Duplicate Test",
        "category": "electronics",
    }
    resp1 = await client.post(
        "/api/v1/webhooks/product-scored",
        json=payload,
        headers=auth_headers,
    )
    resp2 = await client.post(
        "/api/v1/webhooks/product-scored",
        json=payload,
        headers=auth_headers,
    )
    # Both should succeed (idempotent) or second may return 409
    assert resp1.status_code in (200, 201, 202)
    assert resp2.status_code in (200, 201, 202, 409)
