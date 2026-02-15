"""
Database setup for the LLM Gateway.

Uses the shared ecomm_core database utilities for engine and session creation.

For Developers:
    The gateway has its own tables (provider_configs, usage_logs, etc.)
    that live in the shared PostgreSQL database. Each table is prefixed
    with ``llm_`` to avoid collisions.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all LLM Gateway models."""

    pass


engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """
    FastAPI dependency that yields a database session.

    Commits on success, rolls back on error.

    Yields:
        AsyncSession: A database session for the request lifecycle.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
