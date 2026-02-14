"""
Test fixtures for the ContentForge backend.

Uses shared test utilities from ecomm_core for database setup and auth helpers.

For Developers:
    Uses a dedicated PostgreSQL database (``contentforge_test``) to isolate from
    other services sharing the main database. Tables are created once at session
    start and truncated before each test.

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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from ecomm_core.testing import register_and_login  # noqa: F401 — re-exported for tests

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base

# Import all models so Base.metadata knows about them
from app.models import *  # noqa: F401,F403

_TEST_DB_NAME = "contentforge_test"
# Build a connection URL pointing at our dedicated test database
_base_url = settings.database_url.rsplit("/", 1)[0]
_TEST_DB_URL = f"{_base_url}/{_TEST_DB_NAME}"
_MAIN_DSN = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
_TEST_DSN = _TEST_DB_URL.replace("postgresql+asyncpg://", "postgresql://")


def _make_engine():
    """Create a fresh NullPool engine pointing at the dedicated test database."""
    return create_async_engine(_TEST_DB_URL, poolclass=NullPool)


def _make_session_factory(engine):
    """Create a session factory for the given engine."""
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


async def _ensure_test_db():
    """Create the contentforge_test database if it does not exist.

    Connects to the main database to issue CREATE DATABASE, since
    PostgreSQL does not support CREATE DATABASE inside a transaction
    on the target database.
    """
    conn = await asyncpg.connect(_MAIN_DSN)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB_NAME
        )
        if not exists:
            await conn.execute(f"CREATE DATABASE {_TEST_DB_NAME} OWNER dropship")
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """
    Create a dedicated test database and all tables once at the start
    of the test session.

    Uses a separate database so tests do not conflict with other services
    sharing the main PostgreSQL instance.
    """
    global _engine, _session_factory

    await _ensure_test_db()

    # Terminate any stale connections to the test database
    try:
        conn = await asyncpg.connect(_TEST_DSN)
        await conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid != pg_backend_pid()
            """
        )
        await conn.close()
    except Exception:
        pass
    await asyncio.sleep(0.3)

    engine = _make_engine()
    try:
        async with engine.begin() as conn:
            # Drop all tables then recreate
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(
                    text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE')
                )
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
    except Exception:
        await engine.dispose()
        raise

    yield

    if _engine:
        await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables():
    """Truncate all tables before each test for data isolation.

    Retries up to 3 times in case another service's test run terminates
    our database connection via pg_terminate_backend.
    """
    table_names = ", ".join(
        f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
    )
    if table_names:
        for attempt in range(3):
            try:
                async with _engine.begin() as conn:
                    await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
                break
            except Exception:
                if attempt == 2:
                    raise
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
