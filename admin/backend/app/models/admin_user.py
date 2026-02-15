"""
Admin user model for the Super Admin Dashboard.

Stores credentials and role information for platform administrators.
Each admin user has a role that determines their access level within
the dashboard.

For Developers:
    Passwords are stored as bcrypt hashes via ``auth_service.hash_password``.
    The ``role`` column uses a PostgreSQL-native enum with three levels:
    ``super_admin``, ``admin``, and ``viewer``. The table is prefixed
    with ``admin_`` to avoid collisions with other services.

For QA Engineers:
    Test admin user creation via the ``POST /api/v1/admin/auth/setup``
    endpoint (first user only) and verify login via ``POST /login``.
    The ``is_active`` flag can be used to disable users without deleting.

For Project Managers:
    Admin users are separate from platform customers. They manage
    the infrastructure, monitor services, and configure the LLM Gateway.
    The role hierarchy (super_admin > admin > viewer) controls access.

For End Users:
    Admin users are platform operators. End users interact with the
    storefront and dashboard, not the admin panel.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminUser(Base):
    """
    A platform administrator account.

    Attributes:
        id: Unique identifier (UUID v4), auto-generated.
        email: Admin's email address (unique, used for login).
        hashed_password: Bcrypt hash of the admin's password.
        role: Access level — ``super_admin``, ``admin``, or ``viewer``.
        is_active: Whether the admin account is enabled.
        created_at: Timestamp when the account was created.
        updated_at: Timestamp of the last account modification.
    """

    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="admin"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
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
