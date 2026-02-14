"""
Base configuration class for all ecomm SaaS services.

Each service extends BaseServiceConfig with service-specific settings.
Common settings (database, Redis, JWT, Stripe, CORS) are defined here.

For Developers:
    Subclass BaseServiceConfig in your service's config.py:
        class Settings(BaseServiceConfig):
            service_name: str = "trendscout"
    The `settings` singleton is NOT created here — each service creates its own.

For QA Engineers:
    Override settings via environment variables or .env files.
    Mock mode is active when stripe_secret_key is empty.
"""

from pydantic_settings import BaseSettings


class BaseServiceConfig(BaseSettings):
    """
    Base configuration shared by all ecomm SaaS services.

    Attributes:
        service_name: Internal identifier (e.g., 'trendscout').
        service_display_name: Human-readable name (e.g., 'TrendScout').
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
        llm_gateway_url: URL of the centralized LLM gateway service.
        llm_gateway_key: Service authentication key for LLM gateway.
    """

    # Service identity
    service_name: str = "service"
    service_display_name: str = "Service"
    service_port: int = 8000

    # Debug
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/db"
    database_url_sync: str = "postgresql://user:pass@localhost:5432/db"

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
    cors_origins: str = "http://localhost:3000"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_free_price_id: str = ""
    stripe_pro_price_id: str = ""
    stripe_enterprise_price_id: str = ""
    stripe_billing_success_url: str = "http://localhost:3000/billing?success=true"
    stripe_billing_cancel_url: str = "http://localhost:3000/billing?canceled=true"

    # LLM Gateway
    llm_gateway_url: str = "http://localhost:8200"
    llm_gateway_key: str = ""

    # Platform Bridge (inter-service event delivery)
    platform_webhook_secret: str = "dev-platform-bridge-secret"

    model_config = {"env_prefix": "", "case_sensitive": False}

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
