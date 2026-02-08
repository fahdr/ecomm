"""Shared pytest fixtures for backend tests.

Provides reusable fixtures including an async HTTP client, database session
management with per-test isolation, and authentication helpers.

**For Developers:**
    The ``client`` fixture overrides the ``get_db`` dependency so each test
    uses the test engine. Data is truncated before each test for isolation.
    Tables are created by Alembic migrations (run ``alembic upgrade head``
    before running the test suite).

**For QA Engineers:**
    Tests run against an in-process FastAPI app (no real server). The
    database is real (PostgreSQL) but data is cleaned between tests.
"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db
from app.main import app

# NullPool avoids connection-sharing issues between async fixtures.
test_engine = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
TestSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def client():
    """Yield an async HTTP client wired to the FastAPI app with DB override.

    Disposes engine pools and truncates all tables before yielding to
    ensure test isolation. Uses a dedicated cleanup engine and terminates
    stale connections to avoid TRUNCATE deadlocks across test runs.

    Overrides the ``get_db`` dependency so each request uses a fresh
    database session from the test engine.

    Yields:
        AsyncClient: An httpx client that sends requests to the FastAPI app.
    """
    # Dispose engine pools to release any lingering connections from the
    # previous test that could block the TRUNCATE AccessExclusiveLock.
    from app.database import engine as app_engine
    await app_engine.dispose()
    await test_engine.dispose()

    # Brief pause to let async connection cleanup complete.
    await asyncio.sleep(0.1)

    # Use a dedicated one-shot engine for cleanup so it never conflicts
    # with lingering test_engine connections.
    cleanup_engine = create_async_engine(
        settings.database_url, echo=False, poolclass=NullPool
    )
    try:
        # Terminate any stale connections from previous test runs that
        # could hold locks and block TRUNCATE.
        async with cleanup_engine.begin() as conn:
            await conn.execute(text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = current_database() "
                "AND pid != pg_backend_pid() "
                "AND state != 'active'"
            ))

        # Now truncate all tables for test isolation.
        async with cleanup_engine.begin() as conn:
            table_names = ", ".join(
                table.name for table in Base.metadata.sorted_tables
            )
            if table_names:
                await conn.execute(text(f"TRUNCATE {table_names} CASCADE"))
    finally:
        await cleanup_engine.dispose()

    async def override_get_db():
        """Yield a test database session.

        Yields:
            AsyncSession: A SQLAlchemy async session from the test engine.
        """
        async with TestSessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
