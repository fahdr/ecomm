"""TeamMember and TeamInvite database models.

Defines the ``team_members`` and ``team_invites`` tables for managing
multi-user access to stores. Store owners can invite team members with
different roles to collaborate on store management.

**For Developers:**
    Import these models via ``app.models`` so that Alembic picks up schema
    changes automatically. The ``team_members`` table tracks accepted
    memberships with role-based access control. The ``team_invites`` table
    handles pending invitations with expiring tokens. The composite unique
    constraint on (``store_id``, ``user_id``) prevents duplicate memberships.

**For QA Engineers:**
    - ``TeamRole`` restricts roles to ``owner``, ``admin``, ``editor``,
      or ``viewer``.
    - ``owner`` has full access; ``admin`` can manage team and settings;
      ``editor`` can manage products and orders; ``viewer`` is read-only.
    - ``invited_email`` on TeamMember stores the original email used for
      the invitation (for audit purposes).
    - ``invite_accepted`` tracks whether the user has accepted their invite.
    - ``TeamInvite.token`` is a unique, time-limited token sent via email.
    - ``TeamInvite.expires_at`` determines when the invitation link expires.

**For End Users:**
    Teams let you invite other people to help manage your store. Assign
    roles to control what each team member can do: owners have full
    control, admins can manage settings and team, editors can handle
    products and orders, and viewers can only see data without making
    changes.
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TeamRole(str, enum.Enum):
    """Role-based access levels for team members.

    Attributes:
        owner: Full access to all store features and settings.
        admin: Can manage team members, settings, and all store data.
        editor: Can manage products, orders, and day-to-day operations.
        viewer: Read-only access to store data and analytics.
    """

    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class TeamMember(Base):
    """SQLAlchemy model representing a team member's access to a store.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the membership to a store.
        user_id: Foreign key linking the membership to a user account.
        role: The team member's access level (owner, admin, editor, viewer).
        invited_email: The email address used in the original invitation.
        invite_accepted: Whether the user has accepted the team invitation.
        created_at: Timestamp when the membership was created (DB server time).
        updated_at: Timestamp of the last update (DB server time, auto-updated).
        store: Relationship to the Store.
        user: Relationship to the User account.
    """

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("store_id", "user_id", name="uq_team_members_store_user"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole), nullable=False)
    invited_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_accepted: Mapped[bool] = mapped_column(
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

    store = relationship("Store", backref="team_members", lazy="selectin")
    user = relationship("User", backref="team_memberships", lazy="selectin")


class TeamInvite(Base):
    """SQLAlchemy model representing a pending team invitation.

    Invitations are sent via email with a unique token link. They expire
    after a configurable period. Once accepted, a TeamMember record is
    created and the invite can be deleted.

    Attributes:
        id: Unique identifier (UUID v4), generated server-side.
        store_id: Foreign key linking the invite to a store.
        email: Email address the invitation was sent to.
        role: The role that will be granted upon acceptance.
        token: Unique, URL-safe token used to accept the invitation.
        expires_at: Timestamp after which the invitation is no longer valid.
        created_at: Timestamp when the invitation was created (DB server time).
        store: Relationship to the Store.
    """

    __tablename__ = "team_invites"

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
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole), nullable=False)
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    store = relationship("Store", backref="team_invites", lazy="selectin")
