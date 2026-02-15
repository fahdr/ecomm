"""Pydantic schemas for inventory management endpoints.

These schemas validate requests and shape responses for the
``/api/v1/stores/{store_id}/warehouses/*`` and
``/api/v1/stores/{store_id}/inventory/*`` routes.

**For Developers:**
    All response schemas use ``from_attributes`` for ORM serialization.
    The ``available_quantity`` is computed from ``quantity - reserved_quantity``.

**For QA Engineers:**
    - Warehouse name is required, 1-255 characters.
    - Country code must be exactly 2 characters (ISO 3166-1 alpha-2).
    - Quantity values must be non-negative.
    - AdjustmentReason must be one of the defined enum values.

**For Project Managers:**
    These schemas define the data contracts for the inventory management
    API, enabling warehouse CRUD, stock level tracking, and adjustment
    audit trails.

**For End Users:**
    Manage your warehouse locations, track stock levels across warehouses,
    and view the history of every inventory change.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.inventory import AdjustmentReason


# ---------------------------------------------------------------------------
# Warehouse schemas
# ---------------------------------------------------------------------------


class CreateWarehouseRequest(BaseModel):
    """Schema for creating a new warehouse.

    Attributes:
        name: Warehouse display name (1-255 characters).
        address: Street address (optional).
        city: City name (optional).
        state: State or province (optional).
        country: ISO 3166-1 alpha-2 country code (exactly 2 chars).
        zip_code: Postal/ZIP code (optional).
        is_default: Whether to make this the default warehouse.
    """

    name: str = Field(..., min_length=1, max_length=255)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str = Field(default="US", min_length=2, max_length=2)
    zip_code: str | None = None
    is_default: bool = False


class UpdateWarehouseRequest(BaseModel):
    """Schema for partially updating a warehouse.

    Attributes:
        name: New name (1-255 characters).
        address: New street address.
        city: New city.
        state: New state.
        country: New country code (2 chars).
        zip_code: New postal code.
        is_default: Whether to set as default.
        is_active: Whether the warehouse is operational.
    """

    name: str | None = Field(None, min_length=1, max_length=255)
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = Field(None, min_length=2, max_length=2)
    zip_code: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class WarehouseResponse(BaseModel):
    """Schema for returning warehouse data in API responses.

    Attributes:
        id: Warehouse unique identifier.
        store_id: The store this warehouse belongs to.
        name: Warehouse display name.
        address: Street address.
        city: City name.
        state: State/province.
        country: ISO country code.
        zip_code: Postal code.
        is_default: Whether this is the default warehouse.
        is_active: Whether the warehouse is operational.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    address: str | None
    city: str | None
    state: str | None
    country: str
    zip_code: str | None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Inventory Level schemas
# ---------------------------------------------------------------------------


class SetInventoryRequest(BaseModel):
    """Schema for setting inventory level for a variant at a warehouse.

    Attributes:
        variant_id: The product variant UUID.
        warehouse_id: The warehouse UUID.
        quantity: Total quantity to set (non-negative).
        reorder_point: Stock level that triggers reorder alert (non-negative).
        reorder_quantity: Suggested reorder quantity (non-negative).
    """

    variant_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int = Field(default=0, ge=0)
    reorder_point: int = Field(default=0, ge=0)
    reorder_quantity: int = Field(default=0, ge=0)


class AdjustInventoryRequest(BaseModel):
    """Schema for making an inventory adjustment (delta change).

    Attributes:
        quantity_change: Signed quantity delta (positive = add, negative = remove).
        reason: Categorized reason for the adjustment.
        reference_id: Optional UUID of related entity (order, transfer, etc.).
        notes: Optional human-readable notes.
    """

    quantity_change: int
    reason: AdjustmentReason
    reference_id: uuid.UUID | None = None
    notes: str | None = None


class InventoryLevelResponse(BaseModel):
    """Schema for returning inventory level data.

    Attributes:
        id: Inventory level unique identifier.
        variant_id: The product variant.
        warehouse_id: The warehouse.
        quantity: Total units in stock.
        reserved_quantity: Units reserved for orders.
        available_quantity: Computed available stock.
        reorder_point: Reorder alert threshold.
        reorder_quantity: Suggested reorder amount.
        is_low_stock: Whether stock is at or below reorder point.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    variant_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: int
    reserved_quantity: int
    available_quantity: int
    reorder_point: int
    reorder_quantity: int
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime


class InventoryAdjustmentResponse(BaseModel):
    """Schema for returning inventory adjustment records.

    Attributes:
        id: Adjustment unique identifier.
        inventory_level_id: The inventory level this adjustment applies to.
        quantity_change: Signed delta applied.
        reason: Categorized reason.
        reference_id: Related entity UUID (if any).
        notes: Human-readable notes.
        created_at: When the adjustment was made.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    inventory_level_id: uuid.UUID
    quantity_change: int
    reason: str
    reference_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Inventory Summary
# ---------------------------------------------------------------------------


class InventorySummaryResponse(BaseModel):
    """Aggregated inventory summary for a store.

    Attributes:
        total_warehouses: Number of active warehouses.
        total_variants_tracked: Number of variants with inventory tracking.
        total_in_stock: Total units across all warehouses.
        total_reserved: Total reserved units.
        low_stock_count: Number of inventory levels at or below reorder point.
    """

    total_warehouses: int
    total_variants_tracked: int
    total_in_stock: int
    total_reserved: int
    low_stock_count: int
