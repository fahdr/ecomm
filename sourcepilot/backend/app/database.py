"""
Async database engine and session factory for SourcePilot.

Uses shared helpers from ecomm_core for consistent setup across services.
All queries are scoped to the ``sourcepilot`` schema via the PostgreSQL
``search_path`` connection argument.

For Developers:
    Use ``get_db()`` as a FastAPI dependency to get an async session.
    Sessions auto-commit on success and rollback on exception.

For QA Engineers:
    Tests use a separate engine with NullPool and ``sourcepilot_test`` schema.
    See tests/conftest.py for the test database setup.

For Project Managers:
    This module manages all database connections. The async driver
    (asyncpg) provides high-performance non-blocking database access.
"""

from sqlalchemy.ext.asyncio import create_async_engine

from ecomm_core.db import create_get_db, create_session_factory

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"server_settings": {"search_path": "sourcepilot,public"}},
)
async_session_factory = create_session_factory(engine)
get_db = create_get_db(async_session_factory)
