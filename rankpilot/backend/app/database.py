"""
Async database engine and session factory for RankPilot.

Uses shared helpers from ecomm_core for consistent setup across services.

For Developers:
    Use ``get_db()`` as a FastAPI dependency to get an async session.

For QA Engineers:
    Tests use a separate engine with NullPool. See tests/conftest.py.
"""

from ecomm_core.db import create_db_engine, create_get_db, create_session_factory

from app.config import settings

engine = create_db_engine(settings.database_url, echo=settings.debug)
async_session_factory = create_session_factory(engine)
get_db = create_get_db(async_session_factory)
