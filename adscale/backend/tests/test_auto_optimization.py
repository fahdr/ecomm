"""
Tests for the auto-optimization service.

Validates campaign analysis, recommendation generation, and batch
auto-optimization across all recommendation scenarios.

For Developers:
    Tests operate directly on the service layer using the ``db`` fixture.
    Metric scenarios (low ROAS, high ROAS, low CTR, high CPA) are set
    up to trigger specific recommendation actions.

For QA Engineers:
    Covers: insufficient data, low ROAS -> pause, high CPA -> change_targeting,
    low CTR -> adjust_bid, excellent ROAS -> scale, good ROAS -> moderate scale,
    no issues -> no_action, batch auto_optimize.
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.ad_account import AccountStatus, AdAccount, AdPlatform
from app.models.campaign import Campaign, CampaignObjective, CampaignStatus
from app.models.user import User
from app.services.auto_optimization_service import (
    BENCHMARKS,
    OptimizationRecommendation,
    analyze_campaign,
    auto_optimize,
)
from app.services.performance_service import record_metrics


# ── Fixtures ──────────────────────────────────────────────────────────


async def _create_test_user(db, email="opt-test@example.com") -> User:
    """Create a test user directly in the DB."""
    user = User(email=email, hashed_password="$2b$12$fake")
    db.add(user)
    await db.flush()
    return user


async def _create_test_account(db, user_id: uuid.UUID) -> AdAccount:
    """Create a test ad account directly in the DB."""
    account = AdAccount(
        user_id=user_id,
        platform=AdPlatform.google,
        account_id_external="opt-ext-001",
        account_name="Opt Test Account",
        access_token_enc="mock_token",
        is_connected=True,
        status=AccountStatus.active,
    )
    db.add(account)
    await db.flush()
    return account


async def _create_test_campaign(
    db, user_id: uuid.UUID, ad_account_id: uuid.UUID,
    name: str = "Opt Campaign", status: CampaignStatus = CampaignStatus.active,
    budget_daily: float = 50.0,
) -> Campaign:
    """Create a test campaign directly in the DB."""
    campaign = Campaign(
        user_id=user_id,
        ad_account_id=ad_account_id,
        name=name,
        platform="google",
        objective=CampaignObjective.conversions,
        budget_daily=budget_daily,
        status=status,
    )
    db.add(campaign)
    await db.flush()
    return campaign


async def _add_metrics(
    db, campaign_id: uuid.UUID, days: int = 7, *,
    impressions: int = 1000, clicks: int = 50,
    conversions: int = 5, spend: float = 100.0,
    revenue: float = 300.0,
):
    """Add N days of identical metrics for a campaign."""
    for i in range(days):
        await record_metrics(db, campaign_id, {
            "date": date.today() - timedelta(days=i),
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "spend": spend,
            "revenue": revenue,
        })


# ── analyze_campaign Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_campaign_not_found(db):
    """analyze_campaign raises ValueError for nonexistent campaign."""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Campaign not found"):
        await analyze_campaign(db, fake_id)


@pytest.mark.asyncio
async def test_analyze_campaign_insufficient_data(db):
    """Campaign with no metrics returns insufficient_data action."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(db, user.id, account.id)

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "insufficient_data"
    assert rec.confidence == 0.0


@pytest.mark.asyncio
async def test_analyze_campaign_low_roas_pause(db):
    """Campaign with ROAS below minimum triggers pause action."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(db, user.id, account.id)

    # ROAS = 50/100 = 0.5, below minimum of 1.0
    await _add_metrics(db, campaign.id, spend=100.0, revenue=50.0)

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "pause"
    assert rec.confidence >= 0.8
    assert "ROAS" in rec.reason


@pytest.mark.asyncio
async def test_analyze_campaign_high_cpa_change_targeting(db):
    """Campaign with CPA above maximum triggers change_targeting."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(db, user.id, account.id)

    # CPA = 200/1 = 200, above max of 50; ROAS = 100/200 = 0.5... but that triggers pause first.
    # Need ROAS above 1 but CPA > 50
    # CPA = spend / conversions = 100 / 1 = 100 (> 50)
    # ROAS = revenue / spend = 200 / 100 = 2.0 (> 1.0, avoids pause)
    await _add_metrics(
        db, campaign.id,
        impressions=5000, clicks=200,
        conversions=1, spend=100.0, revenue=200.0,
    )

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "change_targeting"
    assert "CPA" in rec.reason


@pytest.mark.asyncio
async def test_analyze_campaign_low_ctr_adjust_bid(db):
    """Campaign with CTR below minimum triggers adjust_bid."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(db, user.id, account.id)

    # CTR = (5/10000)*100 = 0.05%, below minimum of 1.0%
    # ROAS = 200/50 = 4.0 (above 1.0), CPA = 50/10 = 5.0 (below 50)
    await _add_metrics(
        db, campaign.id,
        impressions=10000, clicks=5,
        conversions=10, spend=50.0, revenue=200.0,
    )

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "adjust_bid"
    assert "CTR" in rec.reason


@pytest.mark.asyncio
async def test_analyze_campaign_excellent_roas_scale(db):
    """Campaign with excellent ROAS triggers scale action with 50% budget increase."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(
        db, user.id, account.id, budget_daily=100.0
    )

    # ROAS = 600/100 = 6.0, above excellent threshold of 5.0
    await _add_metrics(
        db, campaign.id,
        impressions=5000, clicks=200,
        conversions=10, spend=100.0, revenue=600.0,
    )

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "scale"
    assert rec.suggested_budget == 150.0  # 100 * 1.5
    assert rec.confidence >= 0.8


@pytest.mark.asyncio
async def test_analyze_campaign_good_roas_moderate_scale(db):
    """Campaign with good (but not excellent) ROAS triggers moderate scale."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(
        db, user.id, account.id, budget_daily=100.0
    )

    # ROAS = 400/100 = 4.0, above good (3.0) but below excellent (5.0)
    await _add_metrics(
        db, campaign.id,
        impressions=5000, clicks=200,
        conversions=10, spend=100.0, revenue=400.0,
    )

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "scale"
    assert rec.suggested_budget == 120.0  # 100 * 1.2


@pytest.mark.asyncio
async def test_analyze_campaign_no_action(db):
    """Campaign performing within bounds returns no_action."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    campaign = await _create_test_campaign(db, user.id, account.id)

    # ROAS = 200/100 = 2.0 (between 1.0 and 3.0)
    # CTR = (100/5000)*100 = 2.0% (above 1.0%)
    # CPA = 100/10 = 10 (below 50)
    await _add_metrics(
        db, campaign.id,
        impressions=5000, clicks=100,
        conversions=10, spend=100.0, revenue=200.0,
    )

    rec = await analyze_campaign(db, campaign.id)

    assert rec.action == "no_action"
    assert "acceptable" in rec.reason.lower()


# ── auto_optimize Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_optimize_no_active_campaigns(db):
    """auto_optimize with no active campaigns returns empty list."""
    user = await _create_test_user(db)

    recs = await auto_optimize(db, user.id)

    assert recs == []


@pytest.mark.asyncio
async def test_auto_optimize_batch(db):
    """auto_optimize processes multiple active campaigns."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    camp1 = await _create_test_campaign(db, user.id, account.id, name="Camp A")
    camp2 = await _create_test_campaign(db, user.id, account.id, name="Camp B")

    # Camp1: good metrics
    await _add_metrics(db, camp1.id, spend=100.0, revenue=400.0,
                       impressions=5000, clicks=100, conversions=10)
    # Camp2: no metrics -> insufficient data
    # (no metrics added)

    recs = await auto_optimize(db, user.id)

    assert len(recs) == 2
    actions = {r["campaign_name"]: r["action"] for r in recs}
    assert "Camp A" in actions
    assert "Camp B" in actions
    assert actions["Camp B"] == "insufficient_data"


@pytest.mark.asyncio
async def test_auto_optimize_ignores_draft_campaigns(db):
    """auto_optimize only processes active campaigns (not drafts)."""
    user = await _create_test_user(db)
    account = await _create_test_account(db, user.id)
    await _create_test_campaign(
        db, user.id, account.id, name="Draft Camp",
        status=CampaignStatus.draft,
    )

    recs = await auto_optimize(db, user.id)

    assert recs == []
