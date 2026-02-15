"""
ContentForge application configuration.

Extends the shared BaseServiceConfig with ContentForge-specific defaults.

For Developers:
    Only add service-specific settings here. Common settings (JWT, DB,
    Redis, Stripe, CORS) are inherited from BaseServiceConfig.

For QA Engineers:
    Override settings via environment variables in test fixtures.
"""

from ecomm_core.config import BaseServiceConfig


class Settings(BaseServiceConfig):
    """ContentForge-specific configuration extending shared base."""

    service_name: str = "contentforge"
    service_display_name: str = "ContentForge"
    service_port: int = 8102
    cors_origins: str = "http://localhost:3102"
    stripe_billing_success_url: str = "http://localhost:3102/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3102/billing?canceled=true"
    anthropic_api_key: str = ""


settings = Settings()
