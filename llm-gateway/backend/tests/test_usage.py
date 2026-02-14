"""
Tests for the LLM Gateway usage analytics endpoints.

For Developers:
    Seeds usage log entries directly, then tests aggregation queries.

For QA Engineers:
    Verify that usage summary, by-provider, by-service, and by-customer
    aggregations return correct results.
"""

from datetime import datetime, timezone

import pytest

from app.models.usage_log import UsageLog


async def _seed_usage(db, entries):
    """Helper to insert usage log entries for testing."""
    for entry in entries:
        log = UsageLog(
            user_id=entry.get("user_id", "user-1"),
            service_name=entry.get("service_name", "trendscout"),
            task_type=entry.get("task_type", "test"),
            provider_name=entry.get("provider_name", "claude"),
            model_name=entry.get("model_name", "claude-sonnet-4-5-20250929"),
            input_tokens=entry.get("input_tokens", 100),
            output_tokens=entry.get("output_tokens", 50),
            cost_usd=entry.get("cost_usd", 0.001),
            latency_ms=entry.get("latency_ms", 500),
            cached=entry.get("cached", False),
            error=entry.get("error"),
        )
        db.add(log)
    await db.commit()


@pytest.mark.asyncio
async def test_usage_summary(client, auth_headers, db):
    """Summary endpoint returns correct aggregations."""
    await _seed_usage(db, [
        {"cost_usd": 0.01, "input_tokens": 100, "output_tokens": 50},
        {"cost_usd": 0.02, "input_tokens": 200, "output_tokens": 100, "cached": True},
        {"cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "error": "rate limited"},
    ])

    resp = await client.get("/api/v1/usage/summary?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 3
    assert data["total_cost_usd"] == pytest.approx(0.03, abs=0.001)
    assert data["total_tokens"] == 450
    assert data["cached_requests"] == 1
    assert data["error_requests"] == 1


@pytest.mark.asyncio
async def test_usage_by_provider(client, auth_headers, db):
    """By-provider endpoint groups correctly."""
    await _seed_usage(db, [
        {"provider_name": "claude", "cost_usd": 0.05},
        {"provider_name": "claude", "cost_usd": 0.03},
        {"provider_name": "openai", "cost_usd": 0.10},
    ])

    resp = await client.get("/api/v1/usage/by-provider?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Ordered by cost desc — openai first
    assert data[0]["provider_name"] == "openai"
    assert data[0]["request_count"] == 1
    assert data[1]["provider_name"] == "claude"
    assert data[1]["request_count"] == 2


@pytest.mark.asyncio
async def test_usage_by_service(client, auth_headers, db):
    """By-service endpoint groups correctly."""
    await _seed_usage(db, [
        {"service_name": "trendscout", "cost_usd": 0.05},
        {"service_name": "contentforge", "cost_usd": 0.10},
        {"service_name": "contentforge", "cost_usd": 0.05},
    ])

    resp = await client.get("/api/v1/usage/by-service?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["service_name"] == "contentforge"
    assert data[0]["request_count"] == 2


@pytest.mark.asyncio
async def test_usage_by_customer(client, auth_headers, db):
    """By-customer endpoint returns top spenders."""
    await _seed_usage(db, [
        {"user_id": "user-a", "cost_usd": 0.50},
        {"user_id": "user-b", "cost_usd": 0.10},
        {"user_id": "user-b", "cost_usd": 0.10},
        {"user_id": "user-a", "cost_usd": 0.30},
    ])

    resp = await client.get("/api/v1/usage/by-customer?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["user_id"] == "user-a"
    assert data[0]["total_cost_usd"] == pytest.approx(0.80, abs=0.001)


@pytest.mark.asyncio
async def test_usage_empty(client, auth_headers):
    """Summary with no data returns zeros."""
    resp = await client.get("/api/v1/usage/summary?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 0
    assert data["total_cost_usd"] == 0
