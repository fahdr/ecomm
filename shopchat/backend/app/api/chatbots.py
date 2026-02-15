"""
Chatbot CRUD API routes.

Provides endpoints for creating, listing, retrieving, updating, and
deleting chatbots. Also provides a public endpoint for retrieving
widget configuration by widget key (no auth required).

For Developers:
    All authenticated endpoints use `get_current_user` for JWT auth.
    The widget config endpoint is public (no auth) and uses the
    widget_key path parameter to identify the chatbot.

For QA Engineers:
    Test CRUD operations, verify user scoping (can't access other
    users' chatbots), and test the public widget config endpoint.

For Project Managers:
    These endpoints power the chatbot management page in the dashboard.

For End Users:
    Create and manage your AI chatbot assistants through these endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatbotCreate,
    ChatbotResponse,
    ChatbotUpdate,
    PaginatedResponse,
    WidgetConfig,
)
from app.services.chatbot_service import (
    create_chatbot,
    delete_chatbot,
    get_chatbot_by_id,
    get_chatbot_by_widget_key,
    list_chatbots,
    update_chatbot,
)

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


@router.post("", response_model=ChatbotResponse, status_code=status.HTTP_201_CREATED)
async def create_chatbot_endpoint(
    body: ChatbotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new chatbot.

    Generates a unique widget key for the chatbot. The chatbot is
    immediately ready for embedding on external websites.

    Args:
        body: Chatbot creation data (name, personality, etc.).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The newly created chatbot with its widget_key.
    """
    chatbot = await create_chatbot(
        db=db,
        user=current_user,
        name=body.name,
        personality=body.personality,
        welcome_message=body.welcome_message,
        theme_config=body.theme_config,
    )
    return chatbot


@router.get("", response_model=PaginatedResponse)
async def list_chatbots_endpoint(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's chatbots with pagination.

    Args:
        page: Page number (1-based).
        page_size: Items per page (max 100).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        Paginated list of chatbots.
    """
    chatbots, total = await list_chatbots(db, current_user.id, page, page_size)
    return PaginatedResponse(
        items=[ChatbotResponse.model_validate(c) for c in chatbots],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{chatbot_id}", response_model=ChatbotResponse)
async def get_chatbot_endpoint(
    chatbot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single chatbot by ID.

    Args:
        chatbot_id: The chatbot's UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The chatbot details.

    Raises:
        HTTPException: 404 if chatbot not found or not owned by user.
    """
    chatbot = await get_chatbot_by_id(db, chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
    return chatbot


@router.patch("/{chatbot_id}", response_model=ChatbotResponse)
async def update_chatbot_endpoint(
    chatbot_id: uuid.UUID,
    body: ChatbotUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a chatbot's fields.

    Only provided fields are updated.

    Args:
        chatbot_id: The chatbot's UUID.
        body: Fields to update.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The updated chatbot.

    Raises:
        HTTPException: 404 if chatbot not found.
    """
    chatbot = await get_chatbot_by_id(db, chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )

    updated = await update_chatbot(
        db=db,
        chatbot=chatbot,
        name=body.name,
        personality=body.personality,
        welcome_message=body.welcome_message,
        theme_config=body.theme_config,
        is_active=body.is_active,
    )
    return updated


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot_endpoint(
    chatbot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a chatbot and all its data (knowledge base, conversations).

    Args:
        chatbot_id: The chatbot's UUID.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException: 404 if chatbot not found.
    """
    chatbot = await get_chatbot_by_id(db, chatbot_id, current_user.id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbot not found",
        )
    await delete_chatbot(db, chatbot)
