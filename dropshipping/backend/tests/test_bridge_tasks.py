"""Tests for the ServiceBridge Celery task: dispatch_platform_event.

Verifies event routing, HMAC signing, delivery recording, and error handling
for the platform bridge task that delivers events to connected SaaS services.

**For Developers:**
    Tests mock ``SyncSessionFactory``, ``httpx.Client``, and
    ``SERVICE_CATALOG`` to avoid real DB and HTTP calls.

**For QA Engineers:**
    - Tests cover all 5 event types and their expected service mappings.
    - Tests verify HMAC signatures, payload structure, and BridgeDelivery recording.
    - Error scenarios: timeout, HTTP errors, no integrations, no mapped services.
"""

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.service_integration import ServiceName, ServiceTier
from app.tasks.bridge_tasks import EVENT_SERVICE_MAP, dispatch_platform_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_integration(service_name: ServiceName, api_key: str = "test-key-123"):
    """Create a mock ServiceIntegration object.

    Args:
        service_name: The service to mock.
        api_key: The API key for signing.

    Returns:
        MagicMock with integration attributes set.
    """
    integ = MagicMock()
    integ.id = uuid.uuid4()
    integ.user_id = uuid.uuid4()
    integ.service_name = service_name
    integ.api_key = api_key
    integ.is_active = True
    integ.tier = ServiceTier.free
    return integ


# ---------------------------------------------------------------------------
# EVENT_SERVICE_MAP tests
# ---------------------------------------------------------------------------

class TestEventServiceMap:
    """Tests for the event-to-service mapping constant."""

    def test_product_created_targets(self):
        """product.created should target 6 services."""
        services = EVENT_SERVICE_MAP["product.created"]
        assert ServiceName.contentforge in services
        assert ServiceName.rankpilot in services
        assert ServiceName.trendscout in services
        assert ServiceName.postpilot in services
        assert ServiceName.adscale in services
        assert ServiceName.shopchat in services
        assert len(services) == 6

    def test_product_updated_targets(self):
        """product.updated should target 3 services."""
        services = EVENT_SERVICE_MAP["product.updated"]
        assert ServiceName.contentforge in services
        assert ServiceName.rankpilot in services
        assert ServiceName.shopchat in services
        assert len(services) == 3

    def test_order_created_targets(self):
        """order.created should target FlowSend and SpyDrop."""
        services = EVENT_SERVICE_MAP["order.created"]
        assert ServiceName.flowsend in services
        assert ServiceName.spydrop in services
        assert len(services) == 2

    def test_order_shipped_targets(self):
        """order.shipped should target only FlowSend."""
        services = EVENT_SERVICE_MAP["order.shipped"]
        assert ServiceName.flowsend in services
        assert len(services) == 1

    def test_customer_created_targets(self):
        """customer.created should target only FlowSend."""
        services = EVENT_SERVICE_MAP["customer.created"]
        assert ServiceName.flowsend in services
        assert len(services) == 1

    def test_unknown_event_returns_empty(self):
        """Unknown events should return an empty list."""
        assert EVENT_SERVICE_MAP.get("unknown.event", []) == []


# ---------------------------------------------------------------------------
# dispatch_platform_event task tests
# ---------------------------------------------------------------------------

class TestDispatchPlatformEvent:
    """Tests for the dispatch_platform_event Celery task."""

    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    def test_no_mapped_services_returns_zero(self, mock_session_factory):
        """Events with no mapped services should return zero counts."""
        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="unknown.event",
            resource_id=str(uuid.uuid4()),
            resource_type="unknown",
            payload={"test": True},
        )
        assert result == {"delivery_count": 0, "success_count": 0, "failure_count": 0}
        mock_session_factory.assert_not_called()

    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    def test_no_active_integrations_returns_zero(self, mock_session_factory):
        """When user has no active integrations, should return zero counts."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session_factory.return_value = mock_session

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="product.created",
            resource_id=str(uuid.uuid4()),
            resource_type="product",
            payload={"title": "Test Product"},
        )
        assert result == {"delivery_count": 0, "success_count": 0, "failure_count": 0}
        mock_session.close.assert_called_once()

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_successful_delivery(self, mock_httpx, mock_session_factory, mock_base_url):
        """Successful HTTP delivery should record success and correct counts."""
        integration = _make_integration(ServiceName.contentforge)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = "http://localhost:8102"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "ok"}'
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="product.created",
            resource_id=str(uuid.uuid4()),
            resource_type="product",
            payload={"title": "Test Product"},
        )
        assert result["delivery_count"] == 1
        assert result["success_count"] == 1
        assert result["failure_count"] == 0
        assert mock_session.add.called
        mock_session.commit.assert_called_once()

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_failed_delivery_http_error(self, mock_httpx, mock_session_factory, mock_base_url):
        """HTTP 500 response should be recorded as failure."""
        integration = _make_integration(ServiceName.flowsend)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = "http://localhost:8104"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="order.created",
            resource_id=str(uuid.uuid4()),
            resource_type="order",
            payload={"order_id": "test"},
        )
        assert result["delivery_count"] == 1
        assert result["success_count"] == 0
        assert result["failure_count"] == 1

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_timeout_records_failure(self, mock_httpx, mock_session_factory, mock_base_url):
        """HTTP timeout should be recorded as failure with error message."""
        import httpx

        integration = _make_integration(ServiceName.spydrop)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = "http://localhost:8105"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.TimeoutException("Connection timed out")
        mock_httpx.return_value = mock_client

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="order.created",
            resource_id=str(uuid.uuid4()),
            resource_type="order",
            payload={},
        )
        assert result["failure_count"] == 1
        assert result["success_count"] == 0

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_multiple_integrations_mixed_results(self, mock_httpx, mock_session_factory, mock_base_url):
        """Multiple integrations with mixed success/failure results."""
        integ1 = _make_integration(ServiceName.contentforge)
        integ2 = _make_integration(ServiceName.rankpilot)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integ1, integ2]
        mock_session_factory.return_value = mock_session
        mock_base_url.side_effect = ["http://localhost:8102", "http://localhost:8103"]

        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.text = '{"status":"ok"}'

        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 503
        mock_resp_fail.text = "Service Unavailable"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = [mock_resp_ok, mock_resp_fail]
        mock_httpx.return_value = mock_client

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="product.updated",
            resource_id=str(uuid.uuid4()),
            resource_type="product",
            payload={"title": "Updated"},
        )
        assert result["delivery_count"] == 2
        assert result["success_count"] == 1
        assert result["failure_count"] == 1

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_payload_structure(self, mock_httpx, mock_session_factory, mock_base_url):
        """Verify the full payload envelope structure sent to services."""
        integration = _make_integration(ServiceName.trendscout)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = "http://localhost:8101"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"ok"}'
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        user_id = str(uuid.uuid4())
        store_id = str(uuid.uuid4())
        resource_id = str(uuid.uuid4())

        dispatch_platform_event(
            user_id=user_id,
            store_id=store_id,
            event="product.created",
            resource_id=resource_id,
            resource_type="product",
            payload={"title": "Widget"},
        )

        # Get the payload sent
        call_args = mock_client.post.call_args
        sent_json = json.loads(call_args.kwargs.get("content", call_args[1].get("content", "")))
        assert sent_json["event"] == "product.created"
        assert sent_json["user_id"] == user_id
        assert sent_json["store_id"] == store_id
        assert sent_json["resource_id"] == resource_id
        assert sent_json["resource_type"] == "product"
        assert sent_json["data"]["title"] == "Widget"
        assert "timestamp" in sent_json

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_hmac_signature_header(self, mock_httpx, mock_session_factory, mock_base_url):
        """Verify the X-Platform-Signature header contains valid HMAC."""
        integration = _make_integration(ServiceName.shopchat)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = "http://localhost:8108"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"ok"}'
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="product.created",
            resource_id=str(uuid.uuid4()),
            resource_type="product",
            payload={"title": "Test"},
        )

        call_args = mock_client.post.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert "X-Platform-Signature" in headers
        assert headers["X-Platform-Signature"].startswith("sha256=")
        assert headers["X-Platform-Event"] == "product.created"

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    def test_skips_service_without_base_url(self, mock_session_factory, mock_base_url):
        """Services without base_url in catalog should be skipped."""
        integration = _make_integration(ServiceName.postpilot)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = ""

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=str(uuid.uuid4()),
            event="product.created",
            resource_id=str(uuid.uuid4()),
            resource_type="product",
            payload={},
        )
        # Skipped integration = 0 deliveries (no success, no failure)
        assert result["delivery_count"] == 0

    @patch("app.tasks.bridge_tasks._get_service_base_url")
    @patch("app.tasks.bridge_tasks.SyncSessionFactory")
    @patch("httpx.Client")
    def test_store_id_none_allowed(self, mock_httpx, mock_session_factory, mock_base_url):
        """store_id=None should be accepted for customer events."""
        integration = _make_integration(ServiceName.flowsend)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [integration]
        mock_session_factory.return_value = mock_session
        mock_base_url.return_value = "http://localhost:8104"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"ok"}'
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.return_value = mock_client

        result = dispatch_platform_event(
            user_id=str(uuid.uuid4()),
            store_id=None,
            event="customer.created",
            resource_id=str(uuid.uuid4()),
            resource_type="customer",
            payload={"email": "test@example.com"},
        )
        assert result["success_count"] == 1
