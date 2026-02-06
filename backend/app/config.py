"""Application configuration module.

Uses pydantic-settings to load configuration from environment variables
(provided by the devcontainer's docker-compose.yml) with sensible defaults
for local development. In production, all secrets and URLs should be
overridden via environment variables or a .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the backend application.

    Attributes:
        app_name: Display name used in FastAPI docs and metadata.
        debug: Enables SQLAlchemy query logging when True.
        database_url: Async PostgreSQL connection string (asyncpg driver).
        database_url_sync: Sync PostgreSQL connection string (used by Alembic CLI).
        redis_url: Redis URL for general caching.
        celery_broker_url: Redis URL used as the Celery message broker.
        celery_result_backend: Redis URL used to store Celery task results.
        jwt_secret_key: Secret key for signing JWT tokens. Must be changed in production.
        jwt_algorithm: Algorithm used for JWT encoding/decoding.
        jwt_access_token_expire_minutes: Lifetime of access tokens in minutes.
        jwt_refresh_token_expire_days: Lifetime of refresh tokens in days.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    app_name: str = "Dropshipping Platform API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping"
    database_url_sync: str = "postgresql://dropship:dropship_dev@db:5432/dropshipping"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = "http://localhost:3001/checkout/success?session_id={CHECKOUT_SESSION_ID}"
    stripe_cancel_url: str = "http://localhost:3001/cart"

    # JWT
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7


settings = Settings()
