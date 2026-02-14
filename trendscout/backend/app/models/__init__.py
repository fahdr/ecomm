"""
SQLAlchemy models for the TrendScout service.

Re-exports shared models from ecomm_core and includes service-specific models.
All models must be imported here for Alembic migration detection.

For Developers:
    Import new models here after creation so they are registered with
    the Base metadata.
"""

from app.models.base import Base
from app.models.user import User, PlanTier
from app.models.api_key import ApiKey
from app.models.subscription import Subscription
from app.models.research import ResearchResult, ResearchRun
from app.models.source_config import SourceConfig
from app.models.store_connection import StoreConnection
from app.models.watchlist import WatchlistItem

__all__ = [
    "Base",
    "User",
    "PlanTier",
    "ApiKey",
    "Subscription",
    "ResearchRun",
    "ResearchResult",
    "WatchlistItem",
    "SourceConfig",
    "StoreConnection",
]
