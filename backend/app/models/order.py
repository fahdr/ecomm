"""Order and OrderItem database models.

Defines the ``orders`` and ``order_items`` tables for tracking customer
purchases. Each order belongs to a store and contains one or more items
linked to products and optional variants.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` foreign key scopes orders to
    a store. ``stripe_session_id`` is used to correlate with Stripe Checkout.

**For QA Engineers:**
    - ``OrderStatus`` enum restricts status to ``pending``, ``paid``,
      ``shipped``, ``delivered``, or ``cancelled``.
    - Orders start as ``pending`` and transition to ``paid`` when the
      Stripe webhook confirms payment.
    - ``customer_email`` is collected during checkout for order confirmation.
    - ``OrderItem.unit_price`` captures the price at the time of purchase
      (not the current product price).

**For End Users:**
    Orders are created when customers complete checkout. Store owners can
    view and manage orders from the dashboard.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    """Possible statuses for an order.

    Attributes:
        pending: Order created, awaiting payment confirmation.
        paid: Payment confirmed via Stripe webhook.
        shipped: Store owner has shipped the order.
        delivered: Order has been delivered to the customer.
        cancelled: Order was cancelled (refunded or abandoned).
    """

    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class Order(Base):
    """SQLAlchemy model representing a customer order.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the order to the store.
        customer_email: Email address of the customer who placed the order.
        status: Current order status (pending, paid, shipped, delivered, cancelled).
        total: Total order amount in the store's currency.
        stripe_session_id: Stripe Checkout session ID for payment tracking.
        shipping_address: Optional shipping address as free-text.
        created_at: Timestamp when the order was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store this order belongs to.
        items: Relationship to the order's line items.
    """

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.pending, nullable=False
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stripe_session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="orders", lazy="selectin")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base):
    """SQLAlchemy model representing a line item within an order.

    Captures the product, variant, quantity, and price at the time of
    purchase so that the order record remains accurate even if product
    details change later.

    Attributes:
        id: Unique identifier (UUID v4).
        order_id: Foreign key linking to the parent order.
        product_id: Foreign key to the product that was purchased.
        variant_id: Optional foreign key to the specific variant purchased.
        product_title: Product title snapshot at time of purchase.
        variant_name: Variant name snapshot at time of purchase (if applicable).
        quantity: Number of units purchased.
        unit_price: Price per unit at the time of purchase.
        created_at: Timestamp when the item was created.
        order: Relationship to the parent Order.
        product: Relationship to the Product.
        variant: Relationship to the ProductVariant (if applicable).
    """

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_title: Mapped[str] = mapped_column(String(500), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order = relationship("Order", back_populates="items")
    product = relationship("Product", lazy="selectin")
    variant = relationship("ProductVariant", lazy="selectin")
