"""
Test fixtures for the LLM Gateway.

Uses a dedicated PostgreSQL schema (``llm_gateway_test``) to isolate from
other services sharing the same database. The schema is dropped and
recreated once per session, then tables are truncated between tests.

For Developers:
    Uses a separate test schema. Tables are created once per session and
    truncated between tests for full isolation. Each setup uses raw asyncpg
    to terminate stale connections, then a fresh SQLAlchemy engine for DDL.
    The ``client`` fixture provides an httpx.AsyncClient configured
    for the FastAPI app.

For QA Engineers:
    Run tests with: ``pytest`` or ``pytest -v`` for verbose output.
"""

import asyncio
from collections.abc import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import provider_config, customer_override, usage_log  # noqa: F401

_SCHEMA = "llm_gateway_test"
_ASYNCPG_DSN = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def _make_engine():
    """Create a fresh NullPool engine with search_path set to the test schema.

    Returns:
        AsyncEngine: A new async engine using NullPool with the search_path
        configured to prefer the test schema over public.
    """
    eng = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    @event.listens_for(eng.sync_engine, "connect")
    def set_search_path(dbapi_conn, connection_record):
        """Set the search_path on every new raw connection."""
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET search_path TO {_SCHEMA}")
        cursor.close()

    return eng


def _make_session_factory(eng):
    """Create a session factory for the given engine.

    Args:
        eng: The async engine to bind sessions to.

    Returns:
        async_sessionmaker for creating test database sessions.
    """
    return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)


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
    Create the ``llm_gateway_test`` schema and all tables once at the
    start of the test session.

    Uses a dedicated schema so tests do not conflict with other services
    sharing the same PostgreSQL database.
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
                  AND query LIKE '%llm_gateway_test%'
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

    # Step 3: Create tables with a fresh engine
    last_error = None
    for attempt in range(3):
        eng = _make_engine()
        try:
            async with eng.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            _engine = eng
            _session_factory = _make_session_factory(eng)

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
            await eng.dispose()
            await asyncio.sleep(0.5)
    else:
        raise RuntimeError(f"Failed to create tables after 3 attempts: {last_error}")

    yield

    if _engine:
        await _engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables():
    """Truncate all tables before each test for data isolation.

    Also resets Redis caches and rate limiter state to avoid stale
    data between tests.
    """
    # Reset Redis singletons and flush cache
    from app.services import cache_service, rate_limit_service
    cache_service._redis_client = None
    rate_limit_service._redis_client = None

    import redis.asyncio as aioredis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.flushdb()
        await r.aclose()
    except Exception:
        pass

    # Dispose the app's engine to prevent pooled connections from interfering
    from app.database import engine as app_engine
    await app_engine.dispose()

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


@pytest.fixture
def auth_headers() -> dict:
    """Provide authenticated headers with the service key."""
    return {"X-Service-Key": settings.service_key}
