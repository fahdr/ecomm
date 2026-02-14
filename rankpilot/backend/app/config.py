"""
RankPilot application configuration.

Extends the shared BaseServiceConfig with RankPilot-specific defaults.

For Developers:
    Only add service-specific settings here. Common settings (JWT, DB,
    Redis, Stripe, CORS) are inherited from BaseServiceConfig.

For QA Engineers:
    Override settings via environment variables in test fixtures.
"""

from ecomm_core.config import BaseServiceConfig


class Settings(BaseServiceConfig):
    """RankPilot-specific configuration extending shared base."""

    service_name: str = "rankpilot"
    service_display_name: str = "RankPilot"
    service_port: int = 8103
    cors_origins: str = "http://localhost:3103"
    stripe_billing_success_url: str = "http://localhost:3103/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3103/billing?canceled=true"
    anthropic_api_key: str = ""


settings = Settings()
