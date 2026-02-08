"""Upsell database model.

Defines the ``upsells`` table for managing product upsell, cross-sell, and
bundle recommendations. Each upsell links a source product to a target
product within the same store.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``source_product_id`` is the product being
    viewed, and ``target_product_id`` is the recommended product. The
    composite unique constraint on (source, target, type) prevents
    duplicate recommendations of the same type.

**For QA Engineers:**
    - ``UpsellType`` restricts the recommendation type to ``upsell``,
      ``cross_sell``, or ``bundle``.
    - ``discount_percentage`` is an optional incentive discount on the
      target product when bought via the upsell.
    - ``position`` controls display order among upsells for the same
      source product.
    - ``is_active`` controls visibility; inactive upsells are not shown
      on the storefront.
    - The unique constraint prevents creating duplicate upsell records
      for the same source-target-type combination.

**For End Users:**
    Upsells help you increase average order value by recommending
    complementary or upgraded products. Set up upsells (upgrade offers),
    cross-sells (related products), or bundles (buy-together deals) on
    any product page. You can optionally offer a discount to incentivize
    the purchase.
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


class UpsellType(str, enum.Enum):
    """Types of product recommendations.

    Attributes:
        upsell: Recommends an upgraded or premium version of the product.
        cross_sell: Recommends a complementary product often bought together.
        bundle: Recommends a discounted package of multiple products.
    """

    upsell = "upsell"
    cross_sell = "cross_sell"
    bundle = "bundle"


class Upsell(Base):
    """SQLAlchemy model representing a product recommendation (upsell/cross-sell/bundle).

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the upsell to its store.
        source_product_id: Foreign key to the product being viewed.
        target_product_id: Foreign key to the recommended product.
        upsell_type: The type of recommendation (upsell, cross_sell, bundle).
        discount_percentage: Optional percentage discount on the target
            product when purchased via this recommendation.
        title: Optional display title for the recommendation.
        description: Optional description explaining the recommendation.
        position: Sort order among recommendations for the same source
            product (lower = first).
        is_active: Whether this recommendation is shown on the storefront.
        created_at: Timestamp when the upsell was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        source_product: Relationship to the source Product (being viewed).
        target_product: Relationship to the target Product (being recommended).
    """

    __tablename__ = "upsells"
    __table_args__ = (
        UniqueConstraint(
            "source_product_id",
            "target_product_id",
            "upsell_type",
            name="uq_upsells_source_target_type",
        ),
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
    source_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upsell_type: Mapped[UpsellType] = mapped_column(
        Enum(UpsellType), nullable=False
    )
    discount_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="upsells", lazy="selectin")
    source_product = relationship(
        "Product",
        foreign_keys=[source_product_id],
        backref="upsells_as_source",
        lazy="selectin",
    )
    target_product = relationship(
        "Product",
        foreign_keys=[target_product_id],
        backref="upsells_as_target",
        lazy="selectin",
    )
