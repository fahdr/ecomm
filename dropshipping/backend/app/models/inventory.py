"""Inventory management models for ecommerce stores.

Defines ``warehouses``, ``inventory_levels``, and ``inventory_adjustments``
tables for tracking stock across multiple warehouse locations.

**For Developers:**
    Warehouses are store-scoped — each ecommerce/hybrid store can have
    multiple warehouses. InventoryLevel tracks quantity per variant per
    warehouse (unique constraint enforced). InventoryAdjustment provides
    an immutable audit trail of every stock change.

**For QA Engineers:**
    - One default warehouse is auto-created for ecommerce stores.
    - ``InventoryLevel`` has a unique constraint on (variant_id, warehouse_id).
    - ``available_quantity`` = quantity - reserved_quantity.
    - Adjustments record the reason and reference (order_id, manual, etc).
    - ``reserved_quantity`` is incremented on order creation, decremented
      on fulfillment or cancellation.

**For Project Managers:**
    Inventory management is the core differentiator between dropshipping
    and ecommerce modes. These models power real-time stock tracking,
    low-stock alerts, and multi-warehouse fulfillment.

**For End Users:**
    Track your product stock across multiple warehouses. Get notified
    when inventory is low and manage reorder points automatically.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Warehouse(Base):
    """A physical warehouse or fulfillment location.

    Each ecommerce store can have multiple warehouses. One warehouse
    is marked as default for new inventory entries.

    Attributes:
        id: Unique identifier (UUID v4).
        store_id: Foreign key to the store this warehouse belongs to.
        name: Human-readable warehouse name (e.g., "Main Warehouse").
        address: Street address of the warehouse.
        city: City where the warehouse is located.
        state: State or province (optional).
        country: ISO 3166-1 alpha-2 country code (e.g., "US").
        zip_code: Postal/ZIP code (optional).
        is_default: Whether this is the default warehouse for the store.
        is_active: Whether the warehouse is currently operational.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        store: Related Store record.
        inventory_levels: Stock levels at this warehouse.
    """

    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )

    store = relationship("Store", backref="warehouses", lazy="selectin")
    inventory_levels = relationship(
        "InventoryLevel",
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InventoryLevel(Base):
    """Stock level for a product variant at a specific warehouse.

    Tracks current quantity, reserved quantity (for pending orders),
    and reorder thresholds for automated restocking alerts.

    Attributes:
        id: Unique identifier (UUID v4).
        variant_id: Foreign key to the product variant.
        warehouse_id: Foreign key to the warehouse.
        quantity: Total units physically in stock.
        reserved_quantity: Units reserved for pending/unfulfilled orders.
        reorder_point: Threshold below which a reorder alert is triggered.
        reorder_quantity: Suggested quantity to reorder when threshold is hit.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        variant: Related ProductVariant record.
        warehouse: Related Warehouse record.
        adjustments: Audit trail of stock changes.
    """

    __tablename__ = "inventory_levels"
    __table_args__ = (
        UniqueConstraint(
            "variant_id", "warehouse_id",
            name="uq_inventory_variant_warehouse"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )

    variant = relationship("ProductVariant", back_populates="inventory_levels")
    warehouse = relationship("Warehouse", back_populates="inventory_levels")
    adjustments = relationship(
        "InventoryAdjustment",
        back_populates="inventory_level",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def available_quantity(self) -> int:
        """Calculate available stock (total minus reserved).

        Returns:
            Number of units available for new orders.
        """
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self) -> bool:
        """Check if available stock is at or below the reorder point.

        Returns:
            True if stock is low and reorder should be triggered.
        """
        return self.reorder_point > 0 and self.available_quantity <= self.reorder_point


class AdjustmentReason(str, enum.Enum):
    """Reasons for inventory adjustments.

    Attributes:
        received: Stock received from supplier or manufacturer.
        sold: Stock decremented due to a completed sale.
        returned: Stock returned by a customer.
        damaged: Stock removed due to damage or defect.
        correction: Manual inventory correction (count discrepancy).
        reserved: Stock reserved for a pending order.
        unreserved: Reserved stock released (order cancelled).
        transfer: Stock transferred between warehouses.
    """

    received = "received"
    sold = "sold"
    returned = "returned"
    damaged = "damaged"
    correction = "correction"
    reserved = "reserved"
    unreserved = "unreserved"
    transfer = "transfer"


class InventoryAdjustment(Base):
    """Immutable audit trail record for inventory changes.

    Every change to an InventoryLevel's quantity or reserved_quantity
    is recorded as an adjustment with the reason, delta, and optional
    reference to the triggering entity (order, transfer, etc.).

    Attributes:
        id: Unique identifier (UUID v4).
        inventory_level_id: Foreign key to the inventory level.
        quantity_change: Signed integer delta (+received, -sold, etc.).
        reason: Categorized reason for the adjustment.
        reference_id: Optional UUID of the related order, transfer, etc.
        notes: Optional human-readable notes about this adjustment.
        created_at: Adjustment timestamp (immutable).
        inventory_level: Related InventoryLevel record.
    """

    __tablename__ = "inventory_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inventory_level_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_levels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[AdjustmentReason] = mapped_column(
        String(30), nullable=False
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    inventory_level = relationship(
        "InventoryLevel", back_populates="adjustments"
    )
