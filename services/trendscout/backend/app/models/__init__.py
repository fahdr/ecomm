"""
SQLAlchemy models for the TrendScout service.

Exports all models so Alembic can detect them for migration generation.

For Developers:
    Import new models here after creation so they are registered with
    the Base metadata. Alembic relies on this import chain to
    auto-generate migrations.

For QA Engineers:
    All models listed here will have their tables created in the test
    database via conftest.py's setup_db fixture.
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.research import ResearchResult, ResearchRun
from app.models.source_config import SourceConfig
from app.models.subscription import Subscription
from app.models.user import User
from app.models.watchlist import WatchlistItem

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "ResearchRun",
    "ResearchResult",
    "WatchlistItem",
    "SourceConfig",
]
