"""
SQLAlchemy models for the RankPilot service.

Exports all models so Alembic can detect them for migration generation.

For Developers:
    Import all models here to ensure they are registered with the
    SQLAlchemy metadata. This is required for Alembic to auto-generate
    migrations correctly.

For QA Engineers:
    All models listed here should have corresponding database tables
    after running `alembic upgrade head`.
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.blog_post import BlogPost
from app.models.keyword import KeywordTracking
from app.models.keyword_history import KeywordHistory
from app.models.schema_config import SchemaConfig
from app.models.seo_audit import SeoAudit
from app.models.site import Site
from app.models.store_connection import StoreConnection
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "Site",
    "BlogPost",
    "KeywordTracking",
    "KeywordHistory",
    "SeoAudit",
    "SchemaConfig",
    "StoreConnection",
]
