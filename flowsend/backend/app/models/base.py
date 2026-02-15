"""
Re-export shared Base from ecomm_core.

For Developers:
    All models (shared and service-specific) must inherit from this Base
    so they share the same metadata for Alembic and test setup.
"""

from ecomm_core.models.base import Base

__all__ = ["Base"]
