"""Tests for the ServiceBridge REST API endpoints.

Verifies authentication, pagination, filtering, and response structure
for the bridge activity dashboard endpoints.

**For Developers:**
    Tests use the ``client`` and ``db`` fixtures from conftest. Auth
    helper creates a user and returns headers with a valid JWT.

**For QA Engineers:**
    - All endpoints require authentication (401 without token).
    - GET endpoints return correct response structure.
    - POST dispatch fires the Celery task asynchronously.
"""

import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.auth_service import create_access_token, hash_password


async def _create_user(db: AsyncSession) -> User:
    """Create a test user in the database.

    Args:
        db: Async database session.

    Returns:
        The created User with all fields populated.
    """
    user = User(
        email=f"bridge-test-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("testpassword123"),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
    return user


async def _auth_headers(db: AsyncSession) -> dict:
    """Create a test user and return Authorization headers.

    Args:
        db: Async database session.

    Returns:
        Dict with Authorization header containing a valid Bearer JWT.
    """
    user = await _create_user(db)
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestBridgeActivityEndpoint:
    """Tests for GET /api/v1/bridge/activity."""

    async def test_requires_auth(self, client: AsyncClient):
        """Should return 401 without auth token."""
        resp = await client.get("/api/v1/bridge/activity")
        assert resp.status_code == 401

    async def test_empty_activity(self, client: AsyncClient, db: AsyncSession):
        """Should return empty paginated response for new user."""
        headers = await _auth_headers(db)
        resp = await client.get("/api/v1/bridge/activity", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["pages"] == 1

    async def test_pagination_params(self, client: AsyncClient, db: AsyncSession):
        """Should accept pagination query params."""
        headers = await _auth_headers(db)
        resp = await client.get(
            "/api/v1/bridge/activity?page=2&per_page=5",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["per_page"] == 5

    async def test_filter_params_accepted(self, client: AsyncClient, db: AsyncSession):
        """Should accept filter query params without error."""
        headers = await _auth_headers(db)
        resp = await client.get(
            "/api/v1/bridge/activity?event=product.created&service=contentforge&status=success",
            headers=headers,
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestResourceActivityEndpoint:
    """Tests for GET /api/v1/bridge/activity/{resource_type}/{resource_id}."""

    async def test_requires_auth(self, client: AsyncClient):
        """Should return 401 without auth token."""
        resp = await client.get(f"/api/v1/bridge/activity/product/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_empty_resource_activity(self, client: AsyncClient, db: AsyncSession):
        """Should return empty list for resource with no deliveries."""
        headers = await _auth_headers(db)
        resp = await client.get(
            f"/api/v1/bridge/activity/product/{uuid.uuid4()}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestServiceActivityEndpoint:
    """Tests for GET /api/v1/bridge/service/{service_name}/activity."""

    async def test_requires_auth(self, client: AsyncClient):
        """Should return 401 without auth token."""
        resp = await client.get("/api/v1/bridge/service/contentforge/activity")
        assert resp.status_code == 401

    async def test_empty_service_activity(self, client: AsyncClient, db: AsyncSession):
        """Should return empty list for service with no deliveries."""
        headers = await _auth_headers(db)
        resp = await client.get(
            "/api/v1/bridge/service/contentforge/activity",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestSummaryEndpoint:
    """Tests for GET /api/v1/bridge/summary."""

    async def test_requires_auth(self, client: AsyncClient):
        """Should return 401 without auth token."""
        resp = await client.get("/api/v1/bridge/summary")
        assert resp.status_code == 401

    async def test_empty_summary(self, client: AsyncClient, db: AsyncSession):
        """Should return empty list for user with no deliveries."""
        headers = await _auth_headers(db)
        resp = await client.get("/api/v1/bridge/summary", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestDispatchEndpoint:
    """Tests for POST /api/v1/bridge/dispatch."""

    async def test_requires_auth(self, client: AsyncClient):
        """Should return 401 without auth token."""
        resp = await client.post(
            "/api/v1/bridge/dispatch",
            json={
                "event": "product.created",
                "resource_id": str(uuid.uuid4()),
                "resource_type": "product",
            },
        )
        assert resp.status_code == 401

    @patch("app.api.bridge.fire_platform_event")
    async def test_dispatch_fires_event(
        self, mock_fire, client: AsyncClient, db: AsyncSession
    ):
        """Should fire the platform event and return confirmation."""
        headers = await _auth_headers(db)
        resource_id = str(uuid.uuid4())
        resp = await client.post(
            "/api/v1/bridge/dispatch",
            json={
                "event": "product.created",
                "resource_id": resource_id,
                "resource_type": "product",
                "payload": {"title": "Test"},
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "dispatched"
        assert data["event"] == "product.created"
        assert data["resource_id"] == resource_id
        mock_fire.assert_called_once()

    async def test_dispatch_missing_fields(self, client: AsyncClient, db: AsyncSession):
        """Should return 422 for missing required fields."""
        headers = await _auth_headers(db)
        resp = await client.post(
            "/api/v1/bridge/dispatch",
            json={"event": "product.created"},
            headers=headers,
        )
        assert resp.status_code == 422
