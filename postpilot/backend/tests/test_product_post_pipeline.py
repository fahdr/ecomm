"""
Tests for the product-to-post pipeline API endpoint.

Covers end-to-end product-to-post generation including multi-platform
support, auto-scheduling, and error handling.

For Developers:
    Tests use the HTTP client fixture. A connected social account is
    required for the from-product endpoint. The auth_and_account fixture
    from test_posts.py provides the setup.

For QA Engineers:
    These tests verify:
    - POST /api/v1/posts/from-product creates posts for each platform (201).
    - Auto-scheduled posts have status 'scheduled' with future times.
    - Non-auto-scheduled posts are created as drafts.
    - Endpoint returns 400 when no social account is connected.
    - Generated captions contain product-relevant content.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import register_and_login


SAMPLE_PRODUCT = {
    "title": "Premium Leather Wallet",
    "description": "Handcrafted genuine leather bifold wallet with RFID blocking.",
    "price": "$49.99",
    "category": "Accessories",
}


@pytest_asyncio.fixture
async def auth_and_account(client: AsyncClient) -> tuple[dict, str]:
    """
    Register a user and connect an Instagram account.

    Returns:
        Tuple of (auth_headers dict, account_id string).
    """
    headers = await register_and_login(client)

    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@pipeline_test_brand",
        },
        headers=headers,
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    return headers, account_id


@pytest.mark.asyncio
async def test_product_to_posts_single_platform(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts/from-product creates a post for a single platform."""
    headers, _ = auth_and_account

    resp = await client.post(
        "/api/v1/posts/from-product",
        json={
            "product_data": SAMPLE_PRODUCT,
            "platforms": ["instagram"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["platforms_processed"] == 1
    assert len(data["posts"]) == 1
    assert data["posts"][0]["platform"] == "instagram"
    assert data["posts"][0]["status"] == "draft"


@pytest.mark.asyncio
async def test_product_to_posts_multiple_platforms(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts/from-product creates posts for multiple platforms."""
    headers, _ = auth_and_account

    resp = await client.post(
        "/api/v1/posts/from-product",
        json={
            "product_data": SAMPLE_PRODUCT,
            "platforms": ["instagram", "facebook", "twitter"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["platforms_processed"] == 3
    assert len(data["posts"]) == 3
    platforms = {p["platform"] for p in data["posts"]}
    assert platforms == {"instagram", "facebook", "twitter"}


@pytest.mark.asyncio
async def test_product_to_posts_auto_schedule(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """POST /api/v1/posts/from-product with auto_schedule creates scheduled posts."""
    headers, _ = auth_and_account

    resp = await client.post(
        "/api/v1/posts/from-product",
        json={
            "product_data": SAMPLE_PRODUCT,
            "platforms": ["instagram"],
            "auto_schedule": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    data = resp.json()
    assert data["posts"][0]["status"] == "scheduled"
    assert data["posts"][0]["scheduled_for"] is not None


@pytest.mark.asyncio
async def test_product_to_posts_no_account(client: AsyncClient):
    """POST /api/v1/posts/from-product returns 400 when no account is connected."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/posts/from-product",
        json={
            "product_data": SAMPLE_PRODUCT,
            "platforms": ["instagram"],
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "no connected" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_product_to_posts_content_contains_product(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """Generated posts contain reference to the product title."""
    headers, _ = auth_and_account

    resp = await client.post(
        "/api/v1/posts/from-product",
        json={
            "product_data": SAMPLE_PRODUCT,
            "platforms": ["instagram"],
            "tone": "engaging",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    post_content = resp.json()["posts"][0]["content"]
    assert "Premium Leather Wallet" in post_content


@pytest.mark.asyncio
async def test_product_to_posts_unauthenticated(client: AsyncClient):
    """POST /api/v1/posts/from-product without auth returns 401."""
    resp = await client.post(
        "/api/v1/posts/from-product",
        json={
            "product_data": SAMPLE_PRODUCT,
            "platforms": ["instagram"],
        },
    )
    assert resp.status_code == 401
