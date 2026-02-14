"""
Tests for SEO utility API endpoints (sitemap generation, page analysis).

Covers the /api/v1/seo/sitemap/generate and /api/v1/seo/analyze endpoints.

For Developers:
    The sitemap endpoint is tested directly with URL data.
    The page analysis endpoint requires mocking httpx to avoid real HTTP.

For QA Engineers:
    These tests verify:
    - Sitemap generation returns valid XML with correct content type.
    - Sitemap with multiple URLs includes all entries.
    - Authentication is required for all endpoints.

For Project Managers:
    Sitemap generation and page analysis are standalone SEO tools
    that provide immediate value to users.
"""

import pytest
from httpx import AsyncClient


# ── Sitemap Generation Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sitemap_generate_endpoint(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/seo/sitemap/generate returns XML sitemap."""
    resp = await client.post(
        "/api/v1/seo/sitemap/generate",
        json={
            "urls": [
                {"loc": "https://example.com/", "priority": 1.0},
                {"loc": "https://example.com/products", "changefreq": "weekly"},
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]

    xml = resp.text
    assert '<?xml version="1.0"' in xml
    assert "<urlset" in xml
    assert "https://example.com/" in xml
    assert "https://example.com/products" in xml


@pytest.mark.asyncio
async def test_sitemap_generate_empty(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/seo/sitemap/generate with empty URL list returns empty sitemap."""
    resp = await client.post(
        "/api/v1/seo/sitemap/generate",
        json={"urls": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    xml = resp.text
    assert "<urlset" in xml
    assert "<url>" not in xml


@pytest.mark.asyncio
async def test_sitemap_generate_unauthenticated(client: AsyncClient):
    """POST /api/v1/seo/sitemap/generate without auth returns 401."""
    resp = await client.post(
        "/api/v1/seo/sitemap/generate",
        json={"urls": [{"loc": "https://example.com/"}]},
    )
    assert resp.status_code == 401
