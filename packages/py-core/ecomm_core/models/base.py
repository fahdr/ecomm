"""
SQLAlchemy declarative base for all models.

For Developers:
    All models should inherit from `Base`. This ensures they are
    registered with the metadata and picked up by Alembic.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models in ecomm services."""

    pass
