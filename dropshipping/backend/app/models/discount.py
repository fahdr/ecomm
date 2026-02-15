"""Discount, DiscountProduct, DiscountCategory, and DiscountUsage database models.

Defines the ``discounts``, ``discount_products``, ``discount_categories``, and
``discount_usages`` tables for managing store-level promotional discounts.
Discounts can apply to all products, specific products, or specific categories
and support percentage, fixed-amount, and free-shipping types.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` foreign key scopes discounts to
    a single store. The ``code`` field is unique per store (not globally)
    via a composite unique constraint. Many-to-many relationships with
    products and categories are handled via the ``discount_products`` and
    ``discount_categories`` junction tables respectively.

**For QA Engineers:**
    - ``DiscountType`` restricts the discount mechanism to ``percentage``,
      ``fixed_amount``, or ``free_shipping``.
    - ``DiscountStatus`` restricts the lifecycle to ``active``, ``expired``,
      or ``disabled``.
    - ``AppliesTo`` restricts targeting to ``all``, ``specific_products``,
      or ``specific_categories``.
    - ``times_used`` increments each time a discount is redeemed; once it
      reaches ``max_uses`` the discount should no longer be accepted.
    - ``starts_at`` and ``expires_at`` define the valid redemption window.
    - ``DiscountUsage`` records each redemption with the order, customer,
      and amount saved for audit purposes.

**For End Users:**
    Discounts let store owners create coupon codes that customers enter at
    checkout to receive a price reduction. Discounts can be percentage-based
    (e.g. 20% off), a fixed dollar amount, or free shipping. Store owners
    can limit discounts to specific products or categories, set maximum
    usage counts, and define validity windows.
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DiscountType(str, enum.Enum):
    """Supported discount calculation methods.

    Attributes:
        percentage: Reduces the order total by a percentage of the subtotal.
        fixed_amount: Reduces the order total by a fixed currency amount.
        free_shipping: Waives the shipping cost for the order.
    """

    percentage = "percentage"
    fixed_amount = "fixed_amount"
    free_shipping = "free_shipping"


class DiscountStatus(str, enum.Enum):
    """Lifecycle states for a discount.

    Attributes:
        active: Discount is available for redemption.
        expired: Discount has passed its ``expires_at`` date.
        disabled: Discount was manually disabled by the store owner.
    """

    active = "active"
    expired = "expired"
    disabled = "disabled"


class AppliesTo(str, enum.Enum):
    """Targeting scope for a discount.

    Attributes:
        all: Discount applies to every product in the store.
        specific_products: Discount applies only to products linked via
            the ``discount_products`` junction table.
        specific_categories: Discount applies only to products belonging
            to categories linked via the ``discount_categories`` junction table.
    """

    all = "all"
    specific_products = "specific_products"
    specific_categories = "specific_categories"


class Discount(Base):
    """SQLAlchemy model representing a store discount / coupon code.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the discount to its store.
        code: Coupon code that customers enter at checkout, unique per store.
        description: Optional human-readable description of the promotion.
        discount_type: The calculation method (percentage, fixed_amount,
            or free_shipping).
        value: The numeric discount value (percentage points or currency amount).
        minimum_order_amount: Optional minimum cart subtotal required to use
            this discount.
        max_uses: Optional cap on the total number of redemptions.
        times_used: Running count of how many times this discount has been used.
        starts_at: Date/time when the discount becomes active.
        expires_at: Optional date/time when the discount expires.
        status: Current lifecycle status (active, expired, disabled).
        applies_to: Targeting scope (all, specific_products, specific_categories).
        created_at: Timestamp when the discount was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store this discount belongs to.
        products: Many-to-many relationship to targeted Product records.
        categories: Many-to-many relationship to targeted Category records.
        usages: One-to-many relationship to DiscountUsage audit records.
    """

    __tablename__ = "discounts"
    __table_args__ = (
        UniqueConstraint("store_id", "code", name="uq_discounts_store_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    minimum_order_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[DiscountStatus] = mapped_column(
        Enum(DiscountStatus), default=DiscountStatus.active, nullable=False
    )
    applies_to: Mapped[AppliesTo] = mapped_column(
        Enum(AppliesTo), default=AppliesTo.all, nullable=False
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

    store = relationship("Store", backref="discounts", lazy="selectin")
    products = relationship(
        "Product",
        secondary="discount_products",
        backref="discounts",
        lazy="selectin",
    )
    categories = relationship(
        "Category",
        secondary="discount_categories",
        backref="discounts",
        lazy="selectin",
    )
    usages = relationship(
        "DiscountUsage",
        back_populates="discount",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DiscountProduct(Base):
    """Junction table linking discounts to specific products.

    Used when a discount's ``applies_to`` is set to ``specific_products``.

    Attributes:
        id: Unique identifier (UUID v4).
        discount_id: Foreign key to the discount.
        product_id: Foreign key to the targeted product.
    """

    __tablename__ = "discount_products"
    __table_args__ = (
        UniqueConstraint(
            "discount_id", "product_id", name="uq_discount_products_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discount_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class DiscountCategory(Base):
    """Junction table linking discounts to specific categories.

    Used when a discount's ``applies_to`` is set to ``specific_categories``.

    Attributes:
        id: Unique identifier (UUID v4).
        discount_id: Foreign key to the discount.
        category_id: Foreign key to the targeted category.
    """

    __tablename__ = "discount_categories"
    __table_args__ = (
        UniqueConstraint(
            "discount_id", "category_id", name="uq_discount_categories_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discount_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class DiscountUsage(Base):
    """Audit record capturing each discount redemption.

    Tracks which customer used a discount on which order and how much
    they saved. Useful for analytics, fraud detection, and reconciliation.

    Attributes:
        id: Unique identifier (UUID v4).
        discount_id: Foreign key to the redeemed discount.
        order_id: Foreign key to the order where the discount was applied.
        customer_email: Email of the customer who redeemed the discount.
        amount_saved: The actual currency amount deducted by this discount.
        created_at: Timestamp when the redemption occurred.
        discount: Relationship back to the parent Discount.
        order: Relationship to the Order.
    """

    __tablename__ = "discount_usages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    discount_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("discounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_saved: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    discount = relationship("Discount", back_populates="usages")
    order = relationship("Order", backref="discount_usages", lazy="selectin")
