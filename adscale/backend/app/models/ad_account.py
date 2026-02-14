"""
Ad Account model for connecting external advertising platforms.

Stores credentials and connection state for Google Ads, Meta (Facebook) Ads,
and other advertising platforms. Access tokens are encrypted at rest.

For Developers:
    Each user can connect multiple ad accounts across platforms.
    The `access_token_enc` field stores an encrypted OAuth token.
    The `status` field tracks the health of the connection.

For QA Engineers:
    Test account connection (mock OAuth flow), listing, and disconnection.
    Verify that disconnecting an account cascades to pause related campaigns.

For Project Managers:
    Ad accounts are the bridge between AdScale and the advertising platforms.
    Users must connect at least one account before creating campaigns.

For End Users:
    Connect your Google Ads or Meta Ads account to start managing campaigns.
    Go to Settings > Ad Accounts to connect or disconnect platforms.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AdPlatform(str, enum.Enum):
    """
    Supported advertising platforms.

    Attributes:
        google: Google Ads platform.
        meta: Meta (Facebook/Instagram) Ads platform.
    """

    google = "google"
    meta = "meta"


class AccountStatus(str, enum.Enum):
    """
    Connection health status for an ad account.

    Attributes:
        active: Account is connected and functioning.
        paused: Account connection is paused by the user.
        error: Account connection has an error (e.g., expired token).
    """

    active = "active"
    paused = "paused"
    error = "error"


class AdAccount(Base):
    """
    External advertising platform account connection.

    Represents a linked Google Ads or Meta Ads account. Stores the
    external account ID, encrypted access token, and connection state.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: The advertising platform (google or meta).
        account_id_external: The platform's own account identifier.
        account_name: Human-readable name for the account.
        access_token_enc: Encrypted OAuth access token (nullable).
        is_connected: Whether the account is currently connected.
        status: Connection health status (active, paused, error).
        connected_at: Timestamp when the account was first connected.
        created_at: Record creation timestamp.
        user: Related User record.
        campaigns: Campaigns associated with this ad account.
    """

    __tablename__ = "ad_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    platform: Mapped[AdPlatform] = mapped_column(
        Enum(AdPlatform), nullable=False
    )
    account_id_external: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    is_connected: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus), default=AccountStatus.active, nullable=False
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", backref="ad_accounts", lazy="selectin")
    campaigns = relationship(
        "Campaign", back_populates="ad_account", lazy="selectin",
        cascade="all, delete-orphan"
    )
