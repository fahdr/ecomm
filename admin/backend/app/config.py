"""
Configuration for the Super Admin Dashboard backend.

Centralizes all environment variables and defaults for the admin service.
Uses pydantic-settings to load configuration from environment variables
with the ``ADMIN_`` prefix.

For Developers:
    Settings are loaded from environment variables prefixed with ``ADMIN_``.
    The ``service_urls`` dict maps every managed service to its base URL,
    used by the health monitor to ping each service.

For QA Engineers:
    The service runs on port 8300 by default.
    The ``admin_secret_key`` is used for JWT signing and must be kept secret.
    The ``llm_gateway_key`` authenticates requests to the LLM Gateway.

For Project Managers:
    This configuration file defines how the admin dashboard connects to
    every other service in the platform. Adding a new service only requires
    adding its URL to the ``service_urls`` dict.

For End Users:
    This file is part of the platform's internal infrastructure and has
    no direct impact on the customer-facing experience.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Admin dashboard configuration loaded from environment variables.

    Attributes:
        service_name: Identifier for health checks and logging.
        service_port: HTTP port the admin service listens on.
        database_url: Async PostgreSQL connection string (shared database).
        redis_url: Redis connection for caching and session management.
        llm_gateway_url: Base URL of the LLM Gateway microservice.
        llm_gateway_key: Shared secret for authenticating with the LLM Gateway.
        admin_secret_key: Secret key used for signing admin JWT tokens.
        admin_token_expire_minutes: JWT token expiration time in minutes.
        debug: Enable verbose SQL logging and debug endpoints.
        service_urls: Mapping of service names to their health-check base URLs.
    """

    service_name: str = "admin"
    service_port: int = 8300
    database_url: str = (
        "postgresql+asyncpg://dropship:dropship_dev@db:5432/dropshipping"
    )
    redis_url: str = "redis://redis:6379/4"
    llm_gateway_url: str = "http://localhost:8200"
    llm_gateway_key: str = "dev-gateway-key"
    admin_secret_key: str = "admin-super-secret-key-change-in-production"
    admin_token_expire_minutes: int = 480
    debug: bool = False

    service_urls: dict[str, str] = {
        "llm-gateway": "http://localhost:8200",
        "trendscout": "http://localhost:8101",
        "contentforge": "http://localhost:8102",
        "priceoptimizer": "http://localhost:8103",
        "reviewsentinel": "http://localhost:8104",
        "inventoryiq": "http://localhost:8105",
        "customerinsight": "http://localhost:8106",
        "adcreator": "http://localhost:8107",
        "competitorradar": "http://localhost:8108",
    }

    model_config = {"env_prefix": "ADMIN_"}


settings = Settings()
