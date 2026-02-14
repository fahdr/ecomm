"""
Database setup for the Super Admin Dashboard.

Provides the async SQLAlchemy engine, session factory, and FastAPI dependency
for database access. Uses the shared ecomm PostgreSQL database with
``admin_``-prefixed tables to avoid collisions with other services.

For Developers:
    The admin backend has its own ``Base`` declarative class. Do not import
    the platform's or gateway's Base — each service maintains independent
    metadata to keep table creation isolated.

    The ``get_db`` dependency commits on success and rolls back on error,
    following the same pattern used across the platform.

For QA Engineers:
    In tests, the ``get_db`` dependency is overridden with a test session
    factory that uses ``NullPool`` for connection isolation.

For Project Managers:
    The admin backend stores its own data (admin users, health snapshots)
    in the shared database, using table prefixes to avoid conflicts.

For End Users:
    This module is part of the internal database infrastructure.
    It has no direct impact on the customer-facing experience.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """
    Declarative base for all Super Admin Dashboard models.

    All models inheriting from this Base will have their tables created
    independently of other services' models. Table names must be
    prefixed with ``admin_`` to avoid collisions.
    """

    pass


engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """
    FastAPI dependency that yields an async database session.

    Commits the transaction on successful completion and rolls back
    on any exception. The session is closed automatically when the
    async context manager exits.

    Yields:
        AsyncSession: A database session scoped to the request lifecycle.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
