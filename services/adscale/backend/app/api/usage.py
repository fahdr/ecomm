"""
Usage reporting endpoint for cross-service integration.

Provides a standardized usage report that the dropshipping platform
(or any integration) can poll to display billing metrics.

For Developers:
    This endpoint accepts both JWT and API key auth. Each service
    should override `get_usage()` in billing_service.py with actual metrics.

For QA Engineers:
    Test: usage endpoint returns correct metrics format, responds to
    both auth methods, and reflects actual resource counts.

For Project Managers:
    This endpoint enables the dropshipping platform to show aggregated
    usage across all connected services on the billing dashboard.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_or_api_key
from app.database import get_db
from app.models.user import User
from app.schemas.billing import UsageMetric, UsageResponse
from app.services.billing_service import get_usage

router = APIRouter(tags=["usage"])


@router.get("/usage", response_model=UsageResponse)
async def get_usage_report(
    current_user: User = Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current usage metrics for the billing period.

    Accepts both JWT Bearer token and X-API-Key authentication.
    Used by the dropshipping platform to sync usage data.

    Args:
        current_user: The authenticated user (via JWT or API key).
        db: Database session.

    Returns:
        UsageResponse with plan, period, and metric values.
    """
    usage_data = await get_usage(db, current_user)
    return UsageResponse(
        plan=usage_data["plan"],
        period_start=usage_data["period_start"],
        period_end=usage_data["period_end"],
        metrics=[UsageMetric(**m) for m in usage_data["metrics"]],
    )
