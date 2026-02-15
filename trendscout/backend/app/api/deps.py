"""
FastAPI dependency injection for authentication and authorization.

Re-exports shared auth dependencies from ecomm_core, created in main.py.

For Developers:
    Use ``get_current_user`` and ``get_current_user_or_api_key`` from main.py
    or import them in service-specific routers.

For QA Engineers:
    Test unauthenticated access (should return 401), expired tokens,
    invalid API keys.
"""

# Dependencies are created in main.py using ecomm_core factories.
# Service-specific routers should import from app.main:
#   from app.main import get_current_user, get_current_user_or_api_key
