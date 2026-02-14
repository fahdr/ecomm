"""
Shared SQLAlchemy models for all ecomm SaaS services.

Provides Base, User, ApiKey, Subscription, PlanTier, and SubscriptionStatus.

For Developers:
    Import models from this package in your service's models/__init__.py:
        from ecomm_core.models import Base, User, PlanTier, ApiKey, Subscription
"""

from ecomm_core.models.base import Base
from ecomm_core.models.user import PlanTier, User
from ecomm_core.models.api_key import ApiKey
from ecomm_core.models.subscription import Subscription, SubscriptionStatus

__all__ = [
    "Base",
    "User",
    "PlanTier",
    "ApiKey",
    "Subscription",
    "SubscriptionStatus",
]
