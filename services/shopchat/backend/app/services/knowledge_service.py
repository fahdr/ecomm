"""
Knowledge base service for CRUD operations and plan limit enforcement.

Handles creating, reading, updating, and deleting knowledge base entries.
Enforces plan-based limits on the number of knowledge base pages a user
can create across all their chatbots.

For Developers:
    Knowledge base entries are scoped to individual chatbots. Plan limits
    are checked against the total count across ALL of a user's chatbots.
    Use `check_knowledge_limit` before creating new entries.

For QA Engineers:
    Test CRUD operations, verify plan limit enforcement, and test
    that entries are correctly scoped to their chatbot.

For Project Managers:
    Knowledge base pages are the secondary billing metric (max_secondary).
    Free tier gets 10 pages, Pro gets 500, Enterprise gets unlimited.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.plans import PLAN_LIMITS
from app.models.chatbot import Chatbot
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User


async def count_user_knowledge_entries(
    db: AsyncSession, user_id: uuid.UUID
) -> int:
    """
    Count total knowledge base entries across all of a user's chatbots.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Integer count of knowledge base entries.
    """
    result = await db.execute(
        select(func.count())
        .select_from(KnowledgeBase)
        .join(Chatbot, KnowledgeBase.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == user_id)
    )
    return result.scalar() or 0


async def check_knowledge_limit(db: AsyncSession, user: User) -> bool:
    """
    Check if the user can create more knowledge base entries.

    Compares current count against the plan's max_secondary limit.
    Returns True if the user is within limits (can create more).

    Args:
        db: Async database session.
        user: The authenticated user.

    Returns:
        True if the user can create more entries, False if at limit.
    """
    plan_limits = PLAN_LIMITS[user.plan]
    if plan_limits.max_secondary == -1:
        return True  # Unlimited

    current_count = await count_user_knowledge_entries(db, user.id)
    return current_count < plan_limits.max_secondary


async def create_knowledge_entry(
    db: AsyncSession,
    chatbot_id: uuid.UUID,
    source_type: str,
    title: str,
    content: str,
    metadata: dict | None = None,
) -> KnowledgeBase:
    """
    Create a new knowledge base entry for a chatbot.

    Args:
        db: Async database session.
        chatbot_id: The parent chatbot's UUID.
        source_type: Origin type of the content.
        title: Human-readable entry title.
        content: Full text content for AI context.
        metadata: Optional extra structured data.

    Returns:
        The newly created KnowledgeBase entry.
    """
    entry = KnowledgeBase(
        chatbot_id=chatbot_id,
        source_type=source_type,
        title=title,
        content=content,
        metadata=metadata,
    )
    db.add(entry)
    await db.flush()
    return entry


async def get_knowledge_entry(
    db: AsyncSession, entry_id: uuid.UUID
) -> KnowledgeBase | None:
    """
    Get a single knowledge base entry by ID.

    Args:
        db: Async database session.
        entry_id: The entry's UUID.

    Returns:
        The KnowledgeBase entry if found, None otherwise.
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == entry_id)
    )
    return result.scalar_one_or_none()


async def list_knowledge_entries(
    db: AsyncSession,
    chatbot_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeBase], int]:
    """
    List knowledge base entries for a chatbot with pagination.

    Args:
        db: Async database session.
        chatbot_id: The parent chatbot's UUID.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Tuple of (list of KnowledgeBase entries, total count).
    """
    count_result = await db.execute(
        select(func.count()).where(KnowledgeBase.chatbot_id == chatbot_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.chatbot_id == chatbot_id)
        .order_by(KnowledgeBase.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    entries = list(result.scalars().all())

    return entries, total


async def list_all_user_knowledge_entries(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[KnowledgeBase], int]:
    """
    List all knowledge base entries across all of a user's chatbots.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-based).
        page_size: Items per page.

    Returns:
        Tuple of (list of KnowledgeBase entries, total count).
    """
    count_result = await db.execute(
        select(func.count())
        .select_from(KnowledgeBase)
        .join(Chatbot, KnowledgeBase.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == user_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(KnowledgeBase)
        .join(Chatbot, KnowledgeBase.chatbot_id == Chatbot.id)
        .where(Chatbot.user_id == user_id)
        .order_by(KnowledgeBase.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    entries = list(result.scalars().all())

    return entries, total


async def update_knowledge_entry(
    db: AsyncSession,
    entry: KnowledgeBase,
    source_type: str | None = None,
    title: str | None = None,
    content: str | None = None,
    metadata: dict | None = ...,  # type: ignore[assignment]
    is_active: bool | None = None,
) -> KnowledgeBase:
    """
    Update a knowledge base entry's fields.

    Uses the Ellipsis sentinel for metadata to distinguish "not provided"
    from explicit None.

    Args:
        db: Async database session.
        entry: The KnowledgeBase entry to update.
        source_type: Updated source type.
        title: Updated title.
        content: Updated content.
        metadata: Updated metadata (Ellipsis = not provided).
        is_active: Updated active status.

    Returns:
        The updated KnowledgeBase entry.
    """
    if source_type is not None:
        entry.source_type = source_type
    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    if metadata is not ...:
        entry.metadata = metadata
    if is_active is not None:
        entry.is_active = is_active

    await db.flush()
    return entry


async def delete_knowledge_entry(db: AsyncSession, entry: KnowledgeBase) -> None:
    """
    Delete a knowledge base entry.

    Args:
        db: Async database session.
        entry: The KnowledgeBase entry to delete.
    """
    await db.delete(entry)
    await db.flush()


async def get_active_entries_for_chatbot(
    db: AsyncSession, chatbot_id: uuid.UUID
) -> list[KnowledgeBase]:
    """
    Get all active knowledge base entries for a chatbot.

    Used by the chat service to build AI context from the knowledge base.

    Args:
        db: Async database session.
        chatbot_id: The chatbot's UUID.

    Returns:
        List of active KnowledgeBase entries.
    """
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.chatbot_id == chatbot_id,
            KnowledgeBase.is_active.is_(True),
        )
    )
    return list(result.scalars().all())
