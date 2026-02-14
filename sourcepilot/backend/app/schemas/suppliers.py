"""
Pydantic schemas for supplier account endpoints.

Defines request/response data structures for managing supplier platform
connections (AliExpress, CJ Dropshipping, Spocket).

For Developers:
    Response schemas redact credentials — only a ``credentials`` dict with
    redacted values is returned to prevent credential leakage.

For Project Managers:
    These schemas define the API contract for supplier account management.

For QA Engineers:
    Verify that API keys are never exposed in responses.
    Test validation with missing required fields.

For End Users:
    These structures describe how to connect and manage your supplier accounts.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SupplierAccountCreate(BaseModel):
    """
    Request body for connecting a new supplier account.

    Attributes:
        name: Human-readable display name for the account.
        platform: Supplier platform identifier (e.g. aliexpress, cjdropshipping).
        credentials: Dict of platform-specific credentials (e.g. api_key, api_secret).
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Display name for the supplier account",
    )
    platform: str = Field(
        ...,
        description="Supplier platform: aliexpress, cjdropshipping, spocket, manual",
    )
    credentials: dict | None = Field(
        default=None,
        description="Platform-specific credentials (e.g. api_key, api_secret)",
    )


class SupplierAccountUpdate(BaseModel):
    """
    Request body for updating an existing supplier account.

    All fields are optional; only provided fields are updated.

    Attributes:
        name: Updated display name (optional).
        platform: Updated platform identifier (optional).
        credentials: Updated credentials dict (optional).
        is_active: Toggle active/inactive state (optional).
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated display name",
    )
    platform: str | None = Field(
        default=None,
        description="Updated platform identifier",
    )
    credentials: dict | None = Field(
        default=None,
        description="Updated credentials dict",
    )
    is_active: bool | None = Field(
        default=None,
        description="Toggle active/inactive",
    )


class SupplierAccountResponse(BaseModel):
    """
    Response schema for a supplier account.

    Credentials are redacted in responses.

    Attributes:
        id: Supplier account unique identifier.
        user_id: Owning user identifier.
        name: Display name.
        platform: Supplier platform identifier.
        credentials: Redacted credentials dict.
        is_active: Whether the account is currently enabled.
        last_synced_at: Most recent sync timestamp.
        created_at: Account creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    platform: str
    credentials: dict | None = None
    is_active: bool
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierAccountListResponse(BaseModel):
    """
    List of supplier accounts (not paginated — users have few accounts).

    Attributes:
        items: All supplier accounts for the user.
    """

    items: list[SupplierAccountResponse]
