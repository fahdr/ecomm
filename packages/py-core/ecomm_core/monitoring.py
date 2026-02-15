"""
Sentry error tracking integration for all ecomm SaaS services.

Provides a single ``init_sentry()`` function that configures Sentry SDK
with FastAPI, SQLAlchemy, Celery, and Redis integrations. When no DSN is
provided (empty string or None), the call is a no-op so local development
runs without Sentry overhead.

For Developers:
    Call ``init_sentry(service_name, dsn, environment)`` early in your
    service's startup (before the FastAPI app is created or in the lifespan
    handler). The function is idempotent — calling it twice is safe.

For QA Engineers:
    Verify that passing an empty DSN does not raise and does not install
    any Sentry hooks. Verify that a valid DSN configures Sentry without
    errors.

For Project Managers:
    Sentry integration captures unhandled exceptions, slow transactions,
    and performance profiles in production. Each service identifies itself
    via ``server_name`` so errors can be filtered per service in the Sentry
    dashboard.

For End Users:
    This module runs behind the scenes. It does not affect API behavior
    or response formats. It helps the engineering team detect and fix
    errors faster.
"""

import logging

logger = logging.getLogger(__name__)


def init_sentry(
    service_name: str,
    dsn: str,
    environment: str = "development",
) -> None:
    """
    Initialize Sentry error tracking for a service.

    Configures the Sentry SDK with integrations for FastAPI, SQLAlchemy,
    Celery, and Redis. In production, traces and profiles are sampled at
    10% to reduce overhead. In non-production environments, all traces
    are captured and profiling is disabled.

    If ``dsn`` is falsy (empty string or None), the function returns
    immediately without initializing Sentry — this is the expected
    behavior for local development.

    Args:
        service_name: Identifier for this service (e.g. 'trendscout').
            Appears as ``server_name`` in Sentry events.
        dsn: The Sentry DSN (Data Source Name) string. An empty string
            disables Sentry entirely.
        environment: Deployment environment label (e.g. 'production',
            'staging', 'development'). Affects sampling rates.

    Returns:
        None
    """
    if not dsn:
        logger.debug(
            "Sentry DSN not configured for %s — skipping initialization",
            service_name,
        )
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError as exc:
        logger.warning(
            "sentry-sdk is not installed — Sentry will not be initialized "
            "for %s: %s",
            service_name,
            exc,
        )
        return

    is_production = environment == "production"

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1 if is_production else 1.0,
        profiles_sample_rate=0.1 if is_production else 0.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        send_default_pii=False,
        server_name=service_name,
    )

    logger.info(
        "Sentry initialized for %s (environment=%s, traces=%.0f%%, profiles=%.0f%%)",
        service_name,
        environment,
        (0.1 if is_production else 1.0) * 100,
        (0.1 if is_production else 0.0) * 100,
    )
