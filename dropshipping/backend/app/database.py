"""Database engine, session factory, and base model.

Provides the async SQLAlchemy engine and session factory used throughout the
application. All ORM models should inherit from ``Base`` so that Alembic can
detect schema changes via ``Base.metadata``.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)

# expire_on_commit=False allows accessing attributes after commit without
# triggering a lazy load, which is not supported in async sessions.
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models.

    Alembic reads ``Base.metadata`` to autogenerate migrations.
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Automatically commits on success or rolls back on exception.

    Yields:
        AsyncSession: A SQLAlchemy async session bound to the current request.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
