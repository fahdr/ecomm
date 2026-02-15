"""
Usage reporting router factory.

Creates a standardized usage endpoint that services and the platform can poll.

For Developers:
    Use `create_usage_router(get_db, get_current_user_or_api_key, get_usage_fn)`.
    The `get_usage_fn` is service-specific and returns usage metrics.
"""

from typing import Callable

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.models.user import User
from ecomm_core.schemas.billing import UsageMetric, UsageResponse


def create_usage_router(get_db, get_current_user_or_api_key, get_usage_fn: Callable) -> APIRouter:
    """
    Factory to create the usage router.

    Args:
        get_db: FastAPI dependency for database session.
        get_current_user_or_api_key: FastAPI dependency for dual auth.
        get_usage_fn: Async function(db, user) -> dict with usage data.

    Returns:
        APIRouter with GET /usage endpoint.
    """
    router = APIRouter(tags=["usage"])

    @router.get("/usage", response_model=UsageResponse)
    async def get_usage_report(
        current_user: User = Depends(get_current_user_or_api_key),
        db: AsyncSession = Depends(get_db),
    ):
        """
        Get current usage metrics for the billing period.

        Accepts both JWT Bearer token and X-API-Key authentication.
        """
        usage_data = await get_usage_fn(db, current_user)
        return UsageResponse(
            plan=usage_data["plan"],
            period_start=usage_data["period_start"],
            period_end=usage_data["period_end"],
            metrics=[UsageMetric(**m) for m in usage_data["metrics"]],
        )

    return router
