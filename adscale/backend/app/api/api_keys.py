"""
API Key management endpoints.

Allows users to create, list, and revoke API keys for programmatic
access to the service.

For Developers:
    API keys are hashed with SHA-256 before storage. The raw key is only
    returned once at creation time. The key_prefix (first 12 chars) is
    stored for identification.

For QA Engineers:
    Test: create key (verify raw key returned), list keys (no raw keys),
    revoke key (verify it stops working), key auth via X-API-Key header.

For End Users:
    Generate API keys in Settings > API Keys. Use the X-API-Key header
    to authenticate your integrations.
"""

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User


class CreateApiKeyRequest(BaseModel):
    """
    Request to create a new API key.

    Attributes:
        name: Human-readable label for the key.
        scopes: Permission scopes (default: ['read']).
    """

    name: str
    scopes: list[str] = ["read"]


class ApiKeyResponse(BaseModel):
    """
    API key response (for listing — no raw key).

    Attributes:
        id: Key identifier.
        name: Human-readable label.
        key_prefix: First 12 characters of the key.
        scopes: Permission scopes.
        is_active: Whether the key is active.
        last_used_at: Last time the key was used.
        created_at: Key creation timestamp.
    """

    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    """
    Response after creating an API key (includes raw key — shown once).

    Attributes:
        id: Key identifier.
        name: Human-readable label.
        key: The raw API key (ONLY shown once at creation).
        key_prefix: First 12 characters of the key.
        scopes: Permission scopes.
    """

    id: uuid.UUID
    name: str
    key: str
    key_prefix: str
    scopes: list[str]


router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key.

    The raw key is returned ONLY in this response. Store it securely.

    Args:
        request: Key name and scopes.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        ApiKeyCreatedResponse with the raw key (shown only once).
    """
    prefix = settings.service_name[:2]
    raw_key = f"{prefix}_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        scopes=request.scopes,
    )
    db.add(api_key)
    await db.flush()

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=raw_key[:12],
        scopes=api_key.scopes,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys for the authenticated user.

    Returns key metadata only — raw keys are never exposed after creation.

    Args:
        current_user: The authenticated user.
        db: Database session.

    Returns:
        List of ApiKeyResponse without raw keys.
    """
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            created_at=k.created_at.isoformat(),
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke (deactivate) an API key.

    The key remains in the database but is marked inactive.

    Args:
        key_id: The UUID of the key to revoke.
        current_user: The authenticated user.
        db: Database session.

    Raises:
        HTTPException 404: If key not found or doesn't belong to user.
    """
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    api_key.is_active = False
    await db.flush()
