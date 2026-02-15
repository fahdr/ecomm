"""Store database model.

Defines the ``stores`` table representing user-created dropshipping stores.
Each store belongs to a single user and has a unique slug used for
subdomain-based routing on the public storefront.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``user_id`` foreign key enforces ownership.
    The ``theme``, ``logo_url``, ``favicon_url``, and ``custom_css`` fields
    support storefront theming (Feature 15). The ``default_currency``
    field enables multi-currency support (Feature 21).

**For QA Engineers:**
    - Store slugs are unique across the platform and auto-generated from the name.
    - Soft-delete is implemented via the ``status`` field (set to ``deleted``).
    - The ``StoreStatus`` enum restricts status to ``active``, ``paused``, or ``deleted``.
    - ``default_currency`` is a 3-letter ISO currency code (default "USD").
    - ``theme`` identifies the active storefront theme (default "default").
    - ``logo_url`` and ``favicon_url`` are optional URLs for store branding.
    - ``custom_css`` allows store owners to inject custom CSS into the storefront.

**For End Users:**
    Each store you create gets a unique URL based on its name. You can pause
    or delete stores from the dashboard at any time. Customize your store
    with a logo, favicon, theme, and custom CSS to match your brand.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StoreType(str, enum.Enum):
    """Type of store determining feature availability.

    Attributes:
        dropshipping: Traditional dropshipping store — products sourced from
            suppliers and shipped directly to customers. No inventory management.
        ecommerce: Standard ecommerce store — own inventory, warehouses,
            and fulfillment. Full inventory management and whitelabeling.
        hybrid: Combination of dropshipping and ecommerce — some products
            sourced from suppliers, others from own warehouses.
    """

    dropshipping = "dropshipping"
    ecommerce = "ecommerce"
    hybrid = "hybrid"


class StoreStatus(str, enum.Enum):
    """Possible statuses for a store.

    Attributes:
        active: Store is live and accessible on the storefront.
        paused: Store is temporarily hidden from the storefront.
        deleted: Store has been soft-deleted by the owner.
    """

    active = "active"
    paused = "paused"
    deleted = "deleted"


class Store(Base):
    """SQLAlchemy model representing a dropshipping store.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        user_id: Foreign key linking the store to its owner.
        name: Display name of the store chosen by the user.
        slug: URL-friendly unique identifier derived from the name.
        niche: The product niche or category the store focuses on.
        description: Optional longer description of the store.
        status: Current status of the store (active, paused, or deleted).
        default_currency: ISO 4217 currency code for the store (default "USD").
        theme: Identifier for the active storefront theme (default "default").
        logo_url: Optional URL for the store's logo image.
        favicon_url: Optional URL for the store's favicon.
        custom_css: Optional custom CSS injected into the storefront.
        created_at: Timestamp when the store was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        owner: Relationship back to the User who owns this store.
    """

    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    niche: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD", server_default="USD"
    )
    theme: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default", server_default="default"
    )
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    store_type: Mapped[StoreType] = mapped_column(
        Enum(StoreType), default=StoreType.dropshipping,
        server_default="dropshipping", nullable=False
    )
    status: Mapped[StoreStatus] = mapped_column(
        Enum(StoreStatus), default=StoreStatus.active, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner = relationship("User", backref="stores", lazy="selectin")
