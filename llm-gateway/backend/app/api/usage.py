"""
Usage analytics endpoints for the LLM Gateway.

Provides cost and usage aggregations for the admin dashboard.

For Developers:
    Queries the ``llm_usage_logs`` table with various GROUP BY dimensions.
    All endpoints return JSON-serializable dicts.

For QA Engineers:
    Seed some usage logs and verify aggregation results.

For Project Managers:
    These endpoints power the cost dashboard showing spend by
    provider, service, customer, and time period.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.generate import _verify_service_key
from app.database import get_db
from app.models.usage_log import UsageLog

router = APIRouter()


@router.get("/summary")
async def usage_summary(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Get a high-level usage summary for the last N days.

    Args:
        days: Number of days to look back (default: 30).

    Returns:
        Dict with total_requests, total_cost, total_tokens, cached_requests.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            func.count(UsageLog.id).label("total_requests"),
            func.coalesce(func.sum(UsageLog.cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(UsageLog.input_tokens + UsageLog.output_tokens), 0).label("total_tokens"),
            func.count(UsageLog.id).filter(UsageLog.cached.is_(True)).label("cached_requests"),
            func.count(UsageLog.id).filter(UsageLog.error.isnot(None)).label("error_requests"),
        ).where(UsageLog.created_at >= since)
    )
    row = result.one()
    return {
        "period_days": days,
        "total_requests": row.total_requests,
        "total_cost_usd": round(float(row.total_cost), 4),
        "total_tokens": int(row.total_tokens),
        "cached_requests": row.cached_requests,
        "error_requests": row.error_requests,
        "cache_hit_rate": round(
            row.cached_requests / row.total_requests * 100, 1
        ) if row.total_requests > 0 else 0,
    }


@router.get("/by-provider")
async def usage_by_provider(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Get usage breakdown by provider.

    Returns:
        List of dicts with provider_name, request_count, total_cost, avg_latency.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            UsageLog.provider_name,
            func.count(UsageLog.id).label("request_count"),
            func.sum(UsageLog.cost_usd).label("total_cost"),
            func.avg(UsageLog.latency_ms).label("avg_latency_ms"),
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total_tokens"),
        )
        .where(UsageLog.created_at >= since)
        .group_by(UsageLog.provider_name)
        .order_by(func.sum(UsageLog.cost_usd).desc())
    )
    return [
        {
            "provider_name": row.provider_name,
            "request_count": row.request_count,
            "total_cost_usd": round(float(row.total_cost or 0), 4),
            "avg_latency_ms": int(row.avg_latency_ms or 0),
            "total_tokens": int(row.total_tokens or 0),
        }
        for row in result
    ]


@router.get("/by-service")
async def usage_by_service(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Get usage breakdown by calling service.

    Returns:
        List of dicts with service_name, request_count, total_cost.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            UsageLog.service_name,
            func.count(UsageLog.id).label("request_count"),
            func.sum(UsageLog.cost_usd).label("total_cost"),
            func.sum(UsageLog.input_tokens + UsageLog.output_tokens).label("total_tokens"),
        )
        .where(UsageLog.created_at >= since)
        .group_by(UsageLog.service_name)
        .order_by(func.sum(UsageLog.cost_usd).desc())
    )
    return [
        {
            "service_name": row.service_name,
            "request_count": row.request_count,
            "total_cost_usd": round(float(row.total_cost or 0), 4),
            "total_tokens": int(row.total_tokens or 0),
        }
        for row in result
    ]


@router.get("/by-customer")
async def usage_by_customer(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Get usage breakdown by customer (user_id).

    Returns:
        List of top N customers by cost.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(
            UsageLog.user_id,
            func.count(UsageLog.id).label("request_count"),
            func.sum(UsageLog.cost_usd).label("total_cost"),
        )
        .where(UsageLog.created_at >= since)
        .group_by(UsageLog.user_id)
        .order_by(func.sum(UsageLog.cost_usd).desc())
        .limit(limit)
    )
    return [
        {
            "user_id": row.user_id,
            "request_count": row.request_count,
            "total_cost_usd": round(float(row.total_cost or 0), 4),
        }
        for row in result
    ]
