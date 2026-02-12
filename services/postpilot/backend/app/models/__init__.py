"""
SQLAlchemy models for the PostPilot service.

Exports all models so Alembic can detect them for migration generation.
This includes both template models (User, Subscription, ApiKey) and
feature-specific models (SocialAccount, Post, PostMetrics, ContentQueue).

For Developers:
    Import new models here after creating them so Alembic autogenerate
    can detect the table definitions and create migrations.
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.content_queue import ContentQueue
from app.models.post import Post
from app.models.post_metrics import PostMetrics
from app.models.social_account import SocialAccount
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "SocialAccount",
    "Post",
    "PostMetrics",
    "ContentQueue",
]
