"""
SQLAlchemy models for the ContentForge service.

Exports all models so Alembic can detect them for migration generation.

For Developers:
    Import new models here whenever you add a model file. This ensures
    Alembic's `autogenerate` picks up schema changes. The import order
    matters for foreign key resolution — base models first, then dependents.

For QA Engineers:
    All models listed here are included in the test database schema.
    If a model is missing from this file, its table won't be created
    in the test database and tests will fail.
"""

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.generation import GeneratedContent, GenerationJob
from app.models.image_job import ImageJob
from app.models.store_connection import StoreConnection
from app.models.subscription import Subscription
from app.models.template import Template
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Subscription",
    "ApiKey",
    "Template",
    "GenerationJob",
    "GeneratedContent",
    "ImageJob",
    "StoreConnection",
]
