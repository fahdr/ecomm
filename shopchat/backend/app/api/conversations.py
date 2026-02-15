"""
Conversation management API routes.

Provides endpoints for listing conversations, viewing conversation
details with messages, ending conversations, and rating satisfaction.

For Developers:
    Conversations are scoped through chatbot ownership. The list endpoint
    supports optional chatbot_id filtering and pagination.

For QA Engineers:
    Test conversation listing, detail view with messages, ending
    conversations, and satisfaction rating validation (1-5 range).

For Project Managers:
    These endpoints power the Conversations page in the dashboard,
    allowing users to review chat history and customer satisfaction.

For End Users:
    View your chatbot conversations, read message threads, and
    see how satisfied your customers are.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.chatbot import Chatbot
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.chat import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    PaginatedResponse,
    SatisfactionRating,
)
from app.services.chat_service import end_conversation, rate_conversation

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=PaginatedResponse)
async def list_conversations_endpoint(
    chatbot_id: uuid.UUID | None = Query(None, description="Filter by chatbot"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List conversations for the current user's chatbots.

    Supports optional filtering by chatbot_id and pagination.

    Args:
        chatbot_id: Optional chatbot UUID to filter by.
        page: Page number (1-based).
        page_size: Items per page.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of conversations.
    """
    base_query = (
        select(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == current_user.id)
    )
    count_query = (
        select(func.count())
        .select_from(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == current_user.id)
    )

    if chatbot_id:
        base_query = base_query.where(Conversation.chatbot_id == chatbot_id)
        count_query = count_query.where(Conversation.chatbot_id == chatbot_id)

    # Total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        base_query
        .order_by(Conversation.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    conversations = list(result.scalars().all())

    return PaginatedResponse(
        items=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_endpoint(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a conversation with its full message history.

    Args:
        conversation_id: The conversation's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Conversation detail with all messages.

    Raises:
        HTTPException: 404 if conversation not found or not owned by user.
    """
    result = await db.execute(
        select(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Conversation.id == conversation_id,
            Chatbot.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return ConversationDetailResponse(
        id=conversation.id,
        chatbot_id=conversation.chatbot_id,
        visitor_id=conversation.visitor_id,
        visitor_name=conversation.visitor_name,
        started_at=conversation.started_at,
        ended_at=conversation.ended_at,
        message_count=conversation.message_count,
        satisfaction_score=conversation.satisfaction_score,
        status=conversation.status,
        messages=[MessageResponse.model_validate(m) for m in conversation.messages],
    )


@router.post("/{conversation_id}/end", response_model=ConversationResponse)
async def end_conversation_endpoint(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    End an active conversation.

    Sets the status to "ended" and records the end timestamp.

    Args:
        conversation_id: The conversation's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The ended conversation.

    Raises:
        HTTPException: 404 if not found, 400 if already ended.
    """
    result = await db.execute(
        select(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Conversation.id == conversation_id,
            Chatbot.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if conversation.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation is not active",
        )

    ended = await end_conversation(db, conversation)
    return ended


@router.post("/{conversation_id}/rate", response_model=ConversationResponse)
async def rate_conversation_endpoint(
    conversation_id: uuid.UUID,
    body: SatisfactionRating,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Rate a conversation with a satisfaction score.

    Args:
        conversation_id: The conversation's UUID.
        body: Satisfaction rating (1.0 to 5.0).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The rated conversation.

    Raises:
        HTTPException: 404 if conversation not found.
    """
    result = await db.execute(
        select(Conversation)
        .join(Chatbot, Conversation.chatbot_id == Chatbot.id)
        .where(
            Conversation.id == conversation_id,
            Chatbot.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    rated = await rate_conversation(db, conversation, body.score)
    return rated
