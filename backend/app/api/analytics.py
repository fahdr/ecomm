"""Analytics API router.

Provides read-only analytics endpoints for store owners to view profit
summaries, revenue time series, top products, and combined dashboard data.

**For Developers:**
    The router is nested under stores: ``/stores/{store_id}/analytics/...``
    (full path: ``/api/v1/stores/{store_id}/analytics/...``).
    The ``get_current_user`` dependency is used for authentication.
    Service functions in ``analytics_service`` compute all metrics.

**For QA Engineers:**
    - All endpoints return 401 without a valid token.
    - All endpoints return 404 if the store doesn't belong to the current user.
    - The ``period`` query parameter accepts ``7d``, ``30d``, ``90d``, ``365d``.
    - Revenue time series returns data points grouped by day.
    - Top products are sorted by profit descending.
    - Dashboard endpoint combines summary, revenue, and top products.

**For End Users:**
    - View your store's profit summary for different time periods.
    - Track revenue trends over time with charts.
    - Identify your most profitable products.
    - Access a combined dashboard view for a quick business overview.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    ProfitSummaryResponse,
    RevenueTimeSeriesPoint,
    RevenueTimeSeriesResponse,
    TopProductResponse,
    TopProductsResponse,
)

router = APIRouter(prefix="/stores/{store_id}/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

VALID_PERIODS = {"7d", "30d", "90d", "365d"}


@router.get("/summary", response_model=ProfitSummaryResponse)
async def get_profit_summary_endpoint(
    store_id: uuid.UUID,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or 365d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfitSummaryResponse:
    """Get a profit summary for the store over a given period.

    Computes total revenue, costs, profit, margin, order count,
    average order value, and refund total for the specified time window.

    Args:
        store_id: The UUID of the store.
        period: Time period string (7d, 30d, 90d, or 365d).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        ProfitSummaryResponse with aggregated financial metrics.

    Raises:
        HTTPException 400: If the period value is invalid.
        HTTPException 404: If the store is not found or belongs to another user.
    """
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
        )

    from app.services import analytics_service

    try:
        summary = await analytics_service.get_profit_summary(
            db, store_id=store_id, user_id=current_user.id, period=period
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    total_revenue = summary.get("total_revenue", Decimal("0.00"))
    order_count = summary.get("order_count", 0)
    average_order_value = (
        total_revenue / order_count if order_count > 0 else Decimal("0.00")
    )

    return ProfitSummaryResponse(
        period=summary.get("period", period),
        total_revenue=total_revenue,
        total_cost=summary.get("total_cost", Decimal("0.00")),
        total_profit=summary.get("profit", Decimal("0.00")),
        profit_margin=summary.get("margin", 0.0),
        total_orders=order_count,
        average_order_value=average_order_value,
        refund_total=summary.get("refund_total", Decimal("0.00")),
    )


@router.get("/revenue", response_model=RevenueTimeSeriesResponse)
async def get_revenue_time_series_endpoint(
    store_id: uuid.UUID,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or 365d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RevenueTimeSeriesResponse:
    """Get revenue time series data for charting.

    Returns daily data points with revenue, cost, profit, and order
    counts for the specified period.

    Args:
        store_id: The UUID of the store.
        period: Time period string (7d, 30d, 90d, or 365d).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        RevenueTimeSeriesResponse with daily data points.

    Raises:
        HTTPException 400: If the period value is invalid.
        HTTPException 404: If the store is not found or belongs to another user.
    """
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
        )

    from app.services import analytics_service

    try:
        data = await analytics_service.get_revenue_time_series(
            db, store_id=store_id, user_id=current_user.id, period=period
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    # Service returns list of dicts with keys: date, revenue, order_count
    # Map to RevenueTimeSeriesPoint fields (date, revenue, cost, profit, orders)
    data_points = [
        RevenueTimeSeriesPoint(
            date=d.get("date", ""),
            revenue=d.get("revenue", Decimal("0.00")),
            cost=d.get("cost", Decimal("0.00")),
            profit=d.get("profit", Decimal("0.00")),
            orders=d.get("order_count", d.get("orders", 0)),
        )
        for d in data
    ]
    return RevenueTimeSeriesResponse(period=period, data=data_points)


@router.get("/top-products", response_model=TopProductsResponse)
async def get_top_products_endpoint(
    store_id: uuid.UUID,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or 365d"),
    limit: int = Query(10, ge=1, le=50, description="Number of top products"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TopProductsResponse:
    """Get top products ranked by profit for the given period.

    Returns the most profitable products with their revenue, cost,
    profit, units sold, and margin data, wrapped in a response object
    that includes the period.

    Args:
        store_id: The UUID of the store.
        period: Time period string (7d, 30d, 90d, or 365d).
        limit: Maximum number of products to return (1-50, default 10).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        TopProductsResponse with period and a list of top products.

    Raises:
        HTTPException 400: If the period value is invalid.
        HTTPException 404: If the store is not found or belongs to another user.
    """
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
        )

    from app.services import analytics_service

    try:
        products = await analytics_service.get_top_products(
            db,
            store_id=store_id,
            user_id=current_user.id,
            period=period,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    product_responses = [
        TopProductResponse(
            product_id=p["product_id"],
            product_title=p.get("product_title", ""),
            revenue=p.get("revenue", Decimal("0.00")),
            cost=p.get("cost", Decimal("0.00")),
            profit=p.get("profit", Decimal("0.00")),
            units_sold=p.get("units_sold", 0),
            margin=p.get("margin", 0.0),
        )
        for p in products
    ]
    return TopProductsResponse(period=period, products=product_responses)


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def get_dashboard_endpoint(
    store_id: uuid.UUID,
    period: str = Query("30d", description="Time period: 7d, 30d, 90d, or 365d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsDashboardResponse:
    """Get combined dashboard data for the store.

    Returns profit summary, revenue time series, and top products in
    a single request to minimize round trips for dashboard rendering.

    Args:
        store_id: The UUID of the store.
        period: Time period string (7d, 30d, 90d, or 365d).
        current_user: The authenticated store owner.
        db: Async database session injected by FastAPI.

    Returns:
        AnalyticsDashboardResponse combining summary, revenue, and top products.

    Raises:
        HTTPException 400: If the period value is invalid.
        HTTPException 404: If the store is not found or belongs to another user.
    """
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
        )

    from app.services import analytics_service

    try:
        dashboard = await analytics_service.get_dashboard_analytics(
            db, store_id=store_id, user_id=current_user.id, period=period
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    # Build summary response
    summary_data = dashboard["summary"]
    total_revenue = summary_data.get("total_revenue", Decimal("0.00"))
    order_count = summary_data.get("order_count", 0)
    average_order_value = (
        total_revenue / order_count if order_count > 0 else Decimal("0.00")
    )
    summary_resp = ProfitSummaryResponse(
        period=summary_data.get("period", period),
        total_revenue=total_revenue,
        total_cost=summary_data.get("total_cost", Decimal("0.00")),
        total_profit=summary_data.get("profit", Decimal("0.00")),
        profit_margin=summary_data.get("margin", 0.0),
        total_orders=order_count,
        average_order_value=average_order_value,
        refund_total=summary_data.get("refund_total", Decimal("0.00")),
    )

    # Build revenue time series response
    time_series_data = dashboard.get("time_series", [])
    time_series_points = [
        RevenueTimeSeriesPoint(
            date=d.get("date", ""),
            revenue=d.get("revenue", Decimal("0.00")),
            cost=d.get("cost", Decimal("0.00")),
            profit=d.get("profit", Decimal("0.00")),
            orders=d.get("order_count", d.get("orders", 0)),
        )
        for d in time_series_data
    ]
    revenue_resp = RevenueTimeSeriesResponse(period=period, data=time_series_points)

    # Build top products response
    top_products_data = dashboard.get("top_products", [])
    top_product_items = [
        TopProductResponse(
            product_id=p["product_id"],
            product_title=p.get("product_title", ""),
            revenue=p.get("revenue", Decimal("0.00")),
            cost=p.get("cost", Decimal("0.00")),
            profit=p.get("profit", Decimal("0.00")),
            units_sold=p.get("units_sold", 0),
            margin=p.get("margin", 0.0),
        )
        for p in top_products_data
    ]
    top_products_resp = TopProductsResponse(period=period, products=top_product_items)

    return AnalyticsDashboardResponse(
        summary=summary_resp,
        revenue=revenue_resp,
        top_products=top_products_resp,
    )
