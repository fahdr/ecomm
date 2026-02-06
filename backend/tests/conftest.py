"""Shared pytest fixtures for backend tests.

Provides reusable fixtures (e.g. the async HTTP client) that are
automatically available to all test modules in this directory.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Yield an async HTTP client wired to the FastAPI app.

    Uses httpx's ASGITransport so requests are handled in-process
    without starting a real server, making tests fast and isolated.

    Yields:
        AsyncClient: An httpx client that sends requests to the FastAPI app.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
