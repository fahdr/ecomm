"""
API Key model for programmatic access to the service.

API keys allow external integrations (including the dropshipping platform)
to authenticate without user credentials. Keys are hashed with SHA-256
and only shown once at creation time.

For Developers:
    The `key_hash` stores SHA-256(key). The full key is only returned
    at creation time. Use `key_prefix` (first 8 chars) for identification.
    Scopes control what operations the key can perform.

For QA Engineers:
    Test key creation (POST /api/v1/api-keys), verify the key works
    via X-API-Key header, and test key revocation.

For End Users:
    API keys let you integrate RankPilot with your own
    applications. Generate keys in the dashboard under Settings > API Keys.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ApiKey(Base):
    """
    API key for programmatic service access.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        name: Human-readable label for the key.
        key_hash: SHA-256 hash of the API key.
        key_prefix: First 8 characters of the key for identification.
        scopes: List of permission scopes (e.g., ['read', 'write']).
        is_active: Whether the key is currently active.
        last_used_at: Timestamp of last API call with this key.
        expires_at: Optional expiration timestamp.
        created_at: Key creation timestamp.
        owner: Related User record.
    """

    __tablename__ = "api_keys"

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
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["read"], nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="api_keys")
