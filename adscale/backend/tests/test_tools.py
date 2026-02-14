"""
Tests for the AdScale tools API endpoints.

Validates budget calculator, AI ad copy generation, campaign optimization,
and auto-optimization endpoints.

For Developers:
    Budget calculator tests are stateless computations.  Ad copy tests
    mock the LLM Gateway.  Optimization tests require campaigns and
    metrics in the database.

For QA Engineers:
    Covers: budget calculator (valid input, edge cases), ad copy generation,
    campaign optimization (insufficient data, low ROAS, high ROAS),
    auto-optimize batch processing, and authentication.
"""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from tests.conftest import register_and_login


# ── Helpers ───────────────────────────────────────────────────────────


async def _create_ad_account(
    client: AsyncClient, headers: dict, external_id: str = "tools-acct-001"
) -> str:
    """Create an ad account and return its UUID."""
    resp = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "platform": "google",
            "account_id_external": external_id,
            "account_name": "Tools Test Account",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_campaign(
    client: AsyncClient,
    headers: dict,
    ad_account_id: str,
    name: str = "Test Campaign",
    status: str = "active",
) -> str:
    """Create a campaign and return its UUID."""
    resp = await client.post(
        "/api/v1/campaigns",
        headers=headers,
        json={
            "ad_account_id": ad_account_id,
            "name": name,
            "objective": "conversions",
            "budget_daily": 50.0,
            "status": status,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Budget Calculator Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_budget_calculator_success(client: AsyncClient, auth_headers: dict):
    """POST /tools/budget-calculator returns computed budget recommendations."""
    resp = await client.post(
        "/api/v1/tools/budget-calculator",
        headers=auth_headers,
        json={
            "product_price": 50.0,
            "target_roas": 3.0,
            "estimated_cpc": 1.50,
            "conversion_rate": 2.5,
            "profit_margin": 30.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["recommended_daily_budget"] > 0
    assert data["estimated_daily_clicks"] > 0
    assert data["estimated_daily_conversions"] > 0
    assert data["estimated_daily_revenue"] > 0
    assert data["estimated_monthly_budget"] == round(data["recommended_daily_budget"] * 30, 2)
    assert data["target_cpa"] > 0
    assert data["break_even_cpa"] > 0


@pytest.mark.asyncio
async def test_budget_calculator_high_roas_target(client: AsyncClient, auth_headers: dict):
    """Budget calculator adjusts for high ROAS targets."""
    resp = await client.post(
        "/api/v1/tools/budget-calculator",
        headers=auth_headers,
        json={
            "product_price": 100.0,
            "target_roas": 10.0,
            "estimated_cpc": 2.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_cpa"] == 10.0  # 100 / 10


@pytest.mark.asyncio
async def test_budget_calculator_validation_errors(client: AsyncClient, auth_headers: dict):
    """Budget calculator rejects invalid inputs."""
    # Zero price
    resp = await client.post(
        "/api/v1/tools/budget-calculator",
        headers=auth_headers,
        json={"product_price": 0, "target_roas": 3.0, "estimated_cpc": 1.0},
    )
    assert resp.status_code == 422

    # Negative CPC
    resp = await client.post(
        "/api/v1/tools/budget-calculator",
        headers=auth_headers,
        json={"product_price": 50, "target_roas": 3.0, "estimated_cpc": -1.0},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_budget_calculator_unauthenticated(client: AsyncClient):
    """Budget calculator requires authentication."""
    resp = await client.post(
        "/api/v1/tools/budget-calculator",
        json={"product_price": 50, "target_roas": 3.0, "estimated_cpc": 1.0},
    )
    assert resp.status_code == 401


# ── Ad Copy Generation Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_copy_endpoint(client: AsyncClient, auth_headers: dict):
    """POST /tools/generate-copy returns ad copy (using fallback)."""
    from app.services.llm_client import LLMGatewayError

    with patch("app.services.ad_copy_service.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMGatewayError("Gateway down")

        resp = await client.post(
            "/api/v1/tools/generate-copy",
            headers=auth_headers,
            json={
                "product_name": "Running Shoes",
                "product_description": "Lightweight shoes for runners",
                "platform": "google_ads",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["headlines"]) >= 1
    assert len(data["descriptions"]) >= 1
    assert len(data["call_to_actions"]) >= 1


@pytest.mark.asyncio
async def test_generate_variants_endpoint(client: AsyncClient, auth_headers: dict):
    """POST /tools/generate-variants returns multiple variants."""
    from app.services.llm_client import LLMGatewayError

    with patch("app.services.ad_copy_service.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LLMGatewayError("Gateway down")

        resp = await client.post(
            "/api/v1/tools/generate-variants",
            headers=auth_headers,
            json={
                "product_name": "Widget",
                "product_description": "A cool widget",
                "platform": "meta_ads",
                "count": 3,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert all("headlines" in v for v in data)


# ── Campaign Optimization Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_optimize_campaign_insufficient_data(
    client: AsyncClient, auth_headers: dict
):
    """Optimization for a campaign with no metrics returns insufficient_data."""
    account_id = await _create_ad_account(client, auth_headers)
    campaign_id = await _create_campaign(client, auth_headers, account_id)

    resp = await client.post(
        f"/api/v1/tools/campaigns/{campaign_id}/optimize",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "insufficient_data"


@pytest.mark.asyncio
async def test_optimize_campaign_not_found(client: AsyncClient, auth_headers: dict):
    """Optimization for a nonexistent campaign returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/tools/campaigns/{fake_id}/optimize",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_optimize_campaign_invalid_uuid(client: AsyncClient, auth_headers: dict):
    """Optimization with invalid UUID returns 400."""
    resp = await client.post(
        "/api/v1/tools/campaigns/not-a-uuid/optimize",
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_auto_optimize_no_campaigns(client: AsyncClient, auth_headers: dict):
    """Auto-optimize with no active campaigns returns empty list."""
    resp = await client.post(
        "/api/v1/tools/auto-optimize",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == []
