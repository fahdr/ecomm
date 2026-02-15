"""
SpyDrop application configuration.

Extends the shared BaseServiceConfig with SpyDrop-specific defaults.

For Developers:
    Only add service-specific settings here. Common settings (JWT, DB,
    Redis, Stripe, CORS) are inherited from BaseServiceConfig.

For QA Engineers:
    Override settings via environment variables in test fixtures.
"""

from ecomm_core.config import BaseServiceConfig


class Settings(BaseServiceConfig):
    """SpyDrop-specific configuration extending shared base."""

    service_name: str = "spydrop"
    service_display_name: str = "SpyDrop"
    service_port: int = 8105
    cors_origins: str = "http://localhost:3105"
    stripe_billing_success_url: str = "http://localhost:3105/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3105/billing?canceled=true"
    anthropic_api_key: str = ""


settings = Settings()
