"""CustomerAccount and CustomerWishlist database models.

Defines the ``customer_accounts`` and ``customer_wishlists`` tables for
storefront customer-facing accounts. Customer accounts allow store visitors
to register, view order history, and maintain a wishlist of products they
are interested in. Each customer account is scoped to a single store.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` + ``email`` composite unique
    constraint on ``customer_accounts`` ensures a customer can only have
    one account per store while allowing the same email across different
    stores. The ``customer_wishlists`` junction table links customer
    accounts to products with a composite unique constraint preventing
    duplicate wishlist entries.

    Note: Customer accounts are separate from the platform ``User`` model.
    Users are store owners who manage the dashboard; customer accounts are
    shoppers who buy from the storefront.

**For QA Engineers:**
    - ``CustomerAccount.email`` + ``store_id`` is unique (one account per
      store per email).
    - ``hashed_password`` stores a bcrypt hash for storefront login.
    - ``is_active`` can be toggled to disable a customer account.
    - ``CustomerWishlist`` enforces uniqueness on (``customer_id``,
      ``product_id``) to prevent adding the same product twice.
    - Deleting a customer account cascades to their wishlist entries.
    - Deleting a product removes it from all wishlists (CASCADE).

**For End Users:**
    Customer accounts let your store visitors create an account to track
    their orders and save products to a wishlist. Customers can register
    with their email, log in to view past orders, and maintain a list of
    products they want to buy later.
"""

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


class CustomerAccount(Base):
    """SQLAlchemy model representing a storefront customer account.

    Customer accounts are separate from platform User accounts. Users own
    and manage stores via the dashboard; customer accounts are created by
    shoppers on the storefront to track orders and wishlists.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the customer to a specific store.
        email: Customer's email address, unique within the store.
        hashed_password: Bcrypt hash of the customer's storefront password.
        first_name: Customer's first name.
        last_name: Customer's last name.
        is_active: Whether the account is enabled. Defaults to True.
        created_at: Timestamp when the account was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store this customer belongs to.
        wishlist_items: One-to-many relationship to CustomerWishlist entries.
    """

    __tablename__ = "customer_accounts"
    __table_args__ = (
        UniqueConstraint("store_id", "email", name="uq_customer_accounts_store_email"),
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
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

    store = relationship("Store", backref="customer_accounts", lazy="selectin")
    wishlist_items = relationship(
        "CustomerWishlist",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CustomerWishlist(Base):
    """Junction table linking customer accounts to wishlist products.

    Each record represents a product that a customer has saved to their
    wishlist for future purchase. The composite unique constraint prevents
    adding the same product twice.

    Attributes:
        id: Unique identifier (UUID v4).
        customer_id: Foreign key to the customer account.
        product_id: Foreign key to the wishlisted product.
        added_at: Timestamp when the product was added to the wishlist.
        customer: Relationship back to the CustomerAccount.
        product: Relationship to the Product.
    """

    __tablename__ = "customer_wishlists"
    __table_args__ = (
        UniqueConstraint(
            "customer_id", "product_id", name="uq_customer_wishlists_pair"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer = relationship("CustomerAccount", back_populates="wishlist_items")
    product = relationship("Product", backref="wishlisted_by", lazy="selectin")


class CustomerAddress(Base):
    """Saved shipping address for a customer account.

    Customers can save multiple addresses and mark one as default.
    The default address is pre-filled during checkout.

    Attributes:
        id: Unique identifier (UUID v4).
        customer_id: Foreign key to the customer account.
        store_id: Foreign key to the store (denormalized for query efficiency).
        label: Human-friendly label (e.g. "Home", "Office").
        name: Full name for the shipping label.
        line1: Street address line 1.
        line2: Optional street address line 2.
        city: City name.
        state: State/province (optional for some countries).
        postal_code: Postal/ZIP code.
        country: ISO 3166-1 alpha-2 country code.
        phone: Optional phone number.
        is_default: Whether this is the customer's default address.
        created_at: Timestamp when the address was created.
        updated_at: Timestamp of the last update.
        customer: Relationship back to the CustomerAccount.
    """

    __tablename__ = "customer_addresses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False, default="Home")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer = relationship("CustomerAccount", backref="addresses")
