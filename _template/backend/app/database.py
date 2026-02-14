"""
Async database engine and session factory.

Provides the SQLAlchemy async engine, session factory, and FastAPI
dependency for injecting database sessions into route handlers.

For Developers:
    Use `get_db()` as a FastAPI dependency to get an async session.
    Sessions auto-commit on success and rollback on exception.

For QA Engineers:
    Tests use a separate engine with NullPool to avoid connection sharing.
    See tests/conftest.py for the test database setup.

For Project Managers:
    This module manages all database connections. The async driver
    (asyncpg) provides high-performance non-blocking database access.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.

    Automatically commits on success or rolls back on exception.
    Used as: `db: AsyncSession = Depends(get_db)`

    Yields:
        AsyncSession: An async SQLAlchemy session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
