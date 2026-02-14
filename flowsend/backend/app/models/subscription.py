"""
Re-export shared Subscription model from ecomm_core.

For Developers:
    Import Subscription and SubscriptionStatus from here or ecomm_core.models.
"""

from ecomm_core.models.subscription import Subscription, SubscriptionStatus

__all__ = ["Subscription", "SubscriptionStatus"]
