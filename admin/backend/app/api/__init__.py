"""
API routers for the Super Admin Dashboard.

For Developers:
    Each router module handles a specific domain:
    - ``auth``: Admin authentication (login, setup, profile)
    - ``health_monitor``: Service health checks and history
    - ``llm_proxy``: Proxy to the LLM Gateway for provider/usage management
    - ``services_overview``: Overview of all platform services

For QA Engineers:
    All routes are mounted under ``/api/v1/admin/`` and require JWT
    authentication (except the initial setup endpoint).

For Project Managers:
    The API surface gives admins full control over the platform
    from a single dashboard interface.

For End Users:
    These APIs are exclusively for platform administrators and are
    not exposed in any customer-facing product.
"""
