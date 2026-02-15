"""
Test fixtures for the ShopChat backend.

Uses shared test utilities from ecomm_core for database setup and auth helpers.

For Developers:
    Uses a dedicated ``shopchat_test`` database for isolation from other
    services sharing the same PostgreSQL server. Tables are created once at
    session start and truncated before each test.

    The ``client`` fixture provides an httpx.AsyncClient configured for the
    FastAPI app with dependency overrides pointing to the test database.

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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from ecomm_core.testing import register_and_login

from app.config import settings
from app.database import get_db
from app.models.base import Base

# Force all models to be registered with Base.metadata
import app.models  # noqa: F401

# Import FastAPI app after models so metadata is complete
from app.main import app as fastapi_app  # noqa: E402

# Use a dedicated test database to avoid conflicts with other services
_TEST_DB_NAME = "shopchat_test"
_BASE_DSN = settings.database_url.rsplit("/", 1)[0]  # strip db name
_TEST_DB_URL = f"{_BASE_DSN}/{_TEST_DB_NAME}"
_ASYNCPG_DSN = _TEST_DB_URL.replace("postgresql+asyncpg://", "postgresql://")
_ADMIN_DSN = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def _make_engine():
    """Create a fresh NullPool engine pointing to the test database."""
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


async def _ensure_test_database():
    """
    Ensure the dedicated test database exists.

    Connects to the default database and creates the test database
    if it does not already exist.
    """
    try:
        conn = await asyncpg.connect(_ADMIN_DSN)
        row = await conn.fetchrow(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB_NAME
        )
        if not row:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
        await conn.close()
    except Exception:
        pass  # Database may already exist or be in use


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """
    Create all tables once at the start of the test session.

    Ensures the test database exists, terminates competing connections,
    drops the entire public schema (avoiding inter-table deadlocks),
    and creates all tables fresh.
    Retries up to 5 times to handle race conditions.
    """
    global _engine, _session_factory

    # Ensure the test database exists
    await _ensure_test_database()

    last_exc = None
    for attempt in range(5):
        # Terminate ALL other connections to the test database
        try:
            conn = await asyncpg.connect(_ASYNCPG_DSN)
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
                # Drop and recreate the entire public schema to avoid
                # inter-table deadlocks from circular FK references
                await conn.execute(text("DROP SCHEMA public CASCADE"))
                await conn.execute(text("CREATE SCHEMA public"))
                # Re-create enum types and all tables
                await conn.run_sync(Base.metadata.create_all)

            _engine = engine
            _session_factory = _make_session_factory(engine)

            # Wire up the dependency override to use the test database
            async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
                async with _session_factory() as session:
                    try:
                        yield session
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise

            fastapi_app.dependency_overrides[get_db] = _override_get_db
            break
        except Exception as exc:
            last_exc = exc
            await engine.dispose()
    else:
        raise RuntimeError(
            f"Failed to set up test tables after 5 attempts. Last error: {last_exc}"
        )

    yield

    if _engine:
        await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables():
    """Truncate all tables before each test for data isolation."""
    async with _engine.begin() as conn:
        table_names = ", ".join(
            f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
        )
        if table_names:
            await conn.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    yield


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests."""
    async with _session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient for API testing."""
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Provide authenticated headers for a test user."""
    return await register_and_login(client)
