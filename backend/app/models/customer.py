"""Customer database model.

Defines the ``customers`` table for per-store customer accounts. Each
customer belongs to a single store and is identified by the combination
of ``(store_id, email)``.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` foreign key scopes customers
    to a store. Passwords are hashed with bcrypt via ``auth_service``.

**For QA Engineers:**
    - Customers are per-store: the same email can register on different
      stores independently.
    - ``is_active`` defaults to True and can be used to deactivate accounts.
    - ``first_name``, ``last_name``, and ``phone`` are optional profile fields.

**For End Users:**
    Create an account on a store to track your orders and save products
    to your wishlist.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Customer(Base):
    """SQLAlchemy model representing a per-store customer account.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the customer to the store.
        email: Customer's email address (unique per store).
        hashed_password: Bcrypt-hashed password.
        first_name: Optional first name.
        last_name: Optional last name.
        phone: Optional phone number.
        is_active: Whether the account is active (default True).
        created_at: Timestamp when the account was created.
        updated_at: Timestamp of the last update.
        store: Relationship to the Store this customer belongs to.
    """

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("store_id", "email", name="uq_customers_store_email"),
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
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
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

    store = relationship("Store", backref="customers", lazy="selectin")
