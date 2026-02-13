"""Synchronous database session factory for Celery tasks.

Celery workers run in a synchronous event loop, so they cannot use the
async SQLAlchemy engine from ``app.database``. This module provides a
synchronous session factory backed by ``settings.database_url_sync``.

**For Developers:**
    Import ``SyncSessionFactory`` in task modules to get a sync session::

        from app.tasks.db import SyncSessionFactory
        session = SyncSessionFactory()
        try:
            # ... query / mutate ...
            session.commit()
        finally:
            session.close()

    The engine uses ``pool_pre_ping=True`` for connection health checks,
    which prevents stale-connection errors in long-running workers.

**For QA Engineers:**
    This factory is only used inside Celery tasks. The API layer
    continues to use the async engine from ``app.database``. Tests can
    mock ``SyncSessionFactory`` to inject controlled state.

**For Project Managers:**
    This is infrastructure that allows background tasks to access the
    same database as the main API without async/sync conflicts.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

_sync_engine = create_engine(
    settings.database_url_sync,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SyncSessionFactory = sessionmaker(bind=_sync_engine)
