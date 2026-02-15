"""
ShopChat application configuration.

Extends the shared BaseServiceConfig with ShopChat-specific defaults.

For Developers:
    Only add service-specific settings here. Common settings (JWT, DB,
    Redis, Stripe, CORS) are inherited from BaseServiceConfig.

For QA Engineers:
    Override settings via environment variables in test fixtures.
"""

from ecomm_core.config import BaseServiceConfig


class Settings(BaseServiceConfig):
    """
    ShopChat-specific configuration extending shared base.

    Adds LLM Gateway connection settings, store connection defaults,
    and widget configuration on top of the standard service config.

    Attributes:
        service_name: Internal service identifier.
        service_display_name: Human-readable service name.
        service_port: Port for the ShopChat backend.
        cors_origins: Allowed CORS origins.
        stripe_billing_success_url: Redirect URL after successful billing.
        stripe_billing_cancel_url: Redirect URL after canceled billing.
        anthropic_api_key: Direct Anthropic API key (legacy, prefer gateway).
        llm_gateway_url: Base URL for the centralized LLM Gateway service.
        llm_gateway_key: Service authentication key for the LLM Gateway.
        platform_api_url: Base URL for the main dropshipping platform API.
    """

    service_name: str = "shopchat"
    service_display_name: str = "ShopChat"
    service_port: int = 8108
    cors_origins: str = "http://localhost:3108"
    stripe_billing_success_url: str = "http://localhost:3108/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3108/billing?canceled=true"
    anthropic_api_key: str = ""
    llm_gateway_url: str = "http://localhost:8200"
    llm_gateway_key: str = "dev-service-key"
    platform_api_url: str = "http://localhost:8000"


settings = Settings()
