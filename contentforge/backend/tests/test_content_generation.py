"""
Content generation service and new endpoint tests.

Tests the LLM-powered content generation, A/B variant generation,
bulk generation v2, and content export features.

For Developers:
    Tests mock ``app.services.llm_client.call_contentforge_llm`` to avoid
    real LLM gateway calls. The mock is applied at the import location
    in content_service so both direct calls and endpoint-triggered calls
    use the mock.

For QA Engineers:
    Run with: ``pytest tests/test_content_generation.py -v``
    Tests cover:
    - LLM-powered generation with mocked gateway
    - Fallback to mock content when LLM is unavailable
    - A/B variant generation (multiple variants returned)
    - Bulk generation v2 with product list
    - Bulk generation v2 with connection_id
    - Content export to connected store
    - Export validation (incomplete job, missing connection)
    - Template name propagation through generation
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.content_service import (
    _build_product_prompt_vars,
    generate_content,
    generate_ab_variants,
    generate_mock_content,
)
from tests.conftest import register_and_login


# ── Unit Tests: Product Prompt Vars ───────────────────────────────────


def test_build_product_prompt_vars_basic():
    """_build_product_prompt_vars extracts name, price, category, features."""
    data = {
        "name": "Widget Pro",
        "price": "49.99",
        "category": "Gadgets",
        "features": ["Wireless", "Compact", "USB-C"],
        "description": "The best widget",
    }
    vars = _build_product_prompt_vars(data)
    assert vars["product_name"] == "Widget Pro"
    assert vars["product_price"] == "49.99"
    assert vars["product_category"] == "Gadgets"
    assert "Wireless" in vars["product_features"]
    assert "Compact" in vars["product_features"]
    assert vars["product_description"] == "The best widget"


def test_build_product_prompt_vars_defaults():
    """_build_product_prompt_vars uses sensible defaults for missing keys."""
    vars = _build_product_prompt_vars({})
    assert vars["product_name"] == "Premium Product"
    assert vars["product_price"] == "29.99"
    assert vars["product_category"] == "General"
    assert vars["product_features"] == "high quality, durable"


def test_build_product_prompt_vars_string_features():
    """_build_product_prompt_vars handles string features (not list)."""
    data = {"features": "Wireless, Compact, Lightweight"}
    vars = _build_product_prompt_vars(data)
    assert vars["product_features"] == "Wireless, Compact, Lightweight"


# ── Unit Tests: Mock Content Generation ──────────────────────────────


def test_mock_content_social_caption():
    """generate_mock_content produces social_caption content type."""
    text = generate_mock_content(
        {"name": "Widget", "category": "Gadgets", "price": "29.99"},
        "social_caption",
    )
    assert "Widget" in text
    assert "#" in text  # hashtags


def test_mock_content_all_types_produce_output():
    """generate_mock_content produces non-empty output for all content types."""
    product = {
        "name": "Test Product",
        "price": "19.99",
        "category": "Electronics",
        "features": ["Feature A", "Feature B"],
    }
    for ct in ["title", "description", "meta_description", "keywords", "bullet_points", "social_caption"]:
        text = generate_mock_content(product, ct)
        assert len(text) > 0, f"Empty content for type '{ct}'"
        assert len(text.split()) > 0


# ── Unit Tests: LLM Content Generation ───────────────────────────────


@pytest.mark.asyncio
async def test_generate_content_with_mocked_llm(db):
    """generate_content calls LLM gateway and returns structured results."""
    import uuid

    mock_llm = AsyncMock(return_value={
        "content": "AI-generated product title for testing",
        "provider": "anthropic",
        "model": "claude-3-haiku",
        "input_tokens": 50,
        "output_tokens": 8,
        "cost_usd": 0.001,
        "cached": False,
        "latency_ms": 200,
    })

    with patch("app.services.llm_client.call_contentforge_llm", mock_llm):
        results = await generate_content(
            db=db,
            user_id=uuid.uuid4(),
            product_data={"name": "Widget Pro", "price": "49.99", "features": ["Wireless"]},
            content_types=["title"],
            template_name="amazon_style",
        )

    assert len(results) == 1
    assert results[0]["content_type"] == "title"
    assert results[0]["content"] == "AI-generated product title for testing"
    assert results[0]["word_count"] > 0
    assert results[0]["version"] == 1
    mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_generate_content_fallback_on_llm_failure(db):
    """generate_content falls back to mock when LLM gateway fails."""
    import uuid

    mock_llm = AsyncMock(side_effect=Exception("Gateway unavailable"))

    with patch("app.services.llm_client.call_contentforge_llm", mock_llm):
        results = await generate_content(
            db=db,
            user_id=uuid.uuid4(),
            product_data={"name": "Fallback Widget", "price": "29.99"},
            content_types=["title"],
            template_name="shopify_seo",
        )

    assert len(results) == 1
    assert results[0]["content_type"] == "title"
    assert "Fallback Widget" in results[0]["content"]  # mock uses product name


@pytest.mark.asyncio
async def test_generate_content_multiple_types(db):
    """generate_content processes all requested content types."""
    import uuid

    call_count = 0

    async def mock_llm(**kwargs):
        nonlocal call_count
        call_count += 1
        return {
            "content": f"Generated content #{call_count}",
            "provider": "mock",
            "model": "test",
            "input_tokens": 10,
            "output_tokens": 5,
            "cost_usd": 0.0,
            "cached": False,
            "latency_ms": 1,
        }

    # Patch the function that's imported inside generate_content
    with patch("app.services.llm_client.call_contentforge_llm", side_effect=mock_llm):
        results = await generate_content(
            db=db,
            user_id=uuid.uuid4(),
            product_data={"name": "Multi-Type Widget"},
            content_types=["title", "description", "keywords"],
            template_name="shopify_seo",
        )

    assert len(results) == 3
    content_types = [r["content_type"] for r in results]
    assert content_types == ["title", "description", "keywords"]


# ── Unit Tests: A/B Variant Generation ───────────────────────────────


@pytest.mark.asyncio
async def test_generate_ab_variants_returns_count(db):
    """generate_ab_variants returns the requested number of variants."""
    import uuid

    variant_num = 0

    async def mock_llm(**kwargs):
        nonlocal variant_num
        variant_num += 1
        return {
            "content": f"Variant {variant_num}: Amazing Widget Title",
            "provider": "mock",
            "model": "test",
            "input_tokens": 10,
            "output_tokens": 6,
            "cost_usd": 0.0,
            "cached": False,
            "latency_ms": 1,
        }

    with patch("app.services.llm_client.call_contentforge_llm", side_effect=mock_llm):
        variants = await generate_ab_variants(
            db=db,
            user_id=uuid.uuid4(),
            product_data={"name": "AB Widget"},
            content_type="title",
            template_name="amazon_style",
            count=3,
        )

    assert len(variants) == 3
    assert all("Variant" in v for v in variants)


@pytest.mark.asyncio
async def test_generate_ab_variants_fallback(db):
    """generate_ab_variants falls back to mock on LLM failure."""
    import uuid

    mock_llm = AsyncMock(side_effect=Exception("Gateway down"))

    with patch("app.services.llm_client.call_contentforge_llm", mock_llm):
        variants = await generate_ab_variants(
            db=db,
            user_id=uuid.uuid4(),
            product_data={"name": "Fallback Widget"},
            content_type="title",
            count=2,
        )

    assert len(variants) == 2
    assert all("variant" in v.lower() for v in variants)


# ── API Tests: A/B Variants Endpoint ─────────────────────────────────


@pytest.mark.asyncio
async def test_ab_variants_endpoint(client: AsyncClient):
    """POST /content/ab-variants returns multiple variants."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/ab-variants",
        headers=headers,
        json={
            "product_data": {"name": "Endpoint Widget", "price": "39.99"},
            "content_type": "title",
            "template_name": "amazon_style",
            "count": 3,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content_type"] == "title"
    assert data["template_name"] == "amazon_style"
    assert len(data["variants"]) == 3


@pytest.mark.asyncio
async def test_ab_variants_endpoint_unauthenticated(client: AsyncClient):
    """POST /content/ab-variants requires authentication."""
    resp = await client.post(
        "/api/v1/content/ab-variants",
        json={
            "product_data": {"name": "Test"},
            "content_type": "title",
            "count": 2,
        },
    )
    assert resp.status_code == 401


# ── API Tests: Bulk Generation v2 ────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_generation_v2_with_products(client: AsyncClient):
    """POST /content/bulk with product list creates multiple jobs."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/bulk",
        headers=headers,
        json={
            "products": [
                {"name": "Bulk Product 1", "price": "19.99"},
                {"name": "Bulk Product 2", "price": "29.99"},
            ],
            "template_name": "shopify_seo",
            "content_types": ["title", "description"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_products"] == 2
    assert data["jobs_created"] == 2
    assert len(data["jobs"]) == 2
    assert len(data["errors"]) == 0
    for job in data["jobs"]:
        assert job["status"] == "completed"
        assert len(job["content_items"]) == 2


@pytest.mark.asyncio
async def test_bulk_generation_v2_with_connection(client: AsyncClient):
    """POST /content/bulk with connection_id generates for store products."""
    headers = await register_and_login(client)

    # Create a store connection first
    conn_resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "bulk-store.myshopify.com",
            "api_key": "bulk_key",
        },
    )
    conn_id = conn_resp.json()["id"]

    resp = await client.post(
        "/api/v1/content/bulk",
        headers=headers,
        json={
            "connection_id": conn_id,
            "content_types": ["title"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_products"] == 3  # mock pulls 3 products
    assert data["jobs_created"] == 3


@pytest.mark.asyncio
async def test_bulk_generation_v2_empty_request(client: AsyncClient):
    """POST /content/bulk with no products or connection returns 400."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/bulk",
        headers=headers,
        json={
            "products": [],
            "content_types": ["title"],
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_bulk_generation_v2_invalid_connection(client: AsyncClient):
    """POST /content/bulk with nonexistent connection_id returns 404."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/bulk",
        headers=headers,
        json={
            "connection_id": "00000000-0000-0000-0000-000000000000",
            "content_types": ["title"],
        },
    )
    assert resp.status_code == 404


# ── API Tests: Content Export ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_content_to_store(client: AsyncClient):
    """POST /content/{job_id}/export exports content to connected store."""
    headers = await register_and_login(client)

    # Create a completed generation job
    gen_resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Exportable Product"},
            "content_types": ["title", "description"],
        },
    )
    assert gen_resp.status_code == 201
    job_id = gen_resp.json()["id"]

    # Create a store connection
    conn_resp = await client.post(
        "/api/v1/connections/",
        headers=headers,
        json={
            "platform": "shopify",
            "store_url": "export-store.myshopify.com",
            "api_key": "export_key",
        },
    )
    conn_id = conn_resp.json()["id"]

    # Export
    resp = await client.post(
        f"/api/v1/content/{job_id}/export",
        headers=headers,
        json={
            "connection_id": conn_id,
            "product_id": "product-ext-123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["job_id"] == job_id
    assert data["connection_id"] == conn_id
    assert data["product_id"] == "product-ext-123"
    assert "title" in data["fields_updated"]
    assert "description" in data["fields_updated"]
    assert len(data["fields_updated"]) == 2


@pytest.mark.asyncio
async def test_export_content_job_not_found(client: AsyncClient):
    """POST /content/{job_id}/export returns 404 for nonexistent job."""
    headers = await register_and_login(client)

    resp = await client.post(
        "/api/v1/content/00000000-0000-0000-0000-000000000000/export",
        headers=headers,
        json={
            "connection_id": "00000000-0000-0000-0000-000000000000",
            "product_id": "ext-123",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_content_invalid_connection(client: AsyncClient):
    """POST /content/{job_id}/export returns 404 for nonexistent connection."""
    headers = await register_and_login(client)

    # Create a job first
    gen_resp = await client.post(
        "/api/v1/content/generate",
        headers=headers,
        json={
            "source_type": "manual",
            "source_data": {"name": "Export Test"},
            "content_types": ["title"],
        },
    )
    job_id = gen_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/content/{job_id}/export",
        headers=headers,
        json={
            "connection_id": "00000000-0000-0000-0000-000000000000",
            "product_id": "ext-123",
        },
    )
    assert resp.status_code == 404
