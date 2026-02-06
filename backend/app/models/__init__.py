"""SQLAlchemy ORM models.

All models are imported here so that Alembic can discover them via
``Base.metadata`` when autogenerating migrations.
"""

from app.models.user import User  # noqa: F401
