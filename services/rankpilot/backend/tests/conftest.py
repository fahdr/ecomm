"""
Test fixtures for the RankPilot backend.

Provides async test client, database session, and helper functions
for creating test users and authenticated clients.

For Developers:
    Uses a separate test database. Tables are truncated between tests.
    The `client` fixture provides an httpx.AsyncClient configured
    for the FastAPI app. Use `auth_client` for authenticated requests.

For QA Engineers:
    Run tests with: `pytest` or `pytest -v` for verbose output.
    All tests run in mock Stripe mode (no real API calls).
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AST, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base

# Test database URL — uses the same DB but with NullPool for test isolation
TEST_DATABASE_URL = settings.database_url

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
test_session_factory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """
    Create tables before tests and truncate after each test.

    Uses CREATE ALL for initial setup and TRUNCATE CASCADE for cleanup
    between tests to ensure test isolation.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        # Terminate other connections to prevent deadlocks
        await conn.execute(
            text(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND pid != pg_backend_pid()
                """
            )
        )
        # Truncate all tables
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session for tests.

    Yields:
        AsyncSession: A test database session.
    """
    async with test_session_factory() as session:
        yield session


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db dependency for tests."""
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an httpx AsyncClient for API testing.

    Yields:
        AsyncClient: Configured for the FastAPI app.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


async def register_and_login(client: AsyncClient, email: str | None = None) -> dict:
    """
    Helper to register a user and return auth headers.

    Args:
        client: The test HTTP client.
        email: Optional email (random if not provided).

    Returns:
        Dict with Authorization header for authenticated requests.
    """
    if not email:
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )
    assert resp.status_code == 201
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """
    Provide authenticated headers for a test user.

    Yields:
        Dict with Authorization Bearer header.
    """
    return await register_and_login(client)
