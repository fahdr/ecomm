"""
Provider management endpoints for the LLM Gateway.

Admin CRUD for LLM provider configurations (API keys, models, rate limits).
These endpoints are called by the Super Admin Dashboard.

For Developers:
    All endpoints require the service key header for authentication.
    Provider names must be unique. The ``models`` field is a JSON list
    of available model identifiers.

For QA Engineers:
    Test CRUD operations: create, list, get, update, delete.
    Test the /test endpoint to verify provider connectivity.

For Project Managers:
    These endpoints let the admin manage AI provider configurations
    without redeploying the gateway.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.generate import _verify_service_key
from app.database import get_db
from app.models.provider_config import ProviderConfig
from app.services.router_service import PROVIDER_MAP, _create_provider

router = APIRouter()


class ProviderCreate(BaseModel):
    """
    Schema for creating a new provider configuration.

    Attributes:
        name: Unique provider identifier (claude, openai, gemini, etc.).
        display_name: Human-readable label.
        api_key: The provider's API key (stored as-is for now).
        base_url: Optional custom endpoint URL.
        models: List of available model identifiers.
        is_enabled: Whether this provider accepts requests.
        rate_limit_rpm: Requests per minute limit.
        rate_limit_tpm: Tokens per minute limit.
        priority: Routing priority (lower = preferred).
    """

    name: str
    display_name: str
    api_key: str
    base_url: str | None = None
    models: list[str] = Field(default_factory=list)
    is_enabled: bool = True
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000
    priority: int = 10


class ProviderUpdate(BaseModel):
    """Schema for updating a provider configuration."""

    display_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    models: list[str] | None = None
    is_enabled: bool | None = None
    rate_limit_rpm: int | None = None
    rate_limit_tpm: int | None = None
    priority: int | None = None


class ProviderResponse(BaseModel):
    """Response schema for a provider configuration."""

    id: uuid.UUID
    name: str
    display_name: str
    base_url: str | None
    models: list
    is_enabled: bool
    rate_limit_rpm: int
    rate_limit_tpm: int
    priority: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProviderResponse])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    List all configured LLM providers.

    Returns:
        List of provider configurations ordered by priority.
    """
    result = await db.execute(
        select(ProviderConfig).order_by(ProviderConfig.priority)
    )
    providers = result.scalars().all()
    return [
        ProviderResponse(
            id=p.id,
            name=p.name,
            display_name=p.display_name,
            base_url=p.base_url,
            models=p.models if isinstance(p.models, list) else [],
            is_enabled=p.is_enabled,
            rate_limit_rpm=p.rate_limit_rpm,
            rate_limit_tpm=p.rate_limit_tpm,
            priority=p.priority,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in providers
    ]


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(
    body: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Create a new provider configuration.

    Args:
        body: Provider creation data.

    Returns:
        The created provider configuration.
    """
    existing = await db.execute(
        select(ProviderConfig).where(ProviderConfig.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Provider '{body.name}' already exists")

    config = ProviderConfig(
        name=body.name,
        display_name=body.display_name,
        api_key_encrypted=body.api_key,
        base_url=body.base_url,
        models=body.models,
        is_enabled=body.is_enabled,
        rate_limit_rpm=body.rate_limit_rpm,
        rate_limit_tpm=body.rate_limit_tpm,
        priority=body.priority,
    )
    db.add(config)
    await db.flush()
    return ProviderResponse(
        id=config.id,
        name=config.name,
        display_name=config.display_name,
        base_url=config.base_url,
        models=config.models if isinstance(config.models, list) else [],
        is_enabled=config.is_enabled,
        rate_limit_rpm=config.rate_limit_rpm,
        rate_limit_tpm=config.rate_limit_tpm,
        priority=config.priority,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """Fetch a single provider configuration by ID."""
    config = await db.get(ProviderConfig, provider_id)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderResponse(
        id=config.id,
        name=config.name,
        display_name=config.display_name,
        base_url=config.base_url,
        models=config.models if isinstance(config.models, list) else [],
        is_enabled=config.is_enabled,
        rate_limit_rpm=config.rate_limit_rpm,
        rate_limit_tpm=config.rate_limit_tpm,
        priority=config.priority,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: uuid.UUID,
    body: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """Update a provider configuration."""
    config = await db.get(ProviderConfig, provider_id)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")

    if body.display_name is not None:
        config.display_name = body.display_name
    if body.api_key is not None:
        config.api_key_encrypted = body.api_key
    if body.base_url is not None:
        config.base_url = body.base_url
    if body.models is not None:
        config.models = body.models
    if body.is_enabled is not None:
        config.is_enabled = body.is_enabled
    if body.rate_limit_rpm is not None:
        config.rate_limit_rpm = body.rate_limit_rpm
    if body.rate_limit_tpm is not None:
        config.rate_limit_tpm = body.rate_limit_tpm
    if body.priority is not None:
        config.priority = body.priority

    await db.flush()
    await db.refresh(config)
    return ProviderResponse(
        id=config.id,
        name=config.name,
        display_name=config.display_name,
        base_url=config.base_url,
        models=config.models if isinstance(config.models, list) else [],
        is_enabled=config.is_enabled,
        rate_limit_rpm=config.rate_limit_rpm,
        rate_limit_tpm=config.rate_limit_tpm,
        priority=config.priority,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """Delete a provider configuration."""
    config = await db.get(ProviderConfig, provider_id)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(config)
    await db.flush()


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    Test connectivity to a provider.

    Makes a minimal API call to verify the key and endpoint work.

    Returns:
        JSON with ``success`` boolean and optional ``error`` message.
    """
    config = await db.get(ProviderConfig, provider_id)
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")

    try:
        provider = _create_provider(config)
        success = await provider.test_connection()
        return {"success": success, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}
