"""
Personality configuration API routes.

Provides endpoints for creating, retrieving, and updating the chat
personality configuration. Each user has at most one personality config
that controls how the AI assistant responds.

For Developers:
    The POST endpoint is an upsert: it creates or updates the
    personality config. GET returns the current config or defaults.

For QA Engineers:
    Test create/update/get operations. Verify that defaults are
    returned when no config exists. Test field validation.

For Project Managers:
    These endpoints power the Settings page in the dashboard where
    users customize their AI assistant's behavior.

For End Users:
    Customize your AI assistant's personality, greeting, name, and
    language through the Settings page.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import PersonalityCreate, PersonalityResponse
from app.services.personality_service import (
    create_or_update_personality,
    get_personality,
)

router = APIRouter(prefix="/personality", tags=["personality"])


@router.get("", response_model=PersonalityResponse | None)
async def get_personality_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current user's personality configuration.

    Returns the personality config if one exists, or None with
    default values implied by the frontend.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        PersonalityResponse or None if no config exists.
    """
    personality = await get_personality(db, current_user.id)
    if not personality:
        return None
    return personality


@router.post("", response_model=PersonalityResponse)
async def set_personality_config(
    body: PersonalityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create or update the personality configuration.

    This is an upsert operation: if a config exists, it is updated;
    otherwise a new one is created.

    Args:
        body: Personality configuration data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created or updated personality configuration.
    """
    personality = await create_or_update_personality(
        db=db,
        user_id=current_user.id,
        greeting_message=body.greeting_message,
        tone=body.tone,
        bot_name=body.bot_name,
        escalation_rules=body.escalation_rules,
        response_language=body.response_language,
        custom_instructions=body.custom_instructions,
    )
    return personality
