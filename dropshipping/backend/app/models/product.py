"""Product and ProductVariant database models.

Defines the ``products`` and ``product_variants`` tables for store inventory
management. Each product belongs to a single store and can have multiple
variants (e.g. sizes, colors).

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` foreign key enforces store scoping.
    Products use soft-delete via the ``status`` field (set to ``archived``).
    The ``avg_rating`` and ``review_count`` are denormalized from the
    ``reviews`` table for fast product listing queries. The ``tags`` JSON
    column stores free-form tag strings for search and filtering.

**For QA Engineers:**
    - Product slugs are unique per store (enforced via database unique constraint
      on ``store_id`` + ``slug``).
    - Soft-delete sets ``status`` to ``archived`` rather than removing the row.
    - The ``ProductStatus`` enum restricts status to ``draft``, ``active``, or ``archived``.
    - ``images`` is a JSON array of image URL strings.
    - ``compare_at_price`` is the "was" price shown with a strikethrough.
    - ``cost`` is the supplier cost (private, never exposed publicly).
    - ``avg_rating`` is a denormalized average of approved review ratings
      (null if no reviews).
    - ``review_count`` is a denormalized count of approved reviews.
    - ``tags`` is a JSON array of tag strings for search filtering.

**For End Users:**
    Products are the items you sell in your store. Each product has a title,
    description, price, and optional images. You can create variants for
    different sizes, colors, or other options.
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
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductStatus(str, enum.Enum):
    """Possible statuses for a product.

    Attributes:
        draft: Product is being prepared and not visible on the storefront.
        active: Product is live and visible to customers.
        archived: Product has been soft-deleted / retired.
    """

    draft = "draft"
    active = "active"
    archived = "archived"


class Product(Base):
    """SQLAlchemy model representing a product in a store.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the product to its store.
        title: Display title of the product.
        slug: URL-friendly identifier, unique within the store.
        description: Optional longer description with product details.
        price: Selling price shown to customers.
        compare_at_price: Optional original/"was" price for showing discounts.
        cost: Supplier cost (private, not exposed in public API).
        images: JSON array of image URL strings.
        status: Current product status (draft, active, or archived).
        avg_rating: Denormalized average star rating from approved reviews.
        review_count: Denormalized count of approved reviews.
        tags: JSON array of tag strings for search and filtering.
        seo_title: Optional custom SEO title for search engines.
        seo_description: Optional custom SEO meta description.
        created_at: Timestamp when the product was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship back to the Store that owns this product.
        variants: Relationship to the product's variants.
    """

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("store_id", "slug", name="uq_products_store_slug"),
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
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    compare_at_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    images: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.draft, nullable=False
    )
    avg_rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="products", lazy="selectin")
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductVariant(Base):
    """SQLAlchemy model representing a variant of a product.

    Variants allow a product to have different options (e.g. size, color)
    each with its own SKU, price override, and inventory count.

    Attributes:
        id: Unique identifier (UUID v4).
        product_id: Foreign key linking to the parent product.
        name: Display name of the variant (e.g. "Large", "Blue").
        sku: Optional stock-keeping unit identifier.
        price: Optional price override; if null, uses the product's base price.
        inventory_count: Number of units in stock.
        created_at: Timestamp when the variant was created.
        updated_at: Timestamp of the last update.
        product: Relationship back to the parent Product.
    """

    __tablename__ = "product_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    inventory_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    weight_unit: Mapped[str] = mapped_column(
        String(10), default="kg", server_default="kg", nullable=False
    )
    track_inventory: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    allow_backorder: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
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

    product = relationship("Product", back_populates="variants")
    inventory_levels = relationship(
        "InventoryLevel",
        back_populates="variant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
