"""
SQLAlchemy models for the SpyDrop service.

Exports all models so Alembic can detect them for migration generation.

For Developers:
    Import models from this package rather than individual files.
    This ensures all models are registered with the SQLAlchemy metadata.

For QA Engineers:
    All models listed here will have corresponding database tables
    created during test setup (via Base.metadata.create_all).
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.subscription import Subscription
from app.models.user import User
from app.models.competitor import Competitor, CompetitorProduct
from app.models.alert import AlertHistory, PriceAlert
from app.models.scan import ScanResult
from app.models.source_match import SourceMatch

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "Competitor",
    "CompetitorProduct",
    "PriceAlert",
    "AlertHistory",
    "ScanResult",
    "SourceMatch",
]
