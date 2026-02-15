"""
Database engine and session factory utilities.

Provides helper functions for creating async engines and session factories.

For Developers:
    Use `create_db_engine()` and `create_session_factory()` in your
    service's database.py, passing the settings.database_url.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def create_db_engine(database_url: str, echo: bool = False):
    """
    Create an async SQLAlchemy engine.

    Args:
        database_url: Async PostgreSQL connection string.
        echo: Enable SQL logging for debugging.

    Returns:
        AsyncEngine instance.
    """
    return create_async_engine(database_url, echo=echo)


def create_session_factory(engine) -> async_sessionmaker:
    """
    Create an async session factory from an engine.

    Args:
        engine: AsyncEngine to bind sessions to.

    Returns:
        async_sessionmaker configured for the engine.
    """
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def create_get_db(session_factory: async_sessionmaker):
    """
    Create a FastAPI dependency for injecting database sessions.

    Args:
        session_factory: The async session factory to use.

    Returns:
        An async generator function suitable for FastAPI Depends().
    """

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        """
        FastAPI dependency that yields an async database session.

        Automatically commits on success or rolls back on exception.
        """
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return get_db
