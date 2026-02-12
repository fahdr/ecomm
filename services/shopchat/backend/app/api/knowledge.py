"""
Knowledge base CRUD API routes.

Provides endpoints for creating, listing, retrieving, updating, and
deleting knowledge base entries. Enforces plan-based limits on the
number of entries a user can create.

For Developers:
    Knowledge entries belong to a chatbot. Ownership is verified by
    checking that the chatbot belongs to the authenticated user.
    Plan limits are checked before creation via `check_knowledge_limit`.

For QA Engineers:
    Test CRUD operations, verify plan limit enforcement (403 when at limit),
    and test entry scoping (entries from other chatbots are not accessible).

For Project Managers:
    Knowledge base pages are the secondary billing metric.
    These endpoints power the Knowledge Base page in the dashboard.

For End Users:
    Add product info, FAQs, and policies to your chatbot's knowledge base.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    PaginatedResponse,
)
from app.services.chatbot_service import get_chatbot_by_id
from app.services.knowledge_service import (
    check_knowledge_limit,
    create_knowledge_entry,
    delete_knowledge_entry,
    get_knowledge_entry,
    list_all_user_knowledge_entries,
    list_knowledge_entries,
    update_knowledge_entry,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry_endpoint(
    body: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new knowledge base entry.

    Validates chatbot ownership and checks plan limits before creation.

    Args:
        body: Entry creation data (chatbot_id, source_type, title, content).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created knowledge base entry.

    Raises:
        HTTPException: 404 if chatbot not found, 403 if plan limit reached.
    """
    # Verify chatbot ownership
    chatbot = await get_chatbot_by_id(db, body.chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )

    # Check plan limits
    within_limit = await check_knowledge_limit(db, current_user)
    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base page limit reached for your plan. Upgrade to add more.",
        )

    entry = await create_knowledge_entry(
        db=db,
        chatbot_id=body.chatbot_id,
        source_type=body.source_type,
        title=body.title,
        content=body.content,
        metadata=body.metadata,
    )
    return entry


@router.get("", response_model=PaginatedResponse)
async def list_knowledge_entries_endpoint(
    chatbot_id: uuid.UUID | None = Query(None, description="Filter by chatbot"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List knowledge base entries with optional chatbot filter.

    If chatbot_id is provided, returns entries for that chatbot only.
    Otherwise returns all entries across the user's chatbots.

    Args:
        chatbot_id: Optional chatbot UUID to filter by.
        page: Page number (1-based).
        page_size: Items per page.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of knowledge base entries.
    """
    if chatbot_id:
        # Verify chatbot ownership
        chatbot = await get_chatbot_by_id(db, chatbot_id, current_user.id)
        if not chatbot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbot not found",
            )
        entries, total = await list_knowledge_entries(db, chatbot_id, page, page_size)
    else:
        entries, total = await list_all_user_knowledge_entries(
            db, current_user.id, page, page_size
        )

    return PaginatedResponse(
        items=[KnowledgeBaseResponse.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{entry_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_entry_endpoint(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single knowledge base entry by ID.

    Verifies ownership via the chatbot -> user chain.

    Args:
        entry_id: The entry's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The knowledge base entry.

    Raises:
        HTTPException: 404 if entry not found or not owned by user.
    """
    entry = await get_knowledge_entry(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    # Verify ownership through chatbot
    chatbot = await get_chatbot_by_id(db, entry.chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    return entry


@router.patch("/{entry_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_entry_endpoint(
    entry_id: uuid.UUID,
    body: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a knowledge base entry.

    Args:
        entry_id: The entry's UUID.
        body: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated knowledge base entry.

    Raises:
        HTTPException: 404 if entry not found.
    """
    entry = await get_knowledge_entry(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    # Verify ownership
    chatbot = await get_chatbot_by_id(db, entry.chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    updated = await update_knowledge_entry(
        db=db,
        entry=entry,
        source_type=body.source_type,
        title=body.title,
        content=body.content,
        metadata=body.metadata if body.metadata is not None else ...,
        is_active=body.is_active,
    )
    return updated


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_entry_endpoint(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a knowledge base entry.

    Args:
        entry_id: The entry's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException: 404 if entry not found.
    """
    entry = await get_knowledge_entry(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    # Verify ownership
    chatbot = await get_chatbot_by_id(db, entry.chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base entry not found",
        )

    await delete_knowledge_entry(db, entry)
