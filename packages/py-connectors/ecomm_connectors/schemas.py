"""
Pydantic schemas for store connections.

For Developers:
    Use these DTOs in API endpoints that manage store connections.
    They are platform-agnostic — the ``platform`` field determines
    which connector handles the connection.

For QA Engineers:
    Validation rules are enforced at the schema level (required fields,
    URL format, enum values).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ecomm_connectors.base import PlatformType


class ConnectStoreRequest(BaseModel):
    """
    Request body for connecting a new store.

    For End Users:
        Provide your store URL and API credentials to link your ecommerce
        platform with the service.

    Attributes:
        platform: The ecommerce platform type.
        store_url: Your store's URL.
        credentials: Platform-specific credentials (API key, secret, etc.).
        store_name: Optional display name for the connection.
    """

    platform: PlatformType
    store_url: str
    credentials: dict[str, str]
    store_name: str = ""


class StoreConnectionResponse(BaseModel):
    """
    Response representing a connected store.

    For End Users:
        Shows the status and details of your connected store.

    Attributes:
        id: Connection ID.
        platform: Platform type.
        store_url: Connected store URL.
        store_name: Display name.
        is_active: Whether the connection is currently active.
        last_synced_at: When data was last synchronized.
        created_at: When the connection was established.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: PlatformType
    store_url: str
    store_name: str
    is_active: bool
    last_synced_at: datetime | None = None
    created_at: datetime


class TestConnectionResponse(BaseModel):
    """
    Response from testing a store connection.

    For End Users:
        Shows whether your store connection is working properly.

    Attributes:
        success: Whether the test passed.
        platform: Platform type.
        store_name: Store name returned from the platform.
        message: Human-readable status message.
    """

    success: bool
    platform: str
    store_name: str = ""
    message: str = ""


class SyncStatusResponse(BaseModel):
    """
    Response showing sync progress.

    For End Users:
        Shows the current status of data synchronization with your store.

    Attributes:
        connection_id: The connection being synced.
        products_synced: Number of products imported.
        orders_synced: Number of orders imported.
        customers_synced: Number of customers imported.
        last_synced_at: Timestamp of completion.
        status: Current sync status (running, completed, failed).
    """

    connection_id: str
    products_synced: int = 0
    orders_synced: int = 0
    customers_synced: int = 0
    last_synced_at: datetime | None = None
    status: str = "pending"
