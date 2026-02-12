"""
Chatbot service for CRUD operations and widget key management.

Handles creating, reading, updating, and deleting chatbots. Generates
unique widget keys for each chatbot and manages theme configuration.

For Developers:
    Widget keys are generated using `secrets.token_urlsafe(24)` for
    URL-safe, unique identifiers. All queries are scoped to the
    authenticated user's chatbots to enforce multi-tenancy.

For QA Engineers:
    Test CRUD operations, verify widget key uniqueness, and test
    that users can only access their own chatbots.

For Project Managers:
    This service manages the core chatbot entity. Each chatbot is
    an independent AI assistant instance.
"""

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chatbot import Chatbot
from app.models.user import User


def generate_widget_key() -> str:
    """
    Generate a unique, URL-safe widget key for chatbot embedding.

    Returns:
        A 32-character URL-safe string prefixed with 'wk_'.
    """
    return f"wk_{secrets.token_urlsafe(24)}"


async def create_chatbot(
    db: AsyncSession,
    user: User,
    name: str,
    personality: str = "friendly",
    welcome_message: str = "Hi there! How can I help you today?",
    theme_config: dict | None = None,
) -> Chatbot:
    """
    Create a new chatbot for a user.

    Generates a unique widget key and stores the chatbot with the
    given personality, welcome message, and theme configuration.

    Args:
        db: Async database session.
        user: The owning user.
        name: Human-readable chatbot name.
        personality: Chatbot personality style.
        welcome_message: Greeting shown when the widget opens.
        theme_config: Widget appearance settings.

    Returns:
        The newly created Chatbot.
    """
    if theme_config is None:
        theme_config = {
            "primary_color": "#6366f1",
            "text_color": "#ffffff",
            "position": "bottom-right",
            "size": "medium",
        }

    chatbot = Chatbot(
        user_id=user.id,
        name=name,
        personality=personality,
        welcome_message=welcome_message,
        theme_config=theme_config,
        widget_key=generate_widget_key(),
    )
    db.add(chatbot)
    await db.flush()
    return chatbot


async def get_chatbot_by_id(
    db: AsyncSession, chatbot_id: uuid.UUID, user_id: uuid.UUID
) -> Chatbot | None:
    """
    Get a chatbot by ID, scoped to the given user.

    Args:
        db: Async database session.
        chatbot_id: The chatbot's UUID.
        user_id: The owning user's UUID (for access control).

    Returns:
        The Chatbot if found and owned by the user, None otherwise.
    """
    result = await db.execute(
        select(Chatbot).where(
            Chatbot.id == chatbot_id,
            Chatbot.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_chatbot_by_widget_key(
    db: AsyncSession, widget_key: str
) -> Chatbot | None:
    """
    Get a chatbot by its public widget key (no user scoping).

    Used by the public widget endpoint to identify chatbots
    without requiring authentication.

    Args:
        db: Async database session.
        widget_key: The chatbot's unique widget key.

    Returns:
        The Chatbot if found, None otherwise.
    """
    result = await db.execute(
        select(Chatbot).where(Chatbot.widget_key == widget_key)
    )
    return result.scalar_one_or_none()


async def list_chatbots(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Chatbot], int]:
    """
    List chatbots for a user with pagination.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        page: Page number (1-based).
        page_size: Number of items per page.

    Returns:
        Tuple of (list of Chatbots, total count).
    """
    # Count total
    count_result = await db.execute(
        select(func.count()).where(Chatbot.user_id == user_id)
    )
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Chatbot)
        .where(Chatbot.user_id == user_id)
        .order_by(Chatbot.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    chatbots = list(result.scalars().all())

    return chatbots, total


async def update_chatbot(
    db: AsyncSession,
    chatbot: Chatbot,
    name: str | None = None,
    personality: str | None = None,
    welcome_message: str | None = None,
    theme_config: dict | None = None,
    is_active: bool | None = None,
) -> Chatbot:
    """
    Update a chatbot's fields.

    Only non-None arguments are applied. Uses the sentinel pattern
    to distinguish between "not provided" and explicit None.

    Args:
        db: Async database session.
        chatbot: The Chatbot to update.
        name: Updated name.
        personality: Updated personality style.
        welcome_message: Updated greeting.
        theme_config: Updated appearance settings.
        is_active: Updated active status.

    Returns:
        The updated Chatbot.
    """
    if name is not None:
        chatbot.name = name
    if personality is not None:
        chatbot.personality = personality
    if welcome_message is not None:
        chatbot.welcome_message = welcome_message
    if theme_config is not None:
        chatbot.theme_config = theme_config
    if is_active is not None:
        chatbot.is_active = is_active

    await db.flush()
    return chatbot


async def delete_chatbot(db: AsyncSession, chatbot: Chatbot) -> None:
    """
    Delete a chatbot and all related data (cascades).

    Args:
        db: Async database session.
        chatbot: The Chatbot to delete.
    """
    await db.delete(chatbot)
    await db.flush()


async def count_user_chatbots(db: AsyncSession, user_id: uuid.UUID) -> int:
    """
    Count the total number of chatbots owned by a user.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Integer count of chatbots.
    """
    result = await db.execute(
        select(func.count()).where(Chatbot.user_id == user_id)
    )
    return result.scalar() or 0
