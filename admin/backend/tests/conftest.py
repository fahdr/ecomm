"""
Test fixtures for the Super Admin Dashboard backend.

Uses a dedicated PostgreSQL schema (``admin_test``) to isolate from
other services sharing the same database. The schema is dropped and
recreated once per session, then tables are truncated between tests.

For Developers:
    - ``create_tables``: Creates the schema and tables once per session.
    - ``truncate_tables``: Truncates all tables before each test.
    - ``db``: Provides an async database session for direct model operations.
    - ``client``: Provides an httpx AsyncClient wired to the FastAPI app.
    - ``auth_headers``: Returns Authorization headers with a valid admin JWT.
    - ``create_admin``: Helper to create an admin user in the database.

For QA Engineers:
    Run tests with: ``pytest`` or ``pytest -v`` from the ``admin/backend`` dir.
    All tests are async and use real database operations against PostgreSQL.

For Project Managers:
    The test configuration uses schema isolation to avoid conflicts with
    other services sharing the same database.
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
from app.models import admin_user, health_snapshot  # noqa: F401
from app.models.admin_user import AdminUser
from app.services.auth_service import create_access_token, hash_password

_SCHEMA = "admin_test"
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
    Create the ``admin_test`` schema and all tables once at the
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
                  AND query LIKE '%admin_test%'
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
    """Truncate all tables before each test for data isolation."""
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


async def create_admin(
    db: AsyncSession,
    email: str = "admin@example.com",
    password: str = "securepassword123",
    role: str = "super_admin",
    is_active: bool = True,
) -> AdminUser:
    """
    Helper to create an admin user directly in the database.

    Args:
        db: The async database session.
        email: The admin's email address.
        password: The plaintext password (will be hashed).
        role: The admin role (super_admin, admin, viewer).
        is_active: Whether the account is active.

    Returns:
        The created AdminUser ORM object with all fields populated.
    """
    admin = AdminUser(
        email=email,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    await db.commit()
    return admin


@pytest_asyncio.fixture
async def auth_headers(db: AsyncSession) -> dict:
    """
    Provide Authorization headers with a valid admin JWT.

    Creates a super_admin user and generates a JWT for it.

    Args:
        db: The async database session.

    Returns:
        Dict with the Authorization header containing a Bearer token.
    """
    admin = await create_admin(db)
    token = create_access_token({"sub": str(admin.id)})
    return {"Authorization": f"Bearer {token}"}
