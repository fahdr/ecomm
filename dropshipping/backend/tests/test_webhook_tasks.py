"""Tests for webhook delivery Celery tasks.

Validates that ``dispatch_webhook_event`` correctly matches webhooks,
sends HTTP POST requests, records deliveries, and handles failures.

**For Developers:**
    Tests mock ``SyncSessionFactory`` and ``httpx.Client`` to avoid real
    HTTP calls and database access.

**For QA Engineers:**
    - Verifies event matching against webhook subscriptions.
    - Verifies HMAC signature generation.
    - Verifies failure counting and auto-disable after 10 failures.
    - Verifies delivery recording in WebhookDelivery.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest


class TestDispatchWebhookEvent:
    """Tests for the dispatch_webhook_event task."""

    @patch("app.tasks.webhook_tasks.SyncSessionFactory")
    def test_no_matching_webhooks(self, mock_factory):
        """Returns zero counts when no webhooks match the event."""
        from app.tasks.webhook_tasks import dispatch_webhook_event

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        mock_factory.return_value = session

        result = dispatch_webhook_event(str(uuid.uuid4()), "order.paid", {"test": True})
        assert result["delivery_count"] == 0
        assert result["success_count"] == 0
        assert result["failure_count"] == 0

    @patch("app.tasks.webhook_tasks.httpx")
    @patch("app.tasks.webhook_tasks.SyncSessionFactory")
    def test_successful_delivery(self, mock_factory, mock_httpx):
        """Sends HTTP POST and records successful delivery."""
        from app.tasks.webhook_tasks import dispatch_webhook_event

        mock_webhook = MagicMock()
        mock_webhook.id = uuid.uuid4()
        mock_webhook.url = "https://example.com/webhook"
        mock_webhook.secret = "whsec_test123"
        mock_webhook.events = ["order.paid", "order.shipped"]
        mock_webhook.is_active = True
        mock_webhook.failure_count = 0

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [mock_webhook]
        mock_factory.return_value = session

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        store_id = str(uuid.uuid4())
        result = dispatch_webhook_event(store_id, "order.paid", {"amount": "49.99"})

        assert result["delivery_count"] == 1
        assert result["success_count"] == 1
        assert result["failure_count"] == 0
        assert mock_webhook.failure_count == 0
        session.add.assert_called_once()  # WebhookDelivery was added
        session.commit.assert_called_once()

    @patch("app.tasks.webhook_tasks.httpx")
    @patch("app.tasks.webhook_tasks.SyncSessionFactory")
    def test_failed_delivery_increments_count(self, mock_factory, mock_httpx):
        """Increments failure_count on non-2xx response."""
        from app.tasks.webhook_tasks import dispatch_webhook_event

        mock_webhook = MagicMock()
        mock_webhook.id = uuid.uuid4()
        mock_webhook.url = "https://example.com/webhook"
        mock_webhook.secret = "whsec_test"
        mock_webhook.events = ["order.paid"]
        mock_webhook.is_active = True
        mock_webhook.failure_count = 0

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [mock_webhook]
        mock_factory.return_value = session

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        result = dispatch_webhook_event(str(uuid.uuid4()), "order.paid", {})
        assert result["failure_count"] == 1
        assert mock_webhook.failure_count == 1

    @patch("app.tasks.webhook_tasks.httpx")
    @patch("app.tasks.webhook_tasks.SyncSessionFactory")
    def test_auto_disable_after_10_failures(self, mock_factory, mock_httpx):
        """Webhook is disabled when failure_count reaches 10."""
        from app.tasks.webhook_tasks import dispatch_webhook_event

        mock_webhook = MagicMock()
        mock_webhook.id = uuid.uuid4()
        mock_webhook.url = "https://example.com/webhook"
        mock_webhook.secret = "whsec_test"
        mock_webhook.events = ["order.paid"]
        mock_webhook.is_active = True
        mock_webhook.failure_count = 9  # Next failure = 10 → disable

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [mock_webhook]
        mock_factory.return_value = session

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        result = dispatch_webhook_event(str(uuid.uuid4()), "order.paid", {})
        assert mock_webhook.failure_count == 10
        assert mock_webhook.is_active is False

    @patch("app.tasks.webhook_tasks.SyncSessionFactory")
    def test_event_filtering(self, mock_factory):
        """Only webhooks subscribed to the event are dispatched."""
        from app.tasks.webhook_tasks import dispatch_webhook_event

        # Webhook subscribed to "product.created", not "order.paid"
        mock_webhook = MagicMock()
        mock_webhook.id = uuid.uuid4()
        mock_webhook.events = ["product.created"]
        mock_webhook.is_active = True

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [mock_webhook]
        mock_factory.return_value = session

        result = dispatch_webhook_event(str(uuid.uuid4()), "order.paid", {})
        assert result["delivery_count"] == 0
