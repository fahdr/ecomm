"""
Tests for the Competitor Store Crawler service.

Verifies product extraction from Shopify JSON API and HTML fallbacks,
pagination handling, price parsing, and error resilience.

For Developers:
    Tests mock HTTP responses using ``unittest.mock.AsyncMock`` and
    ``httpx.Response`` objects. No real network calls are made.

For QA Engineers:
    These tests cover:
    - Shopify JSON API crawling with valid product data.
    - Shopify pagination across multiple pages.
    - HTML fallback with Open Graph meta tags.
    - Single product page extraction.
    - Graceful error handling (timeouts, 404s).
    - Price parsing edge cases (European format, currency symbols).

For Project Managers:
    The crawler is tested with realistic mock data to ensure reliable
    product discovery across different store platforms.

For End Users:
    These tests ensure that SpyDrop can accurately find and track
    products from a wide variety of competitor stores.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.crawler_service import (
    _normalize_shopify_product,
    _parse_price,
    _strip_html,
    crawl_product_page,
    crawl_store_products,
)


# ── Price Parsing Tests ────────────────────────────────────────────


def test_parse_price_simple():
    """Standard USD price format."""
    assert _parse_price("29.99") == 29.99


def test_parse_price_with_currency_symbol():
    """Price with dollar sign."""
    assert _parse_price("$29.99") == 29.99


def test_parse_price_european_format():
    """European comma-decimal format (19,99 means 19.99)."""
    assert _parse_price("19,99") == 19.99


def test_parse_price_thousands_separator():
    """Price with comma thousands separator."""
    assert _parse_price("1,299.50") == 1299.50


def test_parse_price_empty_string():
    """Empty string returns None."""
    assert _parse_price("") is None


def test_parse_price_non_numeric():
    """Non-numeric string returns None."""
    assert _parse_price("free") is None


# ── HTML Stripping Tests ───────────────────────────────────────────


def test_strip_html_simple():
    """Removes basic HTML tags."""
    assert _strip_html("<b>bold</b> text") == "bold  text"


def test_strip_html_nested():
    """Removes nested HTML tags."""
    result = _strip_html("<div><p>hello</p></div>")
    assert "hello" in result


# ── Shopify Product Normalization ──────────────────────────────────


def test_normalize_shopify_product_basic():
    """Normalizes a standard Shopify product JSON."""
    raw = {
        "title": "Test Widget",
        "handle": "test-widget",
        "body_html": "<p>A great widget</p>",
        "variants": [
            {"title": "Default", "price": "29.99", "sku": "TW-001"},
        ],
        "images": [{"src": "https://cdn.shopify.com/test.jpg"}],
    }
    result = _normalize_shopify_product(raw, "https://store.com")

    assert result is not None
    assert result["title"] == "Test Widget"
    assert result["price"] == 29.99
    assert result["url"] == "https://store.com/products/test-widget"
    assert result["image_url"] == "https://cdn.shopify.com/test.jpg"
    assert result["source"] == "shopify_json"
    assert len(result["variants"]) == 1
    assert result["variants"][0]["sku"] == "TW-001"


def test_normalize_shopify_product_missing_title():
    """Products without a title are skipped (returns None)."""
    raw = {"title": "", "handle": "empty", "variants": [], "images": []}
    assert _normalize_shopify_product(raw, "https://store.com") is None


def test_normalize_shopify_product_no_variants():
    """Product with no variants has None price."""
    raw = {"title": "No Variant Product", "handle": "nvp", "variants": [], "images": []}
    result = _normalize_shopify_product(raw, "https://store.com")
    assert result is not None
    assert result["price"] is None
    assert result["variants"] == []


# ── Shopify JSON Crawling ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_crawl_store_products_shopify():
    """Crawl products from a mocked Shopify /products.json endpoint."""
    mock_response_page1 = {
        "products": [
            {
                "title": "Product A",
                "handle": "product-a",
                "body_html": "<p>Description A</p>",
                "variants": [{"title": "Default", "price": "15.99", "sku": "A1"}],
                "images": [{"src": "https://cdn.shopify.com/a.jpg"}],
            },
            {
                "title": "Product B",
                "handle": "product-b",
                "body_html": "Description B",
                "variants": [{"title": "Default", "price": "25.00", "sku": "B1"}],
                "images": [],
            },
        ]
    }
    mock_response_page2 = {"products": []}

    async def mock_get(url, **kwargs):
        """Mock HTTP GET that returns Shopify JSON for page 1, empty for page 2."""

        class MockResponse:
            def __init__(self, data, status_code=200):
                self.status_code = status_code
                self._data = data
                self.text = json.dumps(data)

            def json(self):
                return self._data

            def raise_for_status(self):
                pass

        if "page=1" in url:
            return MockResponse(mock_response_page1)
        return MockResponse(mock_response_page2)

    with patch("app.services.crawler_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        products = await crawl_store_products("https://shopify-store.com")

    assert len(products) == 2
    assert products[0]["title"] == "Product A"
    assert products[0]["price"] == 15.99
    assert products[1]["title"] == "Product B"
    assert products[1]["price"] == 25.00


# ── HTML Product Page Crawling ─────────────────────────────────────


@pytest.mark.asyncio
async def test_crawl_product_page_with_og_tags():
    """Extract product info from Open Graph meta tags."""
    html = """
    <html>
    <head>
        <title>Widget Pro</title>
        <meta property="og:title" content="Widget Pro - Best Widget Ever" />
        <meta property="og:description" content="The ultimate widget for pros" />
        <meta property="og:image" content="https://example.com/widget.jpg" />
        <meta property="og:price:amount" content="49.99" />
        <meta property="og:price:currency" content="USD" />
    </head>
    <body></body>
    </html>
    """

    async def mock_get(url, **kwargs):
        class MockResponse:
            status_code = 200
            text = html

            def raise_for_status(self):
                pass

        return MockResponse()

    with patch("app.services.crawler_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await crawl_product_page("https://example.com/products/widget-pro")

    assert result["title"] == "Widget Pro - Best Widget Ever"
    assert result["price"] == 49.99
    assert result["currency"] == "USD"
    assert result["image_url"] == "https://example.com/widget.jpg"
    assert result["source"] == "html_detail"


@pytest.mark.asyncio
async def test_crawl_product_page_network_error():
    """Network errors return minimal dict with URL."""
    with patch("app.services.crawler_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await crawl_product_page("https://offline-store.com/product/1")

    assert result["url"] == "https://offline-store.com/product/1"
    assert result["title"] == ""
    assert result["price"] is None
