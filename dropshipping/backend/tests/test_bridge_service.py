"""Tests for the bridge_service helper functions.

Verifies HMAC signing, fire_platform_event delegation to Celery, and
async query functions for the dashboard UI.

**For Developers:**
    Tests mock the Celery task and use the ``db`` fixture for async queries.

**For QA Engineers:**
    - ``sign_bridge_payload`` produces deterministic HMAC digests.
    - ``fire_platform_event`` calls Celery ``dispatch_platform_event.delay()``.
    - Query functions return empty results for users with no deliveries.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio

from app.models.bridge_delivery import BridgeDelivery
from app.models.service_integration import ServiceName
from app.services.bridge_service import (
    fire_platform_event,
    get_recent_activity,
    get_resource_deliveries,
    get_service_activity,
    get_service_summary,
    sign_bridge_payload,
)


class TestSignBridgePayload:
    """Tests for HMAC-SHA256 signing."""

    def test_deterministic_signature(self):
        """Same input should always produce the same signature."""
        sig1 = sign_bridge_payload('{"event":"test"}', "secret")
        sig2 = sign_bridge_payload('{"event":"test"}', "secret")
        assert sig1 == sig2

    def test_different_secrets_produce_different_signatures(self):
        """Different secrets should produce different signatures."""
        sig1 = sign_bridge_payload('{"event":"test"}', "secret1")
        sig2 = sign_bridge_payload('{"event":"test"}', "secret2")
        assert sig1 != sig2

    def test_matches_stdlib_hmac(self):
        """Should match Python stdlib HMAC computation."""
        payload = '{"event":"product.created"}'
        secret = "my-secret-key"
        expected = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert sign_bridge_payload(payload, secret) == expected


class TestFirePlatformEvent:
    """Tests for the fire_platform_event wrapper."""

    @patch("app.tasks.bridge_tasks.dispatch_platform_event")
    def test_calls_delay_with_correct_args(self, mock_task):
        """Should call dispatch_platform_event.delay() with string UUIDs."""
        user_id = uuid.uuid4()
        store_id = uuid.uuid4()
        resource_id = uuid.uuid4()

        fire_platform_event(
            user_id=user_id,
            store_id=store_id,
            event="product.created",
            resource_id=resource_id,
            resource_type="product",
            payload={"title": "Widget"},
        )

        mock_task.delay.assert_called_once_with(
            user_id=str(user_id),
            store_id=str(store_id),
            event="product.created",
            resource_id=str(resource_id),
            resource_type="product",
            payload={"title": "Widget"},
        )

    @patch("app.tasks.bridge_tasks.dispatch_platform_event")
    def test_none_store_id(self, mock_task):
        """store_id=None should be passed through as None."""
        fire_platform_event(
            user_id=uuid.uuid4(),
            store_id=None,
            event="customer.created",
            resource_id=uuid.uuid4(),
            resource_type="customer",
            payload={},
        )
        call_kwargs = mock_task.delay.call_args.kwargs
        assert call_kwargs["store_id"] is None


@pytest.mark.asyncio
class TestGetRecentActivity:
    """Tests for the get_recent_activity async query."""

    async def test_empty_result(self, db):
        """Should return empty list and zero total for user with no deliveries."""
        deliveries, total = await get_recent_activity(
            db=db, user_id=uuid.uuid4()
        )
        assert deliveries == []
        assert total == 0


@pytest.mark.asyncio
class TestGetResourceDeliveries:
    """Tests for the get_resource_deliveries async query."""

    async def test_empty_result(self, db):
        """Should return empty list for resource with no deliveries."""
        deliveries = await get_resource_deliveries(
            db=db,
            resource_id=str(uuid.uuid4()),
            resource_type="product",
        )
        assert deliveries == []


@pytest.mark.asyncio
class TestGetServiceActivity:
    """Tests for the get_service_activity async query."""

    async def test_empty_result(self, db):
        """Should return empty list for service with no deliveries."""
        deliveries = await get_service_activity(
            db=db,
            user_id=uuid.uuid4(),
            service_name="contentforge",
        )
        assert deliveries == []

    async def test_invalid_service_returns_empty(self, db):
        """Invalid service name should return empty list."""
        deliveries = await get_service_activity(
            db=db,
            user_id=uuid.uuid4(),
            service_name="nonexistent_service",
        )
        assert deliveries == []


@pytest.mark.asyncio
class TestGetServiceSummary:
    """Tests for the get_service_summary async query."""

    async def test_empty_result(self, db):
        """Should return empty dict for user with no deliveries."""
        summary = await get_service_summary(db=db, user_id=uuid.uuid4())
        assert summary == {}
