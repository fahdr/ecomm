"""
Shared Pydantic schemas for all ecomm SaaS services.

Provides authentication, billing, and common DTOs.
"""

from ecomm_core.schemas.auth import (
    LoginRequest,
    MessageResponse,
    ProvisionRequest,
    ProvisionResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from ecomm_core.schemas.billing import (
    BillingOverviewResponse,
    CheckoutSessionResponse,
    CreateCheckoutRequest,
    PlanInfo,
    PortalSessionResponse,
    SubscriptionResponse,
    UsageMetric,
    UsageResponse,
)

__all__ = [
    "LoginRequest",
    "MessageResponse",
    "ProvisionRequest",
    "ProvisionResponse",
    "RefreshRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "BillingOverviewResponse",
    "CheckoutSessionResponse",
    "CreateCheckoutRequest",
    "PlanInfo",
    "PortalSessionResponse",
    "SubscriptionResponse",
    "UsageMetric",
    "UsageResponse",
]
