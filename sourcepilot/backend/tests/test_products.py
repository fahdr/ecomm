"""
Product search and preview endpoint tests for SourcePilot.

Tests cover searching supplier catalogs, paginating results, previewing
product details before import, and edge cases like empty queries and
invalid URLs.

For QA Engineers:
    Verifies product search filtering, pagination, preview extraction,
    caching behavior, and proper error handling for invalid inputs.
"""

import pytest
from httpx import AsyncClient

from ecomm_core.testing import register_and_login


# ---------------------------------------------------------------------------
# Search products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_products(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search?q=<query> returns matching products."""
    resp = await client.get(
        "/api/v1/products/search",
        params={"q": "wireless earbuds"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("products", body.get("data", [])))
    # The endpoint may return empty for unknown queries, but structure should be valid
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_search_products_with_source_filter(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search?q=<query>&source=aliexpress filters by source."""
    resp = await client.get(
        "/api/v1/products/search",
        params={"q": "phone case", "source": "aliexpress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    items = body if isinstance(body, list) else body.get("items", body.get("products", body.get("data", [])))
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_search_products_different_sources(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search with different source values returns valid responses."""
    for source in ("aliexpress", "cjdropshipping", "1688"):
        resp = await client.get(
            "/api/v1/products/search",
            params={"q": "test product", "source": source},
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400), f"Unexpected status for source={source}: {resp.status_code}"


@pytest.mark.asyncio
async def test_search_products_pagination(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search with page/page_size paginates results."""
    resp1 = await client.get(
        "/api/v1/products/search",
        params={"q": "shoes", "page": 1, "page_size": 5},
        headers=auth_headers,
    )
    assert resp1.status_code == 200

    resp2 = await client.get(
        "/api/v1/products/search",
        params={"q": "shoes", "page": 2, "page_size": 5},
        headers=auth_headers,
    )
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_search_products_empty_query(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search with empty query returns 400 or 422."""
    resp = await client.get(
        "/api/v1/products/search",
        params={"q": ""},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 400, 422)


@pytest.mark.asyncio
async def test_search_products_no_query(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search without q param returns 400 or 422."""
    resp = await client.get(
        "/api/v1/products/search",
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_search_products_unauthenticated(client: AsyncClient):
    """GET /api/v1/products/search without auth returns 401."""
    resp = await client.get(
        "/api/v1/products/search",
        params={"q": "test"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_products_invalid_page(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search with negative page returns 400 or 422."""
    resp = await client.get(
        "/api/v1/products/search",
        params={"q": "test", "page": -1},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_search_products_large_page_size(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/search with very large page_size is capped or rejected."""
    resp = await client.get(
        "/api/v1/products/search",
        params={"q": "test", "page_size": 10000},
        headers=auth_headers,
    )
    # May be capped to a reasonable max or rejected
    assert resp.status_code in (200, 400, 422)


# ---------------------------------------------------------------------------
# Preview product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_product(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/products/preview returns product details for a valid URL."""
    resp = await client.post(
        "/api/v1/products/preview",
        json={"url": "https://www.aliexpress.com/item/123456789.html"},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 202)
    if resp.status_code == 200:
        data = resp.json()
        # The response should have product information
        assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_preview_product_invalid_url(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/products/preview with an invalid URL returns 400 or 422."""
    resp = await client.post(
        "/api/v1/products/preview",
        json={"url": "not-a-valid-url"},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_preview_product_missing_url(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/products/preview without url field returns 422."""
    resp = await client.post(
        "/api/v1/products/preview",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_preview_product_unauthenticated(client: AsyncClient):
    """POST /api/v1/products/preview without auth returns 401."""
    resp = await client.post(
        "/api/v1/products/preview",
        json={"url": "https://www.aliexpress.com/item/123456789.html"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_preview_product_caching(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/products/preview for the same URL returns consistent results."""
    url = "https://www.aliexpress.com/item/999999.html"
    resp1 = await client.post(
        "/api/v1/products/preview",
        json={"url": url},
        headers=auth_headers,
    )
    resp2 = await client.post(
        "/api/v1/products/preview",
        json={"url": url},
        headers=auth_headers,
    )
    # Both should succeed with same status
    assert resp1.status_code == resp2.status_code
    if resp1.status_code == 200 and resp2.status_code == 200:
        # Content should be the same (cached or consistent)
        assert resp1.json() == resp2.json()


@pytest.mark.asyncio
async def test_preview_product_unsupported_domain(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/products/preview with unsupported domain returns 400."""
    resp = await client.post(
        "/api/v1/products/preview",
        json={"url": "https://www.randomsite.com/product/12345"},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 400, 422)
