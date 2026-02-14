"""
Customer override endpoints for the LLM Gateway.

Admin CRUD for per-customer provider/model overrides.

For Developers:
    Overrides let the admin assign specific customers to specific providers.
    A service_name of None means the override applies to all services.

For QA Engineers:
    Test CRUD operations and verify that overrides change routing behavior.

For Project Managers:
    Overrides enable premium customers to use better AI models
    while keeping costs low for free-tier users.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.generate import _verify_service_key
from app.database import get_db
from app.models.customer_override import CustomerOverride

router = APIRouter()


class OverrideCreate(BaseModel):
    """Schema for creating a customer override."""

    user_id: str
    service_name: str | None = None
    provider_name: str
    model_name: str


class OverrideResponse(BaseModel):
    """Response schema for a customer override."""

    id: uuid.UUID
    user_id: str
    service_name: str | None
    provider_name: str
    model_name: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[OverrideResponse])
async def list_overrides(
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """
    List customer overrides, optionally filtered by user_id.

    Args:
        user_id: Optional filter by user ID.

    Returns:
        List of override records.
    """
    stmt = select(CustomerOverride)
    if user_id:
        stmt = stmt.where(CustomerOverride.user_id == user_id)
    result = await db.execute(stmt)
    overrides = result.scalars().all()
    return [
        OverrideResponse(
            id=o.id,
            user_id=o.user_id,
            service_name=o.service_name,
            provider_name=o.provider_name,
            model_name=o.model_name,
            created_at=o.created_at.isoformat(),
            updated_at=o.updated_at.isoformat(),
        )
        for o in overrides
    ]


@router.post("", response_model=OverrideResponse, status_code=201)
async def create_override(
    body: OverrideCreate,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """Create a new customer override."""
    override = CustomerOverride(
        user_id=body.user_id,
        service_name=body.service_name,
        provider_name=body.provider_name,
        model_name=body.model_name,
    )
    db.add(override)
    await db.flush()
    return OverrideResponse(
        id=override.id,
        user_id=override.user_id,
        service_name=override.service_name,
        provider_name=override.provider_name,
        model_name=override.model_name,
        created_at=override.created_at.isoformat(),
        updated_at=override.updated_at.isoformat(),
    )


@router.delete("/{override_id}", status_code=204)
async def delete_override(
    override_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(_verify_service_key),
):
    """Delete a customer override."""
    override = await db.get(CustomerOverride, override_id)
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    await db.delete(override)
    await db.flush()
