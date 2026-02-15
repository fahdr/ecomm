"""
FastAPI dependency injection for authentication.

Dependencies are created in main.py using ecomm_core factories.

For Developers:
    Import get_current_user from app.main in service-specific routers.
"""

# Dependencies are created in main.py using ecomm_core factories.
# Service-specific routers should import from app.main:
#   from app.main import get_current_user, get_current_user_or_api_key
