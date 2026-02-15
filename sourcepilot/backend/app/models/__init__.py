"""
SQLAlchemy models for the SourcePilot service.

Re-exports shared models from the template and includes service-specific models.
All models must be imported here for Alembic migration detection.

For Developers:
    Import new models here after creation so they are registered with
    the Base metadata.
"""

from app.models.base import Base
from app.models.user import User, PlanTier
from app.models.api_key import ApiKey
from app.models.subscription import Subscription
from app.models.import_job import ImportJob, ImportJobStatus, ImportSource
from app.models.supplier_account import SupplierAccount
from app.models.product_cache import ProductCache
from app.models.import_history import ImportHistory
from app.models.price_watch import PriceWatch
from app.models.store_connection import StoreConnection

__all__ = [
    "Base",
    "User",
    "PlanTier",
    "ApiKey",
    "Subscription",
    "ImportJob",
    "ImportJobStatus",
    "ImportSource",
    "SupplierAccount",
    "ProductCache",
    "ImportHistory",
    "PriceWatch",
    "StoreConnection",
]
