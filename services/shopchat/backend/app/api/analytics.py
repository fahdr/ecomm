"""
Analytics API routes for chatbot performance metrics.

Provides overview and per-chatbot analytics endpoints for the
dashboard analytics page.

For Developers:
    Analytics are computed on-the-fly from database aggregations.
    Both endpoints require authentication and scope data to the
    current user's chatbots.

For QA Engineers:
    Test with zero data (new account), single chatbot, and
    multiple chatbots. Verify average calculations handle nulls.

For Project Managers:
    These endpoints power the Analytics page in the dashboard,
    providing insights into chatbot usage and customer satisfaction.

For End Users:
    View your chatbot performance metrics on the Analytics page.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import AnalyticsOverview, ChatbotAnalytics
from app.services.analytics_service import get_chatbot_analytics, get_overview_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get overview analytics across all chatbots.

    Returns aggregated metrics: total conversations, messages,
    average satisfaction, active chatbot count, and today's volume.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AnalyticsOverview with aggregated metrics.
    """
    data = await get_overview_analytics(db, current_user.id)
    return AnalyticsOverview(**data)


@router.get("/chatbots", response_model=list[ChatbotAnalytics])
async def get_per_chatbot_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get per-chatbot analytics for all of the user's chatbots.

    Returns a list of analytics breakdowns, one per chatbot, sorted
    by conversation count descending.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of ChatbotAnalytics for each chatbot.
    """
    data = await get_chatbot_analytics(db, current_user.id)
    return [ChatbotAnalytics(**d) for d in data]
