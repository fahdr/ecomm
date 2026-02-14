"""TaxRate database model.

Defines the ``tax_rates`` table for managing location-based tax rules.
Each tax rate is scoped to a store and can target a specific country,
state, and/or zip code.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``rate`` column uses ``Numeric(5, 2)`` to
    support rates like 0.0825 (8.25%). When calculating tax, match the
    customer's shipping address against ``country``, ``state``, and
    ``zip_code`` fields. Multiple matching rates may apply based on
    ``priority`` and ``is_inclusive`` settings.

**For QA Engineers:**
    - ``rate`` stores the tax as a decimal fraction (e.g. 0.0825 for 8.25%).
    - ``country`` is a 2-letter ISO country code (e.g. "US", "CA").
    - ``state`` and ``zip_code`` are optional for more granular targeting.
    - ``priority`` determines the order in which rates are applied when
      multiple rates match (lower = applied first).
    - ``is_inclusive`` means the rate is calculated on top of previously
      applied tax amounts rather than on the original subtotal.
    - ``is_active`` controls whether the rate is used in calculations.

**For End Users:**
    Tax rates let you configure sales tax for different regions. Set up
    rates by country, state, and zip code so the correct tax is
    automatically calculated at checkout. You can mark rates as compound
    if they should stack on top of other taxes.
"""

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
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaxRate(Base):
    """SQLAlchemy model representing a location-based tax rate.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the tax rate to its store.
        name: Human-readable name (e.g. "California State Tax").
        rate: Tax rate as a decimal fraction (e.g. 0.0825 for 8.25%).
        country: ISO 3166-1 alpha-2 country code (e.g. "US").
        state: Optional state or province name for regional targeting.
        zip_code: Optional postal code for hyper-local targeting.
        is_active: Whether this rate is currently applied at checkout.
        priority: Application order when multiple rates match (lower first).
        is_inclusive: Whether this rate compounds on top of previously
            applied taxes.
        created_at: Timestamp when the rate was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
    """

    __tablename__ = "tax_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_inclusive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    store = relationship("Store", backref="tax_rates", lazy="selectin")
