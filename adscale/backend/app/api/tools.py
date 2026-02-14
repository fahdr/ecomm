"""
AdScale tools API endpoints.

Provides utility endpoints for ad campaign planning, including budget
calculations, targeting suggestions, and ad copy generation.

For Developers:
    Tools endpoints are grouped under ``/api/v1/tools/``.  The budget
    calculator is a stateless computation; ad copy generation calls
    the LLM Gateway.  All endpoints require JWT authentication.

For QA Engineers:
    Test: budget calculator with various inputs (boundary values, zero
    CPC, high ROAS targets), ad copy generation (mock LLM), and
    input validation (422 on invalid data).

For Project Managers:
    Tools help users plan campaigns before committing budget.  The
    budget calculator estimates ROI, and AI copy generation saves
    creative time.

For End Users:
    Use the Budget Calculator to estimate how much to spend.  Use the
    AI Copy Generator to create compelling ad text automatically.
"""

import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.ad_copy_service import generate_ad_copy, generate_ad_variants
from app.services.auto_optimization_service import analyze_campaign, auto_optimize

router = APIRouter(prefix="/tools", tags=["tools"])


# ── Budget Calculator Schemas ─────────────────────────────────────────


class BudgetCalculatorRequest(BaseModel):
    """
    Input for the budget calculator tool.

    Attributes:
        product_price: Selling price of the product in USD.
        target_roas: Desired return on ad spend (e.g. 3.0 means $3 revenue per $1 spend).
        estimated_cpc: Estimated cost per click in USD.
        conversion_rate: Estimated conversion rate as a percentage (default 2.5%).
        profit_margin: Profit margin percentage (default 30%).
    """

    product_price: float = Field(..., gt=0, description="Product price in USD")
    target_roas: float = Field(..., gt=0, description="Target ROAS (e.g. 3.0)")
    estimated_cpc: float = Field(..., gt=0, description="Estimated CPC in USD")
    conversion_rate: float = Field(2.5, gt=0, le=100, description="Conversion rate %")
    profit_margin: float = Field(30.0, gt=0, le=100, description="Profit margin %")


class BudgetCalculatorResponse(BaseModel):
    """
    Output from the budget calculator tool.

    Attributes:
        recommended_daily_budget: Suggested daily ad spend in USD.
        estimated_daily_clicks: Expected clicks per day at the given budget.
        estimated_daily_conversions: Expected conversions per day.
        estimated_daily_revenue: Projected daily revenue from ads.
        estimated_daily_profit: Projected daily profit after ad costs.
        estimated_monthly_budget: Projected 30-day ad spend.
        estimated_monthly_revenue: Projected 30-day revenue.
        estimated_monthly_profit: Projected 30-day profit.
        break_even_cpa: Maximum CPA to break even.
        target_cpa: CPA needed to hit the target ROAS.
    """

    recommended_daily_budget: float
    estimated_daily_clicks: float
    estimated_daily_conversions: float
    estimated_daily_revenue: float
    estimated_daily_profit: float
    estimated_monthly_budget: float
    estimated_monthly_revenue: float
    estimated_monthly_profit: float
    break_even_cpa: float
    target_cpa: float


# ── Ad Copy Generation Schemas ────────────────────────────────────────


class AdCopyRequest(BaseModel):
    """
    Input for AI ad copy generation.

    Attributes:
        product_name: Name of the product to advertise.
        product_description: Brief product description.
        product_price: Product price in USD (optional).
        product_category: Product category (optional).
        platform: Ad platform ('google_ads', 'meta_ads', 'tiktok_ads').
        campaign_type: Campaign type for prompt tuning (default 'conversion').
    """

    product_name: str = Field(..., min_length=1, max_length=255)
    product_description: str = Field(..., min_length=1, max_length=1024)
    product_price: float | None = None
    product_category: str | None = None
    platform: str = Field(default="google_ads")
    campaign_type: str = Field(default="conversion")


class AdCopyVariantsRequest(AdCopyRequest):
    """
    Input for generating multiple ad copy variants.

    Attributes:
        count: Number of variants to generate (default 3, max 10).
    """

    count: int = Field(default=3, ge=1, le=10)


class AdCopyResponse(BaseModel):
    """
    AI-generated ad copy response.

    Attributes:
        headlines: List of generated headlines.
        descriptions: List of generated descriptions.
        call_to_actions: List of CTA suggestions.
        display_url_path: Suggested display URL path.
    """

    headlines: list[str]
    descriptions: list[str]
    call_to_actions: list[str]
    display_url_path: str


# ── Campaign Optimize Schemas ─────────────────────────────────────────


class OptimizationResponse(BaseModel):
    """
    Campaign optimization recommendation response.

    Attributes:
        campaign_id: UUID of the analyzed campaign.
        campaign_name: Campaign name.
        action: Recommended action (pause, scale, adjust_bid, etc.).
        reason: Human-readable explanation.
        confidence: Confidence score (0.0 - 1.0).
        suggested_budget: Suggested new daily budget (nullable).
    """

    campaign_id: str
    campaign_name: str
    action: str
    reason: str
    confidence: float
    suggested_budget: float | None = None


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/budget-calculator", response_model=BudgetCalculatorResponse)
async def budget_calculator(
    request: BudgetCalculatorRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Calculate recommended advertising budget based on product economics.

    Uses product price, target ROAS, estimated CPC, and conversion rate
    to project daily and monthly budget, revenue, and profit.

    Args:
        request: Budget calculator input data.
        current_user: The authenticated user.

    Returns:
        BudgetCalculatorResponse with budget recommendations and projections.
    """
    # Core calculations
    # Target CPA = product_price / target_roas
    target_cpa = round(request.product_price / request.target_roas, 2)

    # Break-even CPA = product_price * profit_margin (as decimal)
    break_even_cpa = round(request.product_price * (request.profit_margin / 100), 2)

    # Clicks needed per conversion = 100 / conversion_rate
    clicks_per_conversion = 100 / request.conversion_rate

    # Daily budget to get ~5 conversions per day (reasonable starting point)
    target_daily_conversions = 5.0
    target_daily_clicks = target_daily_conversions * clicks_per_conversion
    recommended_daily_budget = round(target_daily_clicks * request.estimated_cpc, 2)

    # Cap daily budget: don't exceed 10x target CPA per day
    max_daily = target_cpa * target_daily_conversions * 2
    recommended_daily_budget = min(recommended_daily_budget, round(max_daily, 2))

    # Recalculate based on actual budget
    estimated_daily_clicks = round(recommended_daily_budget / request.estimated_cpc, 1)
    estimated_daily_conversions = round(
        estimated_daily_clicks * (request.conversion_rate / 100), 2
    )
    estimated_daily_revenue = round(
        estimated_daily_conversions * request.product_price, 2
    )
    estimated_daily_profit = round(
        estimated_daily_revenue * (request.profit_margin / 100) - recommended_daily_budget,
        2,
    )

    return BudgetCalculatorResponse(
        recommended_daily_budget=recommended_daily_budget,
        estimated_daily_clicks=estimated_daily_clicks,
        estimated_daily_conversions=estimated_daily_conversions,
        estimated_daily_revenue=estimated_daily_revenue,
        estimated_daily_profit=estimated_daily_profit,
        estimated_monthly_budget=round(recommended_daily_budget * 30, 2),
        estimated_monthly_revenue=round(estimated_daily_revenue * 30, 2),
        estimated_monthly_profit=round(estimated_daily_profit * 30, 2),
        break_even_cpa=break_even_cpa,
        target_cpa=target_cpa,
    )


@router.post("/generate-copy", response_model=AdCopyResponse)
async def generate_copy_endpoint(
    request: AdCopyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI-powered ad copy for a product.

    Uses the LLM Gateway to create platform-specific ad copy with
    headlines, descriptions, and CTAs.

    Args:
        request: Ad copy generation input data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AdCopyResponse with generated ad copy.
    """
    product_data = {
        "name": request.product_name,
        "description": request.product_description,
        "price": request.product_price,
        "category": request.product_category,
    }

    result = await generate_ad_copy(
        db=db,
        user_id=str(current_user.id),
        product_data=product_data,
        platform=request.platform,
        campaign_type=request.campaign_type,
    )

    return AdCopyResponse(
        headlines=result.headlines,
        descriptions=result.descriptions,
        call_to_actions=result.call_to_actions,
        display_url_path=result.display_url_path,
    )


@router.post("/generate-variants", response_model=list[AdCopyResponse])
async def generate_variants_endpoint(
    request: AdCopyVariantsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate multiple ad copy variants for A/B testing.

    Produces diverse variations of ad copy for the same product,
    each optimized for a different campaign angle.

    Args:
        request: Ad copy variants input data (includes count).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of AdCopyResponse objects, one per variant.
    """
    product_data = {
        "name": request.product_name,
        "description": request.product_description,
        "price": request.product_price,
        "category": request.product_category,
    }

    results = await generate_ad_variants(
        db=db,
        user_id=str(current_user.id),
        product_data=product_data,
        platform=request.platform,
        count=request.count,
    )

    return [
        AdCopyResponse(
            headlines=r.headlines,
            descriptions=r.descriptions,
            call_to_actions=r.call_to_actions,
            display_url_path=r.display_url_path,
        )
        for r in results
    ]


@router.post(
    "/campaigns/{campaign_id}/optimize",
    response_model=OptimizationResponse,
)
async def optimize_campaign_endpoint(
    campaign_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze a campaign and get optimization recommendations.

    Evaluates the campaign's recent performance against benchmarks
    and returns an actionable recommendation.

    Args:
        campaign_id: UUID of the campaign to optimize.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        OptimizationResponse with the recommendation.

    Raises:
        HTTPException 400: If the campaign ID format is invalid.
        HTTPException 404: If the campaign is not found.
    """
    try:
        cid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    try:
        rec = await analyze_campaign(db, cid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return OptimizationResponse(
        campaign_id=str(rec.campaign_id),
        campaign_name=rec.campaign_name,
        action=rec.action,
        reason=rec.reason,
        confidence=rec.confidence,
        suggested_budget=rec.suggested_budget,
    )


@router.post("/auto-optimize", response_model=list[OptimizationResponse])
async def auto_optimize_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-optimize all active campaigns for the current user.

    Batch-analyzes every active campaign and returns a list of
    optimization recommendations.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of OptimizationResponse with recommendations for each campaign.
    """
    recs = await auto_optimize(db, current_user.id)
    return [OptimizationResponse(**r) for r in recs]
