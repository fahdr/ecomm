"""
Test fixtures for the FlowSend backend.

Uses shared test utilities from ecomm_core for database setup and auth helpers.

For Developers:
    Uses a dedicated PostgreSQL schema (``flowsend_test``) to isolate from
    other services sharing the same database. The schema is dropped and
    recreated once per session, then tables are truncated between tests.

    The ``client`` fixture provides an httpx.AsyncClient configured
    for the FastAPI app with dependency overrides.

For QA Engineers:
    Run tests with: ``pytest`` or ``pytest -v`` for verbose output.
    Each test runs in complete isolation (tables truncated between tests).
"""

import asyncio
from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from ecomm_core.testing import register_and_login  # noqa: F401 -- re-exported for tests

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base

# Import all models so Base.metadata knows about them
from app.models import *  # noqa: F401,F403

_SCHEMA = "flowsend_test"
_ASYNCPG_DSN = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def _make_engine():
    """Create a fresh NullPool engine with search_path set to the test schema.

    Returns:
        AsyncEngine: A new async engine using NullPool with the search_path
        configured to prefer the test schema over public.
    """
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_search_path(dbapi_conn, connection_record):
        """Set the search_path on every new raw connection so all SQL
        operations target the ``flowsend_test`` schema instead of
        ``public``.
        """
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET search_path TO {_SCHEMA}")
        cursor.close()

    return engine


def _make_session_factory(engine):
    """Create a session factory for the given engine.

    Args:
        engine: The async engine to bind sessions to.

    Returns:
        async_sessionmaker for creating test database sessions.
    """
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Module-level references that get set during create_tables
_engine = None
_session_factory = None


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """
    Create the ``flowsend_test`` schema and all tables once at the
    start of the test session.

    Uses a dedicated schema so tests do not conflict with other services
    sharing the same PostgreSQL database.

    Step 1: Terminate stale connections from prior test runs.
    Step 2: Drop and recreate the test schema via raw asyncpg.
    Step 3: Create all tables with a fresh SQLAlchemy engine.
    """
    global _engine, _session_factory

    # Step 1: Terminate stale connections from prior test runs
    for attempt in range(3):
        try:
            term_conn = await asyncpg.connect(_ASYNCPG_DSN)
            await term_conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid != pg_backend_pid()
                  AND query LIKE '%flowsend_test%'
                """
            )
            await term_conn.close()
            break
        except Exception:
            await asyncio.sleep(0.3)

    await asyncio.sleep(0.3)

    # Step 2: Drop and recreate the schema via raw asyncpg
    for attempt in range(5):
        try:
            conn = await asyncpg.connect(_ASYNCPG_DSN)
            await conn.execute(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE")
            await conn.execute(f"CREATE SCHEMA {_SCHEMA}")
            await conn.close()
            break
        except Exception:
            await asyncio.sleep(0.5)
    else:
        raise RuntimeError(f"Failed to create schema {_SCHEMA}")

    # Step 3: Create tables with a fresh engine (search_path = flowsend_test only)
    last_error = None
    for attempt in range(3):
        engine = _make_engine()
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            _engine = engine
            _session_factory = _make_session_factory(engine)

            # Wire up the dependency override
            async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
                async with _session_factory() as session:
                    try:
                        yield session
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

            app.dependency_overrides[get_db] = _override_get_db
            break
        except Exception as exc:
            last_error = exc
            await engine.dispose()
            await asyncio.sleep(0.5)
    else:
        raise RuntimeError(f"Failed to create tables after 3 attempts: {last_error}")

    yield

    if _engine:
        await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables():
    """Truncate all tables before each test for data isolation.

    Uses unqualified table names; the search_path resolves each table
    within the flowsend_test schema. Retries up to 3 times on transient
    connection errors caused by concurrent test suites sharing the DB.
    """
    table_names = ", ".join(
        f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
    )
    if not table_names:
        yield
        return

    for attempt in range(3):
        try:
            async with _engine.begin() as conn:
                await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
            break
        except Exception:
            await _engine.dispose()
            await asyncio.sleep(0.3)
    yield


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests."""
    async with _session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Provide authenticated headers for a test user."""
    return await register_and_login(client)
