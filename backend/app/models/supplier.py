"""Supplier and ProductSupplier database models.

Defines the ``suppliers`` and ``product_suppliers`` tables for managing
dropshipping supplier relationships. Each supplier is scoped to a single
store and can be linked to multiple products via the junction table.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``product_suppliers`` junction table connects
    products to their suppliers and stores per-supplier metadata such as
    cost, SKU, and source URL. The ``is_primary`` flag indicates which
    supplier is the default fulfillment source for a product.

**For QA Engineers:**
    - ``SupplierStatus`` restricts status to ``active``, ``inactive``, or
      ``blacklisted``.
    - ``reliability_score`` is a decimal from 0.00 to 9.99 representing
      how dependable the supplier is (higher is better).
    - ``avg_shipping_days`` is the typical number of days for the supplier
      to deliver to the end customer.
    - The ``product_suppliers`` junction table enforces uniqueness on
      (``product_id``, ``supplier_id``) to prevent duplicate links.

**For End Users:**
    Suppliers are the companies that ship products directly to your
    customers. You can track their contact information, reliability,
    shipping times, and per-product costs to make informed sourcing
    decisions and maximize your profit margins.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
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


class SupplierStatus(str, enum.Enum):
    """Lifecycle states for a supplier.

    Attributes:
        active: Supplier is available for fulfillment.
        inactive: Supplier is temporarily unavailable.
        blacklisted: Supplier has been permanently blocked due to poor
            performance or policy violations.
    """

    active = "active"
    inactive = "inactive"
    blacklisted = "blacklisted"


class Supplier(Base):
    """SQLAlchemy model representing a dropshipping supplier.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the supplier to its store.
        name: Display name of the supplier (e.g. company name).
        website: Optional URL for the supplier's website or platform.
        contact_email: Optional email address for supplier communications.
        contact_phone: Optional phone number for the supplier.
        notes: Optional free-text notes about the supplier.
        status: Current supplier status (active, inactive, blacklisted).
        avg_shipping_days: Average number of days the supplier takes to
            deliver an order to the end customer.
        reliability_score: A score from 0.00 to 9.99 indicating how
            dependable this supplier is based on historical performance.
        created_at: Timestamp when the supplier was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store this supplier belongs to.
        product_links: One-to-many relationship to ProductSupplier records.
    """

    __tablename__ = "suppliers"

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
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SupplierStatus] = mapped_column(
        Enum(SupplierStatus), default=SupplierStatus.active, nullable=False
    )
    avg_shipping_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reliability_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="suppliers", lazy="selectin")
    product_links = relationship(
        "ProductSupplier",
        back_populates="supplier",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductSupplier(Base):
    """Junction table linking products to suppliers with sourcing metadata.

    Captures supplier-specific information for each product such as the
    supplier's cost, SKU, and source URL. The ``is_primary`` flag marks
    which supplier is used by default for order fulfillment.

    Attributes:
        id: Unique identifier (UUID v4).
        product_id: Foreign key to the product.
        supplier_id: Foreign key to the supplier.
        supplier_url: Optional URL to the product on the supplier's platform.
        supplier_sku: Optional supplier-side SKU or item identifier.
        supplier_cost: The cost charged by this supplier for the product.
        is_primary: Whether this is the default supplier for the product.
        created_at: Timestamp when the link was created.
        supplier: Relationship back to the Supplier.
        product: Relationship back to the Product.
    """

    __tablename__ = "product_suppliers"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "supplier_id", name="uq_product_suppliers_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    supplier_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    supplier = relationship("Supplier", back_populates="product_links")
    product = relationship("Product", backref="supplier_links", lazy="selectin")
