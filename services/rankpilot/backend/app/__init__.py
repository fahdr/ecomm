"""
RankPilot Backend Service.

An independently hostable SaaS product providing Automated SEO Engine.
Built with FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Redis, and Celery.

For Developers:
    This package contains the complete backend API including authentication,
    billing (Stripe), API key management, and the core rankpilot features.

For Project Managers:
    This is the backend server that powers the RankPilot product.
    It handles user accounts, subscriptions, and all business logic.

For QA Engineers:
    Tests are located in the `tests/` directory. Run with `pytest`.
    The test suite covers auth, billing, API keys, and all feature endpoints.

For End Users:
    This service is accessed through the dashboard UI or via the REST API.
    API documentation is available at /docs when the server is running.
"""
