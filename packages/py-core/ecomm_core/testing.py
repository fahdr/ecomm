"""
Shared test fixtures and utilities for ecomm SaaS services.

Provides reusable pytest fixtures for database setup, async clients,
and authentication helpers.

For Developers:
    Import and use these fixtures in your service's conftest.py:
        from ecomm_core.testing import create_test_fixtures
        fixtures = create_test_fixtures(app, Base, settings)

For QA Engineers:
    All tests run with isolated database sessions. Tables are truncated
    between tests for full isolation.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def create_test_engine(database_url: str):
    """
    Create a test-specific async engine with NullPool.

    Args:
        database_url: Async PostgreSQL connection string.

    Returns:
        AsyncEngine configured for test isolation.
    """
    return create_async_engine(database_url, poolclass=NullPool)


def create_test_session_factory(engine) -> async_sessionmaker:
    """
    Create a test-specific session factory.

    Args:
        engine: The test engine.

    Returns:
        async_sessionmaker for test sessions.
    """
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def register_and_login(client: AsyncClient, email: str | None = None) -> dict:
    """
    Helper to register a user and return auth headers.

    Args:
        client: The test HTTP client.
        email: Optional email (random if not provided).

    Returns:
        Dict with Authorization header for authenticated requests.
    """
    if not email:
        email = f"test-{uuid.uuid4().hex[:8]}@example.com"

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )
    assert resp.status_code == 201
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
