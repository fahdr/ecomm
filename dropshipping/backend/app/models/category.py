"""Category and ProductCategory database models.

Defines the ``categories`` and ``product_categories`` tables for organizing
products into hierarchical groupings. Categories support self-referential
parent-child nesting (e.g. Electronics > Phones > Smartphones) and are
scoped to a single store.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``parent_id`` self-referential foreign key
    enables arbitrary depth category trees. The ``position`` column supports
    manual ordering within the same parent. The ``product_categories``
    junction table enables a many-to-many relationship between products
    and categories.

**For QA Engineers:**
    - Category slugs are unique per store (composite unique constraint on
      ``store_id`` + ``slug``).
    - ``parent_id`` may be null (top-level category) or reference another
      category in the same store.
    - ``is_active`` controls storefront visibility; inactive categories
      and their products should be hidden.
    - ``position`` is used for manual sort ordering within the same level.
    - The ``product_categories`` junction table enforces uniqueness on
      (``product_id``, ``category_id``) to prevent duplicate assignments.

**For End Users:**
    Categories help you organize your products so customers can browse by
    type. You can create nested categories (e.g. "Clothing" with
    subcategories "Men" and "Women") and assign products to multiple
    categories. Reorder categories to control how they appear on your
    storefront.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    """SQLAlchemy model representing a product category within a store.

    Categories form a tree structure via the self-referential ``parent_id``
    column. Each category has a URL-friendly slug that is unique within its
    store.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the category to its store.
        name: Display name of the category.
        slug: URL-friendly identifier, unique within the store.
        description: Optional longer description of the category.
        image_url: Optional URL for a category banner or icon image.
        parent_id: Optional foreign key to a parent category for nesting.
        position: Sort order within the same parent level (lower = first).
        is_active: Whether the category is visible on the storefront.
        created_at: Timestamp when the category was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store this category belongs to.
        parent: Relationship to the parent Category (if nested).
        children: Relationship to child categories (subcategories).
        products: Many-to-many relationship to products via the junction table.
    """

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("store_id", "slug", name="uq_categories_store_slug"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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

    store = relationship("Store", backref="categories", lazy="selectin")
    parent = relationship(
        "Category",
        remote_side="Category.id",
        backref="children",
        lazy="selectin",
    )
    products = relationship(
        "Product",
        secondary="product_categories",
        backref="categories",
        lazy="selectin",
    )


class ProductCategory(Base):
    """Junction table linking products to categories (many-to-many).

    A product can belong to multiple categories, and a category can
    contain multiple products.

    Attributes:
        id: Unique identifier (UUID v4).
        product_id: Foreign key to the product.
        category_id: Foreign key to the category.
    """

    __tablename__ = "product_categories"
    __table_args__ = (
        UniqueConstraint(
            "product_id", "category_id", name="uq_product_categories_pair"
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
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
