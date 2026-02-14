"""
ecomm_core — Shared core library for all ecomm SaaS platform services.

Provides authentication, billing, database setup, models, schemas,
health checks, plan management, and test utilities.

For Developers:
    Import from submodules: `from ecomm_core.auth import service as auth_service`
    Each service installs this package as an editable dependency.

For Project Managers:
    This package eliminates ~7,000 lines of duplicated code across 8 services.
    A bug fix here automatically applies to all services on next install.
"""

__version__ = "0.1.0"
