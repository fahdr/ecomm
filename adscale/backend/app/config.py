"""
AdScale application configuration.

Extends the shared BaseServiceConfig with AdScale-specific defaults.

For Developers:
    Only add service-specific settings here. Common settings (JWT, DB,
    Redis, Stripe, CORS) are inherited from BaseServiceConfig.

For QA Engineers:
    Override settings via environment variables in test fixtures.
"""

from ecomm_core.config import BaseServiceConfig


class Settings(BaseServiceConfig):
    """
    AdScale-specific configuration extending shared base.

    Adds LLM Gateway connection settings for AI-powered ad copy generation
    and campaign optimization, plus a legacy Anthropic API key for direct
    Claude access.

    For Developers:
        ``llm_gateway_url`` points to the centralized LLM Gateway service.
        ``llm_gateway_key`` is the service-to-service auth key sent as
        ``X-Service-Key`` header.  Override via environment variables.

    For QA Engineers:
        In tests, these default to localhost values.  Mock the gateway
        in integration tests to avoid real HTTP calls.
    """

    service_name: str = "adscale"
    service_display_name: str = "AdScale"
    service_port: int = 8107
    cors_origins: str = "http://localhost:3107"
    stripe_billing_success_url: str = "http://localhost:3107/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3107/billing?canceled=true"
    anthropic_api_key: str = ""

    # LLM Gateway settings
    llm_gateway_url: str = "http://localhost:8200"
    llm_gateway_key: str = "dev-gateway-key"


settings = Settings()
