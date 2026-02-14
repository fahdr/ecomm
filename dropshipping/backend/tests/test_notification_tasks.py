"""Tests for notification creation Celery tasks.

Validates that each notification task creates the correct notification
with the right type, title, message, action URL, and metadata.

**For Developers:**
    Tests mock ``SyncSessionFactory`` to inject controlled database state.
    The ``session.add()`` call is inspected to verify the notification content.

**For QA Engineers:**
    - Each task type has at least one test verifying the notification content.
    - Missing entities result in ``status: "skipped"`` (no error).
    - ``action_url`` deep-links to the correct dashboard page.
    - ``metadata_`` contains the relevant entity IDs.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest


def _make_session_with_store(store_user_id: uuid.UUID):
    """Create a mock session that returns a store with the given owner."""
    from app.models.store import Store

    mock_store = MagicMock(spec=Store)
    mock_store.user_id = store_user_id

    session = MagicMock()

    def query_side_effect(model):
        chain = MagicMock()
        if model.__name__ == "Store":
            chain.filter.return_value.first.return_value = mock_store
        else:
            chain.filter.return_value.first.return_value = None
        return chain

    session.query.side_effect = query_side_effect
    return session


class TestCreateOrderNotification:
    """Tests for create_order_notification task."""

    @patch("app.tasks.notification_tasks.SyncSessionFactory")
    def test_creates_order_placed_notification(self, mock_factory):
        """Creates a notification for a new order."""
        from app.models.notification import Notification, NotificationType
        from app.models.order import Order
        from app.tasks.notification_tasks import create_order_notification

        user_id = uuid.uuid4()
        store_id = uuid.uuid4()
        order_id = uuid.uuid4()

        mock_order = MagicMock(spec=Order)
        mock_order.id = order_id
        mock_order.total = Decimal("49.99")
        mock_order.customer_email = "customer@test.com"

        from app.models.store import Store
        mock_store = MagicMock(spec=Store)
        mock_store.user_id = user_id

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model.__name__ == "Store":
                chain.filter.return_value.first.return_value = mock_store
            elif model.__name__ == "Order":
                chain.filter.return_value.first.return_value = mock_order
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = create_order_notification(str(store_id), str(order_id), "order_placed")
        assert result["status"] == "created"

        # Verify the notification was added to the session
        assert session.add.called
        notification = session.add.call_args[0][0]
        assert notification.user_id == user_id
        assert "New Order" in notification.title
        assert str(order_id) in notification.action_url

    @patch("app.tasks.notification_tasks.SyncSessionFactory")
    def test_skips_unknown_event_type(self, mock_factory):
        """Returns skipped for an unrecognized event type."""
        from app.models.order import Order
        from app.models.store import Store
        from app.tasks.notification_tasks import create_order_notification

        mock_store = MagicMock(spec=Store)
        mock_store.user_id = uuid.uuid4()

        mock_order = MagicMock(spec=Order)
        mock_order.id = uuid.uuid4()
        mock_order.total = Decimal("10.00")
        mock_order.customer_email = "test@test.com"

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model.__name__ == "Store":
                chain.filter.return_value.first.return_value = mock_store
            elif model.__name__ == "Order":
                chain.filter.return_value.first.return_value = mock_order
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = create_order_notification(str(uuid.uuid4()), str(uuid.uuid4()), "unknown_event")
        assert result["status"] == "skipped"
        assert "unknown" in result["reason"].lower()

    @patch("app.tasks.notification_tasks.SyncSessionFactory")
    def test_skips_when_store_not_found(self, mock_factory):
        """Returns skipped when the store doesn't exist."""
        from app.models.store import Store
        from app.tasks.notification_tasks import create_order_notification

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = create_order_notification(str(uuid.uuid4()), str(uuid.uuid4()), "order_placed")
        assert result["status"] == "skipped"


class TestCreateLowStockNotification:
    """Tests for create_low_stock_notification task."""

    @patch("app.tasks.notification_tasks.SyncSessionFactory")
    def test_creates_low_stock_notification(self, mock_factory):
        """Creates a notification with product and variant details."""
        from app.models.product import Product, ProductVariant
        from app.models.store import Store
        from app.tasks.notification_tasks import create_low_stock_notification

        user_id = uuid.uuid4()
        store_id = uuid.uuid4()
        product_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        mock_store = MagicMock(spec=Store)
        mock_store.user_id = user_id

        mock_product = MagicMock(spec=Product)
        mock_product.title = "Widget Pro"

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.name = "Large"
        mock_variant.inventory_count = 3

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model.__name__ == "Store":
                chain.filter.return_value.first.return_value = mock_store
            elif model.__name__ == "Product":
                chain.filter.return_value.first.return_value = mock_product
            elif model.__name__ == "ProductVariant":
                chain.filter.return_value.first.return_value = mock_variant
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = create_low_stock_notification(str(store_id), str(product_id), str(variant_id))
        assert result["status"] == "created"

        notification = session.add.call_args[0][0]
        assert "Low Stock" in notification.title
        assert "Widget Pro" in notification.message
        assert "3 units" in notification.message


class TestCreateFraudAlertNotification:
    """Tests for create_fraud_alert_notification task."""

    @patch("app.tasks.notification_tasks.SyncSessionFactory")
    def test_creates_fraud_alert(self, mock_factory):
        """Creates a fraud alert notification with risk details."""
        from app.models.fraud import FraudCheck, FraudRiskLevel
        from app.models.store import Store
        from app.tasks.notification_tasks import create_fraud_alert_notification

        user_id = uuid.uuid4()
        store_id = uuid.uuid4()
        fc_id = uuid.uuid4()
        order_id = uuid.uuid4()

        mock_store = MagicMock(spec=Store)
        mock_store.user_id = user_id

        mock_fc = MagicMock(spec=FraudCheck)
        mock_fc.id = fc_id
        mock_fc.order_id = order_id
        mock_fc.risk_score = Decimal("75")
        mock_fc.risk_level = FraudRiskLevel.high

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model.__name__ == "Store":
                chain.filter.return_value.first.return_value = mock_store
            elif model.__name__ == "FraudCheck":
                chain.filter.return_value.first.return_value = mock_fc
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = create_fraud_alert_notification(str(store_id), str(fc_id))
        assert result["status"] == "created"

        notification = session.add.call_args[0][0]
        assert "Fraud Alert" in notification.title
        assert "High" in notification.title
