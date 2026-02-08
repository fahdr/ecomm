"""CustomDomain database model.

Defines the ``custom_domains`` table for managing custom domain
configurations for stores. Each store can have at most one custom domain
that replaces the default subdomain-based URL.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``store_id`` has a unique constraint ensuring
    one domain per store. The ``domain`` column is globally unique since
    no two stores can use the same domain. The ``verification_token``
    is a DNS TXT record value the store owner must add to prove domain
    ownership.

**For QA Engineers:**
    - ``DomainStatus`` restricts the lifecycle to ``pending``, ``verified``,
      ``active``, or ``failed``.
    - ``pending``: domain added, awaiting DNS verification.
    - ``verified``: DNS TXT record confirmed, SSL not yet provisioned.
    - ``active``: SSL provisioned, domain is fully operational.
    - ``failed``: DNS verification failed after timeout.
    - ``domain`` is globally unique (no two stores can claim the same domain).
    - ``store_id`` is unique (one custom domain per store).
    - ``ssl_provisioned`` is set to True after an SSL certificate is
      successfully issued.

**For End Users:**
    Custom domains let you use your own domain name (e.g. mystore.com)
    instead of the default platform subdomain. Add your domain, verify
    ownership by adding a DNS record, and SSL will be automatically
    provisioned. Your customers will see your brand's domain in their
    browser.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DomainStatus(str, enum.Enum):
    """Lifecycle states for a custom domain.

    Attributes:
        pending: Domain added, awaiting DNS verification.
        verified: DNS ownership confirmed, SSL pending.
        active: SSL provisioned, domain fully operational.
        failed: DNS verification failed after timeout.
    """

    pending = "pending"
    verified = "verified"
    active = "active"
    failed = "failed"


class CustomDomain(Base):
    """SQLAlchemy model representing a custom domain for a store.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking to the store (unique -- one domain
            per store).
        domain: The custom domain name (e.g. "mystore.com"), globally
            unique.
        status: Current verification/provisioning status.
        verification_token: DNS TXT record value for domain ownership
            verification.
        verified_at: Timestamp when DNS verification succeeded (null until
            verified).
        ssl_provisioned: Whether an SSL certificate has been issued.
        created_at: Timestamp when the domain was added (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
    """

    __tablename__ = "custom_domains"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    domain: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    status: Mapped[DomainStatus] = mapped_column(
        Enum(DomainStatus), default=DomainStatus.pending, nullable=False
    )
    verification_token: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ssl_provisioned: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
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

    store = relationship("Store", backref="custom_domain", uselist=False, lazy="selectin")
