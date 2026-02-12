"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables with sensible defaults
for local development. Each service has its own configuration.

For Developers:
    All config is loaded from environment variables. Add new settings as
    class attributes with type hints and defaults. Access via `settings` singleton.

For QA Engineers:
    Override settings via environment variables in test fixtures or .env files.
    Mock mode is active when stripe_secret_key is empty.

For Project Managers:
    Configuration controls database connections, API keys, billing integration,
    and service identity. See .env.example for all available options.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Service configuration loaded from environment variables.

    Attributes:
        service_name: Internal service identifier (e.g., 'trendscout').
        service_display_name: Human-readable product name (e.g., 'TrendScout').
        service_port: Port the backend listens on.
        debug: Enable debug mode with SQL logging.
        database_url: Async PostgreSQL connection string.
        database_url_sync: Sync PostgreSQL connection string (for Alembic).
        redis_url: Redis connection URL for caching.
        celery_broker_url: Redis URL for Celery task broker.
        celery_result_backend: Redis URL for Celery results.
        jwt_secret_key: Secret key for signing JWT tokens.
        jwt_algorithm: Algorithm for JWT signing (default HS256).
        jwt_access_token_expire_minutes: Access token TTL in minutes.
        jwt_refresh_token_expire_days: Refresh token TTL in days.
        cors_origins: Allowed CORS origins as comma-separated string.
        stripe_secret_key: Stripe API secret key (empty = mock mode).
        stripe_webhook_secret: Stripe webhook signing secret.
        stripe_free_price_id: Stripe Price ID for free tier.
        stripe_pro_price_id: Stripe Price ID for pro tier.
        stripe_enterprise_price_id: Stripe Price ID for enterprise tier.
        stripe_billing_success_url: Redirect URL after successful subscription.
        stripe_billing_cancel_url: Redirect URL if subscription cancelled.
        anthropic_api_key: Anthropic API key for Claude AI features.
    """

    # Service identity
    service_name: str = "spydrop"
    service_display_name: str = "SpyDrop"
    service_port: int = 8105

    # Debug
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://spydrop:spydrop_dev@localhost:5432/spydrop"
    database_url_sync: str = "postgresql://spydrop:spydrop_dev@localhost:5432/spydrop"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3105"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_free_price_id: str = ""
    stripe_pro_price_id: str = ""
    stripe_enterprise_price_id: str = ""
    stripe_billing_success_url: str = "http://localhost:3105/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3105/billing?canceled=true"

    # AI
    anthropic_api_key: str = ""

    model_config = {"env_prefix": "", "case_sensitive": False}

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
