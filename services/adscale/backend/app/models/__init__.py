"""
SQLAlchemy models for the AdScale service.

Exports all models so Alembic can detect them for migration generation.

For Developers:
    Import models here after creating new model files so that Alembic
    auto-generates the correct migration scripts.

For QA Engineers:
    All models listed here will have corresponding database tables.
    Verify that migrations are up to date before running tests.
"""

from app.models.ad_account import AdAccount
from app.models.ad_creative import AdCreative
from app.models.ad_group import AdGroup
from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.campaign import Campaign
from app.models.campaign_metrics import CampaignMetrics
from app.models.optimization_rule import OptimizationRule
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "AdAccount",
    "Campaign",
    "AdGroup",
    "AdCreative",
    "CampaignMetrics",
    "OptimizationRule",
]
