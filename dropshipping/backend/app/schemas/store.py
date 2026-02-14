"""Pydantic schemas for store endpoints.

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/*`` routes.

**For Developers:**
    ``CreateStoreRequest`` and ``UpdateStoreRequest`` are input schemas.
    ``StoreResponse`` uses ``from_attributes`` to serialize ORM instances.

**For QA Engineers:**
    - ``CreateStoreRequest.name`` is required, 1–255 characters.
    - ``UpdateStoreRequest`` is fully optional (partial updates via PATCH).
    - ``StoreResponse`` includes the auto-generated slug and timestamps.

**For End Users:**
    When creating a store, provide a name and niche. A unique URL slug
    will be generated automatically from the store name.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.store import StoreStatus


class CreateStoreRequest(BaseModel):
    """Schema for creating a new store.

    Attributes:
        name: Display name of the store (1–255 characters).
        niche: Product niche or category (1–100 characters).
        description: Optional longer description.
    """

    name: str = Field(..., min_length=1, max_length=255, description="Store display name")
    niche: str = Field(..., min_length=1, max_length=100, description="Product niche")
    description: str | None = Field(None, description="Optional store description")


class UpdateStoreRequest(BaseModel):
    """Schema for updating an existing store (partial update).

    All fields are optional — only provided fields will be updated.

    Attributes:
        name: New display name (1–255 characters).
        niche: New niche (1–100 characters).
        description: New description.
        status: New store status (active or paused; deletion uses DELETE endpoint).
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    niche: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    status: StoreStatus | None = None


class StoreResponse(BaseModel):
    """Schema for returning store data in API responses.

    Attributes:
        id: The store's unique identifier.
        user_id: The owner's user ID.
        name: Display name of the store.
        slug: URL-friendly unique slug.
        niche: Product niche or category.
        description: Store description (may be null).
        status: Current store status.
        created_at: When the store was created.
        updated_at: When the store was last modified.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    slug: str
    niche: str
    description: str | None
    status: StoreStatus
    created_at: datetime
    updated_at: datetime
