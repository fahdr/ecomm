"""
API Key management router factory.

Creates a FastAPI router with endpoints for creating, listing, and
revoking API keys.

For Developers:
    Use `create_api_keys_router(get_db, get_current_user)`.
"""

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ecomm_core.models.api_key import ApiKey
from ecomm_core.models.user import User


class CreateApiKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str
    scopes: list[str] = ["read"]


class ApiKeyResponse(BaseModel):
    """API key response (for listing -- no raw key)."""
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    last_used_at: str | None
    created_at: str
    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    """Response after creating an API key (includes raw key -- shown once)."""
    id: uuid.UUID
    name: str
    key: str
    key_prefix: str
    scopes: list[str]


def create_api_keys_router(get_db, get_current_user) -> APIRouter:
    """
    Factory to create the API keys router.

    Args:
        get_db: FastAPI dependency for database session.
        get_current_user: FastAPI dependency for JWT auth.

    Returns:
        APIRouter with API key CRUD endpoints.
    """
    router = APIRouter(prefix="/api-keys", tags=["api-keys"])

    @router.post("", response_model=ApiKeyCreatedResponse, status_code=201)
    async def create_api_key(
        request: CreateApiKeyRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        """Create a new API key. The raw key is returned ONLY in this response."""
        from app.config import settings

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
        """List all API keys for the authenticated user (no raw keys)."""
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
        """Revoke (deactivate) an API key."""
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

    return router
