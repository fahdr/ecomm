"""
Competitor and CompetitorProduct models for the SpyDrop service.

Competitors represent external stores being monitored. Each competitor
can have many tracked products, with full price history stored as JSON.

For Developers:
    The `platform` field identifies the e-commerce platform the competitor
    runs on (Shopify, WooCommerce, or custom). This determines which
    scraping strategy is used during scans.

    `price_history` is stored as a JSON list of {date, price} dicts,
    appended to during each scan. The `CompetitorProduct.status` field
    tracks whether a product is currently available or has been removed.

For QA Engineers:
    Test competitor CRUD via the /api/v1/competitors endpoints.
    Verify plan limit enforcement (free=3, pro=25, enterprise=unlimited).
    Test product tracking and price history accumulation across scans.

For Project Managers:
    Competitors are the core resource — each one represents a store
    the user wants to monitor. Products are discovered during scans
    and tracked over time for price changes and availability.

For End Users:
    Add competitor stores you want to monitor. SpyDrop will scan them
    regularly and track all their products, prices, and availability.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Competitor(Base):
    """
    A competitor store being monitored by a SpyDrop user.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Human-readable name for the competitor store.
        url: The competitor store's URL.
        platform: E-commerce platform ('shopify', 'woocommerce', 'custom').
        last_scanned: Timestamp of the most recent scan.
        status: Current monitoring status ('active', 'paused', 'error').
        product_count: Number of tracked products (denormalized counter).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        products: Related CompetitorProduct records.
        scan_results: Related ScanResult records.
        alerts: Related PriceAlert records scoped to this competitor.
    """

    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    platform: Mapped[str] = mapped_column(
        String(50), default="custom", nullable=False
    )
    last_scanned: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    product_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    products: Mapped[list["CompetitorProduct"]] = relationship(
        "CompetitorProduct",
        back_populates="competitor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    scan_results: Mapped[list["ScanResult"]] = relationship(
        "ScanResult",
        back_populates="competitor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alerts: Mapped[list["PriceAlert"]] = relationship(
        "PriceAlert",
        back_populates="competitor",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="PriceAlert.competitor_id",
    )
    owner: Mapped["User"] = relationship("User", lazy="selectin")


class CompetitorProduct(Base):
    """
    A product discovered on a competitor's store.

    Tracks the product's price over time with a JSON price_history field
    that accumulates entries from each scan.

    Attributes:
        id: Unique identifier (UUID v4).
        competitor_id: Foreign key to the parent Competitor.
        title: Product title as displayed on the competitor's site.
        url: Direct URL to the product page.
        image_url: Product image URL (optional).
        price: Current price (most recent scan).
        currency: Currency code (default 'USD').
        first_seen: Timestamp when the product was first discovered.
        last_seen: Timestamp when the product was last seen in a scan.
        price_history: JSON list of {date, price} entries.
        status: Product availability ('active', 'removed').
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        competitor: Related Competitor record.
        source_matches: Related SourceMatch records.
        alerts: Related PriceAlert records scoped to this product.
    """

    __tablename__ = "competitor_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    competitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(
        String(10), default="USD", nullable=False
    )
    first_seen: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    price_history: Mapped[dict] = mapped_column(
        JSON, default=list, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    competitor: Mapped["Competitor"] = relationship(
        "Competitor", back_populates="products", lazy="selectin"
    )
    source_matches: Mapped[list["SourceMatch"]] = relationship(
        "SourceMatch",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alerts: Mapped[list["PriceAlert"]] = relationship(
        "PriceAlert",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="PriceAlert.competitor_product_id",
    )


# Avoid circular import — import at bottom for type hints
from app.models.alert import PriceAlert  # noqa: E402
from app.models.scan import ScanResult  # noqa: E402
from app.models.source_match import SourceMatch  # noqa: E402
from app.models.user import User  # noqa: E402
