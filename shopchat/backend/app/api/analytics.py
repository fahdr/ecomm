"""
Analytics API routes for chatbot performance metrics.

Provides overview, per-chatbot, and session-level analytics endpoints
for the dashboard analytics page. Also includes the session rating
endpoint for satisfaction feedback.

For Developers:
    Analytics are computed on-the-fly from database aggregations.
    All endpoints require authentication and scope data to the
    current user's chatbots. Session analytics use the ChatAnalytics
    model for richer per-session tracking.

For QA Engineers:
    Test with zero data (new account), single chatbot, and
    multiple chatbots. Verify average calculations handle nulls.
    Test session rating and analytics summary endpoints.

For Project Managers:
    These endpoints power the Analytics page in the dashboard,
    providing insights into chatbot usage and customer satisfaction.

For End Users:
    View your chatbot performance metrics on the Analytics page.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import (
    AnalyticsOverview,
    AnalyticsSummary,
    ChatbotAnalytics,
    ConversationResponse,
    SessionRating,
)
from app.services.analytics_service import (
    get_analytics_summary,
    get_chatbot_analytics,
    get_overview_analytics,
    record_session_analytics,
)
from app.services.chat_service import rate_conversation

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


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get session-level analytics summary for a time period.

    Returns aggregated metrics from ChatAnalytics records: total sessions,
    average satisfaction, resolution rate, top topics, and response time.

    Args:
        days: Number of days to include (1-365, default: 30).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        AnalyticsSummary with session-level aggregated metrics.
    """
    data = await get_analytics_summary(db, current_user.id, days=days)
    return AnalyticsSummary(**data)


@router.post("/sessions/{session_id}/rate", response_model=ConversationResponse)
async def rate_session(
    session_id: uuid.UUID,
    body: SessionRating,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rate a chat session with a satisfaction score and optional feedback.

    Updates the conversation's satisfaction score and records session
    analytics with the rating and feedback text.

    Args:
        session_id: The conversation/session UUID.
        body: Rating with score (1-5) and optional feedback text.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated conversation with satisfaction score.

    Raises:
        HTTPException: 404 if session not found or not owned by user.
    """
    result = await db.execute(
        select(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Conversation.id == session_id,
            Chatbot.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Update conversation satisfaction score
    rated = await rate_conversation(db, conversation, body.score, body.feedback)

    # Record in session analytics
    await record_session_analytics(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        satisfaction_score=body.score,
        feedback_text=body.feedback,
        message_count=conversation.message_count,
    )

    return rated
