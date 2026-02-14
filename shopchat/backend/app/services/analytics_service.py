"""
Analytics service for conversation and chatbot statistics.

Provides aggregated metrics for the analytics dashboard: conversation
counts, message totals, satisfaction scores, per-chatbot breakdowns,
and session-level analytics recording and summarization.

For Developers:
    All queries are scoped to the authenticated user's chatbots.
    Analytics are computed on-the-fly from the database -- no
    pre-computed aggregation tables. Session-level analytics are
    stored in the ChatAnalytics model for richer querying.
    For high-volume production use, consider materialized views.

For QA Engineers:
    Test analytics with varying amounts of data (0, 1, many).
    Verify that averages handle null satisfaction scores correctly.
    Test per-chatbot analytics match the overview totals.
    Test session analytics recording and summary aggregation.

For Project Managers:
    Analytics help users understand chatbot performance:
    conversation volume, customer satisfaction, and usage patterns.
    Session-level analytics provide deeper insights into topics
    and resolution rates.

For End Users:
    View your chatbot analytics on the dashboard to understand
    how your AI assistant is performing and what customers ask about.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_analytics import ChatAnalytics
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.message import Message


async def get_overview_analytics(
    db: AsyncSession, user_id: uuid.UUID
) -> dict:
    """
    Get overview analytics across all of a user's chatbots.

    Computes total conversations, messages, average satisfaction,
    active chatbot count, today's conversations, and the top chatbot.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Dict with analytics fields matching AnalyticsOverview schema.
    """
    # Total conversations
    conv_count_result = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == user_id)
    )
    total_conversations = conv_count_result.scalar() or 0

    # Total messages
    msg_count_result = await db.execute(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == user_id)
    )
    total_messages = msg_count_result.scalar() or 0

    # Average satisfaction (exclude nulls)
    avg_sat_result = await db.execute(
        select(func.avg(Conversation.satisfaction_score))
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Chatbot.user_id == user_id,
            Conversation.satisfaction_score.isnot(None),
        )
    )
    avg_satisfaction_raw = avg_sat_result.scalar()
    avg_satisfaction = round(float(avg_satisfaction_raw), 2) if avg_satisfaction_raw else None

    # Active chatbots
    active_result = await db.execute(
        select(func.count()).where(
            Chatbot.user_id == user_id,
            Chatbot.is_active.is_(True),
        )
    )
    active_chatbots = active_result.scalar() or 0

    # Conversations today
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Chatbot.user_id == user_id,
            Conversation.started_at >= today_start,
        )
    )
    conversations_today = today_result.scalar() or 0

    # Top chatbot by conversation count
    top_chatbot_result = await db.execute(
        select(Chatbot.name, func.count(Conversation.id).label("conv_count"))
        .join(Conversation, Chatbot.id == Conversation.chatbot_id, isouter=True)
        .where(Chatbot.user_id == user_id)
        .group_by(Chatbot.id, Chatbot.name)
        .order_by(func.count(Conversation.id).desc())
        .limit(1)
    )
    top_row = top_chatbot_result.first()
    top_chatbot_name = top_row[0] if top_row and top_row[1] > 0 else None

    return {
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "avg_satisfaction": avg_satisfaction,
        "active_chatbots": active_chatbots,
        "conversations_today": conversations_today,
        "top_chatbot_name": top_chatbot_name,
    }


async def get_chatbot_analytics(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    """
    Get per-chatbot analytics for all of a user's chatbots.

    Computes conversation count, message count, average satisfaction,
    and average messages per conversation for each chatbot.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of dicts matching ChatbotAnalytics schema.
    """
    # Subquery for message counts per conversation
    msg_subq = (
        select(
            Conversation.chatbot_id,
            func.count(Message.id).label("msg_count"),
        )
        .join(Message, Conversation.id == Message.conversation_id, isouter=True)
        .group_by(Conversation.chatbot_id)
        .subquery()
    )

    # Main query
    result = await db.execute(
        select(
            Chatbot.id,
            Chatbot.name,
            func.count(Conversation.id).label("conv_count"),
            func.coalesce(msg_subq.c.msg_count, 0).label("total_messages"),
            func.avg(Conversation.satisfaction_score).label("avg_sat"),
        )
        .join(Conversation, Chatbot.id == Conversation.chatbot_id, isouter=True)
        .outerjoin(msg_subq, Chatbot.id == msg_subq.c.chatbot_id)
        .where(Chatbot.user_id == user_id)
        .group_by(Chatbot.id, Chatbot.name, msg_subq.c.msg_count)
        .order_by(func.count(Conversation.id).desc())
    )

    analytics = []
    for row in result.all():
        conv_count = row.conv_count or 0
        total_msgs = row.total_messages or 0
        avg_msgs = round(total_msgs / conv_count, 1) if conv_count > 0 else 0.0
        avg_sat = round(float(row.avg_sat), 2) if row.avg_sat else None

        analytics.append({
            "chatbot_id": row.id,
            "chatbot_name": row.name,
            "total_conversations": conv_count,
            "total_messages": total_msgs,
            "avg_satisfaction": avg_sat,
            "avg_messages_per_conversation": avg_msgs,
        })

    return analytics


async def record_session_analytics(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    satisfaction_score: float | None = None,
    feedback_text: str | None = None,
    topic: str | None = None,
    resolved: bool = False,
    response_time_avg_ms: int = 0,
    message_count: int = 0,
) -> ChatAnalytics:
    """
    Record analytics for a completed chat session.

    Creates a ChatAnalytics record with the session's performance
    metrics. Called when a conversation ends or is rated.

    Args:
        db: Async database session.
        user_id: The chatbot owner's UUID.
        session_id: The conversation UUID.
        satisfaction_score: Visitor satisfaction rating (1.0-5.0, optional).
        feedback_text: Optional text feedback from the visitor.
        topic: Extracted topic/category of the conversation.
        resolved: Whether the visitor's question was resolved.
        response_time_avg_ms: Average AI response time in milliseconds.
        message_count: Total messages exchanged in the session.

    Returns:
        The created ChatAnalytics record.
    """
    # Check if analytics already exist for this session
    result = await db.execute(
        select(ChatAnalytics).where(ChatAnalytics.session_id == session_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record
        if satisfaction_score is not None:
            existing.satisfaction_score = satisfaction_score
        if feedback_text is not None:
            existing.feedback_text = feedback_text
        if topic is not None:
            existing.topic = topic
        existing.resolved = resolved
        if response_time_avg_ms > 0:
            existing.response_time_avg_ms = response_time_avg_ms
        if message_count > 0:
            existing.message_count = message_count
        await db.flush()
        return existing

    analytics = ChatAnalytics(
        user_id=user_id,
        session_id=session_id,
        satisfaction_score=satisfaction_score,
        feedback_text=feedback_text,
        topic=topic,
        resolved=resolved,
        response_time_avg_ms=response_time_avg_ms,
        message_count=message_count,
    )
    db.add(analytics)
    await db.flush()
    return analytics


async def get_analytics_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 30,
) -> dict:
    """
    Get an aggregated analytics summary for a user's chat sessions.

    Computes total sessions, average satisfaction, resolution rate,
    top topics, and average response time for the specified time period.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        days: Number of days to include in the summary (default: 30).

    Returns:
        Dict with 'total_sessions', 'avg_satisfaction', 'resolution_rate',
        'top_topics' (list of dicts), and 'avg_response_time_ms'.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Total sessions
    count_result = await db.execute(
        select(func.count()).where(
            ChatAnalytics.user_id == user_id,
            ChatAnalytics.created_at >= cutoff,
        )
    )
    total_sessions = count_result.scalar() or 0

    if total_sessions == 0:
        return {
            "total_sessions": 0,
            "avg_satisfaction": None,
            "resolution_rate": 0.0,
            "top_topics": [],
            "avg_response_time_ms": 0.0,
        }

    # Average satisfaction
    avg_sat_result = await db.execute(
        select(func.avg(ChatAnalytics.satisfaction_score)).where(
            ChatAnalytics.user_id == user_id,
            ChatAnalytics.created_at >= cutoff,
            ChatAnalytics.satisfaction_score.isnot(None),
        )
    )
    avg_sat_raw = avg_sat_result.scalar()
    avg_satisfaction = round(float(avg_sat_raw), 2) if avg_sat_raw else None

    # Resolution rate
    resolved_result = await db.execute(
        select(func.count()).where(
            ChatAnalytics.user_id == user_id,
            ChatAnalytics.created_at >= cutoff,
            ChatAnalytics.resolved.is_(True),
        )
    )
    resolved_count = resolved_result.scalar() or 0
    resolution_rate = round((resolved_count / total_sessions) * 100, 1)

    # Top topics
    topic_result = await db.execute(
        select(
            ChatAnalytics.topic,
            func.count().label("count"),
        )
        .where(
            ChatAnalytics.user_id == user_id,
            ChatAnalytics.created_at >= cutoff,
            ChatAnalytics.topic.isnot(None),
        )
        .group_by(ChatAnalytics.topic)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_topics = [
        {"topic": row.topic, "count": row.count}
        for row in topic_result.all()
    ]

    # Average response time
    avg_time_result = await db.execute(
        select(func.avg(ChatAnalytics.response_time_avg_ms)).where(
            ChatAnalytics.user_id == user_id,
            ChatAnalytics.created_at >= cutoff,
            ChatAnalytics.response_time_avg_ms > 0,
        )
    )
    avg_time_raw = avg_time_result.scalar()
    avg_response_time_ms = round(float(avg_time_raw), 1) if avg_time_raw else 0.0

    return {
        "total_sessions": total_sessions,
        "avg_satisfaction": avg_satisfaction,
        "resolution_rate": resolution_rate,
        "top_topics": top_topics,
        "avg_response_time_ms": avg_response_time_ms,
    }
