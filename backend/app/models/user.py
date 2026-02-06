"""User database model.

Defines the ``users`` table used for authentication and authorization.
Each user has a unique email address and a bcrypt-hashed password.

**For Developers:**
    Import this model via ``app.models`` so that Alembic picks up schema
    changes automatically.

**For QA Engineers:**
    The ``is_active`` flag can be toggled to disable a user account without
    deleting it, which is useful for testing suspension flows.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """SQLAlchemy model representing an application user.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        email: User's email address, unique and indexed for fast lookups.
        hashed_password: Bcrypt hash of the user's password.
        is_active: Whether the account is enabled. Defaults to True.
        created_at: Timestamp when the record was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
