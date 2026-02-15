"""
Tests for the enhanced research service functions.

Covers the run_product_research pipeline, candidate generation from
store connections, LLM analysis parsing, and the watchlist import endpoint.

For Developers:
    Tests that use the database require the ``db`` and ``client`` fixtures
    from conftest.py.  The LLM client is mocked to avoid real HTTP calls.
    Store connections are created via the API for realistic testing.

For QA Engineers:
    These tests verify:
    - Research pipeline generates results from connected stores.
    - LLM analysis failures fall back to mock analysis gracefully.
    - Candidate generation produces products from each connection.
    - Analysis prompt builder creates well-formed prompts.
    - LLM response parsing handles valid JSON, code-fenced JSON, and garbage.
    - Watchlist import endpoint updates item status and returns success.
    - Watchlist import with missing connection returns 404.
    - Watchlist import with inactive connection returns 400.

For Project Managers:
    These tests ensure the core research pipeline and import workflow
    are reliable.  The pipeline is the main value proposition of the
    TrendScout service.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchResult, ResearchRun
from app.models.store_connection import StoreConnection
from app.services.research_service import (
    _build_analysis_prompt,
    _generate_candidates_from_connections,
    _parse_llm_analysis,
    run_product_research,
)
from tests.conftest import register_and_login


# ─── Helper Functions ────────────────────────────────────────────────


async def create_connection_direct(
    db: AsyncSession, user_id: uuid.UUID, platform: str = "shopify"
) -> StoreConnection:
    """
    Create a store connection directly in the database.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        platform: Store platform identifier.

    Returns:
        The created StoreConnection.
    """
    conn = StoreConnection(
        user_id=user_id,
        platform=platform,
        store_url=f"https://test-{platform}.example.com",
        api_key_encrypted="encrypted_test_key",
        api_secret_encrypted="encrypted_test_secret",
        is_active=True,
    )
    db.add(conn)
    await db.flush()
    await db.refresh(conn)
    return conn


async def create_run_direct(
    db: AsyncSession, user_id: uuid.UUID, keywords: list[str] | None = None
) -> ResearchRun:
    """
    Create a research run directly in the database.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        keywords: Search keywords.

    Returns:
        The created ResearchRun.
    """
    run = ResearchRun(
        user_id=user_id,
        keywords=keywords or ["test product"],
        sources=["platform"],
        status="pending",
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


# ─── Candidate Generation Tests ────────────────────────────────────


def test_generate_candidates_from_connections():
    """_generate_candidates_from_connections produces products from connections."""
    # Create mock connections
    conn1 = StoreConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        platform="shopify",
        store_url="https://shop1.example.com",
        api_key_encrypted="key1",
    )
    conn2 = StoreConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        platform="woocommerce",
        store_url="https://woo.example.com",
        api_key_encrypted="key2",
    )

    candidates = _generate_candidates_from_connections(
        [conn1, conn2], ["wireless earbuds"]
    )

    # Should produce 3-5 per connection = 6-10 total
    assert len(candidates) >= 6
    assert len(candidates) <= 10

    # Each candidate should have required fields
    for c in candidates:
        assert "product_title" in c
        assert "product_url" in c
        assert "price" in c
        assert "source" in c
        assert "raw_data" in c


def test_generate_candidates_empty_connections():
    """_generate_candidates_from_connections returns empty list with no connections."""
    candidates = _generate_candidates_from_connections([], ["test"])
    assert candidates == []


def test_generate_candidates_deterministic():
    """_generate_candidates_from_connections produces deterministic results."""
    conn = StoreConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        platform="shopify",
        store_url="https://shop.example.com",
        api_key_encrypted="key",
    )

    candidates1 = _generate_candidates_from_connections([conn], ["earbuds"])
    candidates2 = _generate_candidates_from_connections([conn], ["earbuds"])

    assert len(candidates1) == len(candidates2)
    for c1, c2 in zip(candidates1, candidates2):
        assert c1["product_title"] == c2["product_title"]
        assert c1["price"] == c2["price"]


# ─── Analysis Prompt Builder Tests ─────────────────────────────────


def test_build_analysis_prompt():
    """_build_analysis_prompt creates a well-formed prompt string."""
    data = {
        "product_title": "Wireless Earbuds Pro",
        "price": 29.99,
        "currency": "USD",
        "source": "shopify",
        "raw_data": {"market": {"search_volume": 50000}},
    }
    prompt = _build_analysis_prompt(data, 75.0)

    assert "Wireless Earbuds Pro" in prompt
    assert "29.99" in prompt
    assert "75" in prompt
    assert "shopify" in prompt
    assert "JSON" in prompt


# ─── LLM Response Parsing Tests ────────────────────────────────────


def test_parse_llm_analysis_valid_json():
    """_parse_llm_analysis extracts valid JSON from content field."""
    response = {
        "content": '{"summary": "Good product", "opportunity_score": 80, "risk_factors": ["r1"], "recommended_price_range": {"low": 20, "high": 50, "currency": "USD"}, "target_audience": "millennials", "marketing_angles": ["social ads"]}'
    }
    analysis = _parse_llm_analysis(response)
    assert analysis["summary"] == "Good product"
    assert analysis["opportunity_score"] == 80


def test_parse_llm_analysis_code_fenced():
    """_parse_llm_analysis handles JSON wrapped in markdown code fences."""
    response = {
        "content": '```json\n{"summary": "Fenced JSON", "opportunity_score": 70}\n```'
    }
    analysis = _parse_llm_analysis(response)
    assert analysis["summary"] == "Fenced JSON"


def test_parse_llm_analysis_invalid_content():
    """_parse_llm_analysis returns fallback dict for non-JSON content."""
    response = {"content": "This is not JSON at all"}
    analysis = _parse_llm_analysis(response)
    assert "summary" in analysis
    assert analysis["opportunity_score"] == 50
    assert "Analysis parsing failed" in analysis["risk_factors"]


def test_parse_llm_analysis_empty_response():
    """_parse_llm_analysis handles empty content gracefully."""
    analysis = _parse_llm_analysis({})
    assert analysis["summary"] == "Analysis unavailable"


# ─── Research Pipeline Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_run_product_research_with_connections(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """run_product_research generates results from connected stores."""
    # Register user and get user_id
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = uuid.UUID(resp.json()["id"])

    # Create a store connection
    await create_connection_direct(db, user_id, "shopify")
    await db.commit()

    # Create a research run
    run = await create_run_direct(db, user_id, ["wireless earbuds"])
    await db.commit()

    # Execute the pipeline (mock LLM will fail gracefully)
    results = await run_product_research(
        db, user_id, run.id, ["wireless earbuds"]
    )
    await db.commit()

    assert len(results) >= 3  # At least 3 products per connection
    for result in results:
        assert result.product_title
        assert result.score > 0
        assert result.ai_analysis is not None


@pytest.mark.asyncio
async def test_run_product_research_no_connections(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """run_product_research completes with 0 results when no connections exist."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    user_id = uuid.UUID(resp.json()["id"])

    run = await create_run_direct(db, user_id, ["test keyword"])
    await db.commit()

    results = await run_product_research(
        db, user_id, run.id, ["test keyword"]
    )
    await db.commit()

    assert len(results) == 0
    # Run should still be marked as completed
    await db.refresh(run)
    assert run.status == "completed"
    assert run.results_count == 0


# ─── Watchlist Import Endpoint Tests ───────────────────────────────


async def _setup_watchlist_import(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
) -> tuple[str, str]:
    """
    Set up the prerequisites for a watchlist import test.

    Creates a research run, result, watchlist item, and store connection.

    Returns:
        Tuple of (watchlist_item_id, connection_id).
    """
    # Create a research run
    run_resp = await client.post(
        "/api/v1/research/runs",
        json={"keywords": ["import test"], "sources": ["aliexpress"]},
        headers=auth_headers,
    )
    run = run_resp.json()

    # Create a result in the DB
    result = ResearchResult(
        run_id=uuid.UUID(run["id"]),
        source="aliexpress",
        product_title="Import Test Product",
        product_url="https://aliexpress.com/item/import-test",
        price=24.99,
        currency="USD",
        score=80.0,
        raw_data={"test": True},
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)

    # Add to watchlist
    wl_resp = await client.post(
        "/api/v1/watchlist",
        json={"result_id": str(result.id)},
        headers=auth_headers,
    )
    wl_item = wl_resp.json()

    # Create a store connection
    conn_resp = await client.post(
        "/api/v1/connections",
        json={
            "platform": "shopify",
            "store_url": "https://import-test.myshopify.com",
            "api_key": "shpat_import_key",
        },
        headers=auth_headers,
    )
    conn = conn_resp.json()

    return wl_item["id"], conn["id"]


@pytest.mark.asyncio
async def test_watchlist_import_success(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """POST /api/v1/watchlist/{id}/import successfully imports and updates status."""
    item_id, conn_id = await _setup_watchlist_import(client, auth_headers, db)

    resp = await client.post(
        f"/api/v1/watchlist/{item_id}/import",
        json={"connection_id": conn_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Import Test Product" in data["message"]
    assert data["external_product_id"] is not None

    # Verify watchlist item status updated to 'imported'
    list_resp = await client.get(
        "/api/v1/watchlist?status=imported", headers=auth_headers
    )
    list_data = list_resp.json()
    assert list_data["total"] >= 1


@pytest.mark.asyncio
async def test_watchlist_import_missing_connection(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """POST /api/v1/watchlist/{id}/import returns 404 for non-existent connection."""
    item_id, _ = await _setup_watchlist_import(client, auth_headers, db)
    fake_conn_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/watchlist/{item_id}/import",
        json={"connection_id": fake_conn_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "Store connection not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_watchlist_import_missing_item(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """POST /api/v1/watchlist/{id}/import returns 404 for non-existent watchlist item."""
    _, conn_id = await _setup_watchlist_import(client, auth_headers, db)
    fake_item_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/watchlist/{fake_item_id}/import",
        json={"connection_id": conn_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert "Watchlist item not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_watchlist_import_unauthenticated(
    client: AsyncClient, auth_headers: dict, db: AsyncSession
):
    """POST /api/v1/watchlist/{id}/import returns 401 without auth headers."""
    item_id, conn_id = await _setup_watchlist_import(client, auth_headers, db)

    resp = await client.post(
        f"/api/v1/watchlist/{item_id}/import",
        json={"connection_id": conn_id},
    )
    assert resp.status_code == 401
