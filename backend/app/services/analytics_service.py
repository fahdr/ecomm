"""Analytics business logic.

Provides profit analytics, revenue time series, and top product
performance data for store owners. All calculations are based on
order data and product costs stored in the database.

**For Developers:**
    Period parsing converts shorthand strings like ``"30d"``, ``"7d"``,
    ``"90d"`` into date ranges. Revenue comes from paid/shipped/delivered
    orders. Cost comes from the product ``cost`` field (supplier cost)
    at the time of query (not snapshotted at order time -- a known
    simplification for MVP). Granularity options for time series are
    ``day``, ``week``, and ``month``.

**For QA Engineers:**
    - ``get_profit_summary`` excludes pending and cancelled orders.
    - ``get_revenue_time_series`` groups by PostgreSQL ``date_trunc``.
    - ``get_top_products`` ranks by revenue and includes profit margin.
    - ``get_dashboard_analytics`` combines all three in a single call.
    - All functions verify store ownership before returning data.

**For Project Managers:**
    This service powers Feature 13 (Profit Analytics) from the backlog.
    It gives store owners visibility into their revenue, costs, and
    margins to make data-driven sourcing decisions.

**For End Users:**
    View your store's revenue, costs, and profit on the analytics
    dashboard. See daily/weekly/monthly trends and identify your
    best-selling and most profitable products.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select, extract, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.store import Store, StoreStatus


async def _verify_store_ownership(
    db: AsyncSession, store_id: uuid.UUID, user_id: uuid.UUID
) -> Store:
    """Verify that a store exists and belongs to the given user.

    Args:
        db: Async database session.
        store_id: The UUID of the store.
        user_id: The requesting user's UUID.

    Returns:
        The Store ORM instance.

    Raises:
        ValueError: If the store doesn't exist, is deleted, or belongs
            to a different user.
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()
    if store is None or store.status == StoreStatus.deleted:
        raise ValueError("Store not found")
    if store.user_id != user_id:
        raise ValueError("Store not found")
    return store


def _parse_period(period: str) -> datetime:
    """Parse a period shorthand string into a start datetime.

    Supported formats: ``"7d"`` (7 days), ``"30d"`` (30 days),
    ``"90d"`` (90 days), ``"365d"`` (1 year). Defaults to 30 days
    if the format is not recognised.

    Args:
        period: Period shorthand string (e.g. ``"30d"``).

    Returns:
        A timezone-aware UTC datetime representing the start of the period.
    """
    now = datetime.now(timezone.utc)
    try:
        if period.endswith("d"):
            days = int(period[:-1])
            return now - timedelta(days=days)
    except (ValueError, IndexError):
        pass
    # Default to 30 days
    return now - timedelta(days=30)


# Statuses that count as completed revenue
_REVENUE_STATUSES = [OrderStatus.paid, OrderStatus.shipped, OrderStatus.delivered]


async def get_profit_summary(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    period: str = "30d",
) -> dict:
    """Calculate profit summary for a store over a time period.

    Revenue is the sum of order totals for paid/shipped/delivered orders.
    Cost is estimated from the product ``cost`` field multiplied by
    quantities sold. Profit is revenue minus cost.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        period: Time period shorthand (e.g. ``"30d"``, ``"7d"``).

    Returns:
        A dict with ``total_revenue``, ``total_cost``, ``profit``,
        ``margin`` (percentage), ``order_count``, and ``period``.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)
    period_start = _parse_period(period)

    # Total revenue
    revenue_result = await db.execute(
        select(
            func.coalesce(func.sum(Order.total), Decimal("0.00")),
            func.count(Order.id),
        ).where(
            Order.store_id == store_id,
            Order.status.in_(_REVENUE_STATUSES),
            Order.created_at >= period_start,
        )
    )
    revenue_row = revenue_result.one()
    total_revenue = revenue_row[0]
    order_count = revenue_row[1]

    # Total cost (from product cost * quantity)
    cost_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    func.coalesce(Product.cost, Decimal("0.00")) * OrderItem.quantity
                ),
                Decimal("0.00"),
            )
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            Order.store_id == store_id,
            Order.status.in_(_REVENUE_STATUSES),
            Order.created_at >= period_start,
        )
    )
    total_cost = cost_result.scalar_one()

    profit = total_revenue - total_cost
    margin = (
        float(profit / total_revenue * 100) if total_revenue > 0 else 0.0
    )

    return {
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "profit": profit,
        "margin": round(margin, 2),
        "order_count": order_count,
        "period": period,
    }


async def get_revenue_time_series(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    period: str = "30d",
    granularity: str = "day",
) -> list[dict]:
    """Get revenue grouped by time intervals.

    Uses PostgreSQL ``date_trunc`` to aggregate order totals by day,
    week, or month.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        period: Time period shorthand (e.g. ``"30d"``).
        granularity: Aggregation interval: ``"day"``, ``"week"``, or
            ``"month"``.

    Returns:
        A list of dicts with ``date`` (ISO string), ``revenue``, and
        ``order_count`` for each interval.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)
    period_start = _parse_period(period)

    if granularity not in ("day", "week", "month"):
        granularity = "day"

    date_trunc = func.date_trunc(granularity, Order.created_at)

    result = await db.execute(
        select(
            date_trunc.label("period_date"),
            func.coalesce(func.sum(Order.total), Decimal("0.00")).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .where(
            Order.store_id == store_id,
            Order.status.in_(_REVENUE_STATUSES),
            Order.created_at >= period_start,
        )
        .group_by(date_trunc)
        .order_by(date_trunc)
    )

    time_series = []
    for row in result.fetchall():
        time_series.append({
            "date": row.period_date.isoformat() if row.period_date else None,
            "revenue": row.revenue,
            "order_count": row.order_count,
        })

    return time_series


async def get_top_products(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    period: str = "30d",
    limit: int = 10,
) -> list[dict]:
    """Get top-performing products by revenue.

    Ranks products by total revenue (unit_price * quantity) from orders
    within the period. Includes cost and profit calculations.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        period: Time period shorthand (e.g. ``"30d"``).
        limit: Maximum number of products to return (default 10).

    Returns:
        A list of dicts with ``product_id``, ``product_title``,
        ``revenue``, ``cost``, ``profit``, ``units_sold``, and ``margin``.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    await _verify_store_ownership(db, store_id, user_id)
    period_start = _parse_period(period)

    result = await db.execute(
        select(
            OrderItem.product_id,
            OrderItem.product_title,
            func.sum(OrderItem.unit_price * OrderItem.quantity).label("revenue"),
            func.sum(
                func.coalesce(Product.cost, Decimal("0.00")) * OrderItem.quantity
            ).label("cost"),
            func.sum(OrderItem.quantity).label("units_sold"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .outerjoin(Product, OrderItem.product_id == Product.id)
        .where(
            Order.store_id == store_id,
            Order.status.in_(_REVENUE_STATUSES),
            Order.created_at >= period_start,
        )
        .group_by(OrderItem.product_id, OrderItem.product_title)
        .order_by(func.sum(OrderItem.unit_price * OrderItem.quantity).desc())
        .limit(limit)
    )

    top_products = []
    for row in result.fetchall():
        revenue = row.revenue or Decimal("0.00")
        cost = row.cost or Decimal("0.00")
        profit = revenue - cost
        margin = float(profit / revenue * 100) if revenue > 0 else 0.0

        top_products.append({
            "product_id": row.product_id,
            "product_title": row.product_title,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "units_sold": row.units_sold,
            "margin": round(margin, 2),
        })

    return top_products


async def get_dashboard_analytics(
    db: AsyncSession,
    store_id: uuid.UUID,
    user_id: uuid.UUID,
    period: str = "30d",
) -> dict:
    """Get a comprehensive analytics dashboard payload.

    Combines profit summary, revenue time series, and top products
    into a single response for the dashboard overview.

    Args:
        db: Async database session.
        store_id: The store's UUID.
        user_id: The requesting user's UUID (for ownership check).
        period: Time period shorthand (e.g. ``"30d"``).

    Returns:
        A dict with ``summary``, ``time_series``, and ``top_products`` keys.

    Raises:
        ValueError: If the store doesn't exist or belongs to another user.
    """
    summary = await get_profit_summary(db, store_id, user_id, period)
    time_series = await get_revenue_time_series(db, store_id, user_id, period)
    top_products = await get_top_products(db, store_id, user_id, period)

    return {
        "summary": summary,
        "time_series": time_series,
        "top_products": top_products,
    }
