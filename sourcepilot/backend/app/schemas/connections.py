"""
Pydantic schemas for store connection endpoints.

Defines request/response data structures for connecting, listing,
updating, and disconnecting dropshipping stores.

For Developers:
    StoreConnectionCreate requires store_name, platform, and store_url.
    The api_key is optional (some platforms use OAuth instead).

For Project Managers:
    These schemas define the API contract for store connection management.
    Users must connect at least one store before importing products.

For QA Engineers:
    Test CRUD operations and the is_default constraint. Verify that
    responses match the schema shapes.

For End Users:
    Connect your dropshipping stores to enable product imports.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StoreConnectionCreate(BaseModel):
    """
    Request body for connecting a new store.

    Attributes:
        store_name: Human-readable name of the store.
        platform: E-commerce platform type (shopify, woocommerce, etc.).
        store_url: URL of the store.
        api_key: Store API key for authentication (optional).
    """

    store_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for the store",
    )
    platform: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="E-commerce platform type (shopify, woocommerce, etc.)",
    )
    store_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="URL of the store",
    )
    api_key: str | None = Field(
        default=None,
        max_length=500,
        description="Store API key for authentication (optional)",
    )


class StoreConnectionUpdate(BaseModel):
    """
    Request body for updating an existing store connection.

    All fields are optional; only provided fields are updated.

    Attributes:
        store_name: Updated display name (optional).
        store_url: Updated store URL (optional).
        api_key: Updated API key (optional).
        is_default: Set as default import target (optional).
    """

    store_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated display name",
    )
    store_url: str | None = Field(
        default=None,
        max_length=500,
        description="Updated store URL",
    )
    api_key: str | None = Field(
        default=None,
        max_length=500,
        description="Updated API key",
    )
    is_default: bool | None = Field(
        default=None,
        description="Set as default import target",
    )


class StoreConnectionResponse(BaseModel):
    """
    Response schema for a store connection.

    Attributes:
        id: Connection unique identifier.
        user_id: Owning user identifier.
        store_name: Display name of the store.
        platform: E-commerce platform type.
        store_url: URL of the store.
        is_default: Whether this is the default import target.
        created_at: Connection creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    store_name: str
    platform: str
    store_url: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StoreConnectionListResponse(BaseModel):
    """
    List of store connections (not paginated — users have few connections).

    Attributes:
        items: All store connections for the user.
    """

    items: list[StoreConnectionResponse]
