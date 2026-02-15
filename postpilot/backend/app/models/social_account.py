"""
Social media account model for connecting user profiles to social platforms.

Each SocialAccount represents a single connected social media profile (e.g.,
one Instagram business account, one TikTok creator account). Users can connect
multiple accounts across different platforms, up to their plan limit.

For Developers:
    The `platform` field uses a PostgreSQL Enum for type safety. Access tokens
    are stored encrypted (suffix `_enc`) and should never be returned raw to
    the client. The `is_connected` flag tracks whether the OAuth flow has been
    completed and the token is still valid.

For QA Engineers:
    Test connecting/disconnecting accounts, verify plan limits on
    `max_secondary` (social accounts), and ensure tokens are never
    leaked in API responses.

For Project Managers:
    Social accounts are the foundation of PostPilot — users must connect
    at least one account before they can schedule or publish posts.

For End Users:
    Connect your Instagram, Facebook, or TikTok account to start
    scheduling posts. You can manage connections in the Accounts page.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SocialPlatform(str, enum.Enum):
    """
    Supported social media platforms.

    Attributes:
        instagram: Instagram (Meta) business or creator accounts.
        facebook: Facebook Pages for business publishing.
        tiktok: TikTok creator or business accounts.
        twitter: Twitter/X accounts for short-form content.
        pinterest: Pinterest business accounts for visual discovery.
    """

    instagram = "instagram"
    facebook = "facebook"
    tiktok = "tiktok"
    twitter = "twitter"
    pinterest = "pinterest"


class SocialAccount(Base):
    """
    A connected social media account belonging to a user.

    Attributes:
        id: Unique identifier (UUID v4).
        user_id: Foreign key to the owning user.
        platform: Social media platform (instagram, facebook, tiktok, twitter, pinterest).
        account_name: Display name of the social account (e.g., @mybrand).
        account_id_external: Platform-specific account/page ID.
        access_token_enc: Encrypted OAuth access token (never returned to client).
        refresh_token_enc: Encrypted OAuth refresh token (never returned to client).
        is_connected: Whether the OAuth connection is active and valid.
        connected_at: Timestamp when the account was successfully connected.
        last_posted_at: Timestamp of the last post published through this account.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
        owner: Related User record.
        posts: Posts published through this account.
    """

    __tablename__ = "social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id_external: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_enc: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    refresh_token_enc: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )
    is_connected: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User", backref="social_accounts", lazy="selectin")
    posts = relationship("Post", back_populates="account", lazy="selectin")
