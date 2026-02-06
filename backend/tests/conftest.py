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


@pytest.fixture(autouse=True)
async def clean_tables():
    """Truncate all table data before each test for isolation.

    Tables are assumed to exist (created by Alembic). Only data is cleared.

    Yields:
        None: Control is passed to the test function.
    """
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
    yield


@pytest.fixture
async def client():
    """Yield an async HTTP client wired to the FastAPI app with DB override.

    Overrides the ``get_db`` dependency so each request uses a fresh
    database session from the test engine.

    Yields:
        AsyncClient: An httpx client that sends requests to the FastAPI app.
    """

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
