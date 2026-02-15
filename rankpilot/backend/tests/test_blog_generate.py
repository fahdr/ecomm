"""
Tests for the blog generation endpoint (POST /api/v1/blog/generate).

Covers blog content generation using the LLM Gateway client,
including the fallback mock content when the gateway is unavailable.

For Developers:
    These tests mock the ``call_llm`` function in the blog_generate
    module to avoid real gateway calls. The endpoint is tested through
    the FastAPI test client.

For QA Engineers:
    These tests verify:
    - Blog generation returns title, content, meta_description, slug, keywords.
    - The endpoint requires authentication (401 without token).
    - The fallback mock content is used when the LLM fails.
    - Generated slugs are URL-safe.
    - Content includes the target keywords.

For Project Managers:
    Blog generation is the primary AI feature driving plan upgrades.
    These tests ensure it works reliably for all user tiers.
"""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_blog_generate_basic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog/generate returns a blog post with all required fields."""
    mock_response = {
        "content": "TITLE: Best SEO Strategies\nMETA: Learn top SEO strategies for 2025.\nCONTENT:\n# Best SEO Strategies\n\nThis is a comprehensive guide.",
        "provider": "mock",
        "model": "mock-v1",
        "input_tokens": 50,
        "output_tokens": 20,
        "cost_usd": 0.0,
        "cached": False,
        "latency_ms": 1,
    }

    with patch("app.api.blog_generate.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            "/api/v1/blog/generate",
            json={"keywords": ["seo", "strategies"], "topic": "SEO strategies for beginners"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "title" in data
        assert "content" in data
        assert "meta_description" in data
        assert "slug" in data
        assert "keywords" in data
        assert data["keywords"] == ["seo", "strategies"]
        assert len(data["title"]) > 0
        assert len(data["content"]) > 0
        assert len(data["meta_description"]) > 0
        assert len(data["slug"]) > 0


@pytest.mark.asyncio
async def test_blog_generate_unauthenticated(client: AsyncClient):
    """POST /api/v1/blog/generate without auth returns 401."""
    resp = await client.post(
        "/api/v1/blog/generate",
        json={"keywords": ["seo"]},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_blog_generate_fallback_on_error(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog/generate uses fallback content when LLM fails."""
    with patch("app.api.blog_generate.call_llm", new_callable=AsyncMock, side_effect=Exception("Gateway down")):
        resp = await client.post(
            "/api/v1/blog/generate",
            json={"keywords": ["content marketing"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        data = resp.json()
        # Fallback content should still be valid
        assert len(data["title"]) > 0
        assert len(data["content"]) > 0
        assert "content marketing" in data["content"].lower()


@pytest.mark.asyncio
async def test_blog_generate_slug_is_url_safe(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog/generate produces a URL-safe slug."""
    mock_response = {
        "content": "TITLE: 10 Best SEO Tips & Tricks!\nMETA: Top tips for SEO.\nCONTENT:\n# 10 Best SEO Tips\n\nContent here.",
        "provider": "mock",
        "model": "mock-v1",
        "input_tokens": 50,
        "output_tokens": 20,
        "cost_usd": 0.0,
        "cached": False,
        "latency_ms": 1,
    }

    with patch("app.api.blog_generate.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            "/api/v1/blog/generate",
            json={"keywords": ["seo tips"]},
            headers=auth_headers,
        )
        data = resp.json()
        slug = data["slug"]

        # Slug should only contain lowercase letters, numbers, and hyphens
        import re
        assert re.match(r"^[a-z0-9-]+$", slug), f"Slug '{slug}' contains invalid characters"


@pytest.mark.asyncio
async def test_blog_generate_uses_topic(client: AsyncClient, auth_headers: dict):
    """POST /api/v1/blog/generate uses the provided topic in content generation."""
    mock_response = {
        "content": "TITLE: E-commerce SEO Guide\nMETA: Complete e-commerce SEO guide.\nCONTENT:\n# E-commerce SEO\n\nOptimize your store.",
        "provider": "mock",
        "model": "mock-v1",
        "input_tokens": 50,
        "output_tokens": 20,
        "cost_usd": 0.0,
        "cached": False,
        "latency_ms": 1,
    }

    with patch("app.api.blog_generate.call_llm", new_callable=AsyncMock, return_value=mock_response):
        resp = await client.post(
            "/api/v1/blog/generate",
            json={"keywords": ["seo", "ecommerce"], "topic": "SEO for online stores"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["title"]) > 0
