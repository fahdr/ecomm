"""
Test suite for the Super Admin Dashboard backend.

For Developers:
    Tests use pytest-asyncio with httpx ASGITransport for full
    integration testing against the FastAPI app. The test database
    is the same PostgreSQL instance, with tables dropped and recreated
    between tests to ensure isolation.

For QA Engineers:
    Run with: ``pytest`` or ``pytest -v`` from the admin/backend directory.
    All tests are async and use real database operations.

For Project Managers:
    Comprehensive test coverage ensures that admin operations
    (auth, health monitoring, LLM proxy, service overview) work
    correctly before deployment.

For End Users:
    Tests validate the reliability of the admin dashboard that
    platform operators use to keep the ecomm services running smoothly.
"""
