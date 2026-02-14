"""
Tests for the campaign performance tracking service.

Validates metric recording, campaign performance aggregation, and
account-level performance summaries.

For Developers:
    Tests operate directly on the service layer using the ``db`` fixture.
    Test data (users, ad accounts, campaigns) is created using direct
    ORM operations for isolation from API routing.

For QA Engineers:
    Covers: record_metrics (create + update), derived fields (ROAS, CPA, CTR),
    get_campaign_performance (time series + totals), get_account_performance
    (cross-campaign aggregation), empty data edge cases.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.ad_account import AccountStatus, AdAccount, AdPlatform
from app.models.campaign import Campaign, CampaignObjective, CampaignStatus
from app.models.user import User
from app.services.performance_service import (
    get_account_performance,
    get_campaign_performance,
    record_metrics,
)


# ── Fixtures ──────────────────────────────────────────────────────────


async def _create_user(db, email="perf-test@example.com") -> User:
    """Create a test user directly in the DB."""
    user = User(email=email, hashed_password="$2b$12$fake")
    db.add(user)
    await db.flush()
    return user


async def _create_ad_account(db, user_id: uuid.UUID) -> AdAccount:
    """Create a test ad account directly in the DB."""
    account = AdAccount(
        user_id=user_id,
        platform=AdPlatform.google,
        account_id_external="perf-ext-001",
        account_name="Perf Test Account",
        access_token_enc="mock_token",
        is_connected=True,
        status=AccountStatus.active,
    )
    db.add(account)
    await db.flush()
    return account


async def _create_campaign(
    db, user_id: uuid.UUID, ad_account_id: uuid.UUID, name: str = "Perf Campaign"
) -> Campaign:
    """Create a test campaign directly in the DB."""
    campaign = Campaign(
        user_id=user_id,
        ad_account_id=ad_account_id,
        name=name,
        platform="google",
        objective=CampaignObjective.conversions,
        budget_daily=50.0,
        status=CampaignStatus.active,
    )
    db.add(campaign)
    await db.flush()
    return campaign


# ── record_metrics Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_metrics_creates_new(db):
    """record_metrics creates a new metric record with computed fields."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)
    campaign = await _create_campaign(db, user.id, account.id)

    metric = await record_metrics(db, campaign.id, {
        "date": date.today(),
        "impressions": 1000,
        "clicks": 50,
        "conversions": 5,
        "spend": 100.0,
        "revenue": 500.0,
    })

    assert metric.impressions == 1000
    assert metric.clicks == 50
    assert metric.conversions == 5
    assert metric.spend == 100.0
    assert metric.revenue == 500.0
    # Derived fields
    assert metric.roas == 5.0  # 500/100
    assert metric.cpa == 20.0  # 100/5
    assert metric.ctr == 5.0   # (50/1000)*100


@pytest.mark.asyncio
async def test_record_metrics_updates_existing(db):
    """record_metrics updates existing record for the same date."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)
    campaign = await _create_campaign(db, user.id, account.id)

    today = date.today()

    # Create initial record
    metric1 = await record_metrics(db, campaign.id, {
        "date": today,
        "impressions": 1000,
        "clicks": 50,
        "conversions": 5,
        "spend": 100.0,
        "revenue": 500.0,
    })
    metric1_id = metric1.id

    # Update same date
    metric2 = await record_metrics(db, campaign.id, {
        "date": today,
        "impressions": 2000,
        "clicks": 100,
        "conversions": 10,
        "spend": 200.0,
        "revenue": 1000.0,
    })

    assert metric2.id == metric1_id  # Same record
    assert metric2.impressions == 2000
    assert metric2.revenue == 1000.0
    assert metric2.roas == 5.0


@pytest.mark.asyncio
async def test_record_metrics_zero_spend_no_roas(db):
    """record_metrics sets ROAS to None when spend is zero."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)
    campaign = await _create_campaign(db, user.id, account.id)

    metric = await record_metrics(db, campaign.id, {
        "date": date.today(),
        "impressions": 1000,
        "clicks": 50,
        "conversions": 0,
        "spend": 0.0,
        "revenue": 0.0,
    })

    assert metric.roas is None
    assert metric.cpa is None
    assert metric.ctr == 5.0  # (50/1000)*100


# ── get_campaign_performance Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_campaign_performance_with_data(db):
    """get_campaign_performance returns time series and totals."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)
    campaign = await _create_campaign(db, user.id, account.id)

    # Record 3 days of metrics
    for i in range(3):
        await record_metrics(db, campaign.id, {
            "date": date.today() - timedelta(days=i),
            "impressions": 1000,
            "clicks": 50,
            "conversions": 5,
            "spend": 100.0,
            "revenue": 400.0,
        })

    result = await get_campaign_performance(db, campaign.id, days=30)

    assert result["period_days"] == 30
    assert len(result["time_series"]) == 3
    assert result["totals"]["total_spend"] == 300.0
    assert result["totals"]["total_revenue"] == 1200.0
    assert result["totals"]["total_conversions"] == 15
    assert result["totals"]["avg_roas"] == 4.0  # 1200/300


@pytest.mark.asyncio
async def test_get_campaign_performance_no_data(db):
    """get_campaign_performance with no metrics returns empty time series."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)
    campaign = await _create_campaign(db, user.id, account.id)

    result = await get_campaign_performance(db, campaign.id, days=30)

    assert result["time_series"] == []
    assert result["totals"]["total_spend"] == 0.0
    assert result["totals"]["avg_roas"] is None


# ── get_account_performance Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_account_performance_with_campaigns(db):
    """get_account_performance aggregates across campaigns."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)
    camp1 = await _create_campaign(db, user.id, account.id, name="Camp 1")
    camp2 = await _create_campaign(db, user.id, account.id, name="Camp 2")

    # Add metrics to both campaigns
    await record_metrics(db, camp1.id, {
        "date": date.today(),
        "impressions": 1000,
        "clicks": 50,
        "conversions": 5,
        "spend": 100.0,
        "revenue": 500.0,
    })
    await record_metrics(db, camp2.id, {
        "date": date.today(),
        "impressions": 2000,
        "clicks": 100,
        "conversions": 10,
        "spend": 200.0,
        "revenue": 800.0,
    })

    result = await get_account_performance(db, account.id, days=30)

    assert result["campaign_count"] == 2
    assert result["totals"]["total_spend"] == 300.0
    assert result["totals"]["total_revenue"] == 1300.0
    assert result["totals"]["total_conversions"] == 15
    assert len(result["per_campaign"]) == 2


@pytest.mark.asyncio
async def test_get_account_performance_no_campaigns(db):
    """get_account_performance with no campaigns returns empty."""
    user = await _create_user(db)
    account = await _create_ad_account(db, user.id)

    result = await get_account_performance(db, account.id, days=30)

    assert result["campaign_count"] == 0
    assert result["totals"]["total_spend"] == 0.0
    assert result["per_campaign"] == []
