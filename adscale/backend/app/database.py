"""
Async database engine and session factory for AdScale.

Uses shared helpers from ecomm_core for consistent setup across services.

For Developers:
    Use ``get_db()`` as a FastAPI dependency to get an async session.

For QA Engineers:
    Tests use a separate engine with NullPool. See tests/conftest.py.
"""

from sqlalchemy.ext.asyncio import create_async_engine

from ecomm_core.db import create_get_db, create_session_factory

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"server_settings": {"search_path": "adscale,public"}},
)
async_session_factory = create_session_factory(engine)
get_db = create_get_db(async_session_factory)
