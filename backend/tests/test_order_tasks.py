"""Tests for order processing Celery tasks.

Validates the ``process_paid_order`` orchestrator, ``auto_fulfill_order``
automatic fulfillment, and ``check_fulfillment_status`` Beat task.

**For Developers:**
    Tests mock ``SyncSessionFactory`` and downstream task ``.delay()`` calls.
    ``process_paid_order`` calls ``run_fraud_check`` synchronously (direct import),
    so it is also mocked to control fraud results.

**For QA Engineers:**
    - ``process_paid_order`` always dispatches email, webhook, and notification
      regardless of fraud result.
    - Auto-fulfill is skipped when order is fraud-flagged.
    - ``auto_fulfill_order`` only transitions orders in ``paid`` status.
    - ``check_fulfillment_status`` uses random delivery (mocked to control).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


def _make_mock_order(
    status="paid",
    store_id=None,
    order_id=None,
    customer_email="customer@example.com",
    total="49.99",
):
    """Create a mock Order with configurable fields."""
    from app.models.order import Order, OrderStatus

    mock = MagicMock(spec=Order)
    mock.id = order_id or uuid.uuid4()
    mock.store_id = store_id or uuid.uuid4()
    mock.customer_email = customer_email
    mock.total = Decimal(total)
    mock.currency = "USD"
    mock.status = OrderStatus[status]
    return mock


# ---------------------------------------------------------------------------
# process_paid_order
# ---------------------------------------------------------------------------


class TestProcessPaidOrder:
    """Tests for the process_paid_order orchestrator task."""

    @patch("app.tasks.order_tasks.auto_fulfill_order")
    @patch("app.tasks.notification_tasks.create_low_stock_notification")
    @patch("app.tasks.notification_tasks.create_order_notification")
    @patch("app.tasks.webhook_tasks.dispatch_webhook_event")
    @patch("app.tasks.email_tasks.send_low_stock_alert")
    @patch("app.tasks.email_tasks.send_order_confirmation")
    @patch("app.tasks.fraud_tasks.run_fraud_check")
    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_orchestrates_all_downstream_tasks(
        self, mock_factory, mock_fraud, mock_email, mock_low_stock_email,
        mock_webhook, mock_notify, mock_low_stock_notify, mock_auto_fulfill,
    ):
        """Dispatches email, webhook, notification, and auto-fulfill for a clean order."""
        from app.models.order import Order, OrderItem, OrderStatus
        from app.models.product import ProductVariant
        from app.tasks.order_tasks import process_paid_order

        order = _make_mock_order(status="paid")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == "Order":
                chain.filter.return_value.first.return_value = order
            elif hasattr(model, '__name__') and model.__name__ == "OrderItem":
                chain.filter.return_value.all.return_value = []  # no items
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        mock_fraud.return_value = {
            "risk_score": 0,
            "risk_level": "low",
            "is_flagged": False,
            "signals": [],
        }

        mock_email.delay = MagicMock()
        mock_webhook.delay = MagicMock()
        mock_notify.delay = MagicMock()
        mock_auto_fulfill.delay = MagicMock()

        result = process_paid_order(str(order.id))

        assert result["order_id"] == str(order.id)
        mock_email.delay.assert_called_once()
        mock_webhook.delay.assert_called_once()
        mock_notify.delay.assert_called_once()
        mock_auto_fulfill.delay.assert_called_once()
        assert result["auto_fulfill"] == "dispatched"

    @patch("app.tasks.order_tasks.auto_fulfill_order")
    @patch("app.tasks.notification_tasks.create_order_notification")
    @patch("app.tasks.webhook_tasks.dispatch_webhook_event")
    @patch("app.tasks.email_tasks.send_order_confirmation")
    @patch("app.tasks.fraud_tasks.run_fraud_check")
    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_auto_fulfill_when_fraud_flagged(
        self, mock_factory, mock_fraud, mock_email, mock_webhook,
        mock_notify, mock_auto_fulfill,
    ):
        """Auto-fulfill is skipped when fraud check flags the order."""
        from app.models.order import Order, OrderItem
        from app.tasks.order_tasks import process_paid_order

        order = _make_mock_order(status="paid")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == "Order":
                chain.filter.return_value.first.return_value = order
            elif hasattr(model, '__name__') and model.__name__ == "OrderItem":
                chain.filter.return_value.all.return_value = []
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        mock_fraud.return_value = {
            "risk_score": 75,
            "risk_level": "high",
            "is_flagged": True,
            "signals": ["high_amount", "new_customer_high_order", "first_order"],
        }

        mock_email.delay = MagicMock()
        mock_webhook.delay = MagicMock()
        mock_notify.delay = MagicMock()
        mock_auto_fulfill.delay = MagicMock()

        result = process_paid_order(str(order.id))

        assert result["auto_fulfill"] == "skipped_fraud_flagged"
        mock_auto_fulfill.delay.assert_not_called()
        # Email, webhook, notification still dispatched
        mock_email.delay.assert_called_once()

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_when_order_not_found(self, mock_factory):
        """Returns skipped when order doesn't exist."""
        from app.tasks.order_tasks import process_paid_order

        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        mock_factory.return_value = session

        result = process_paid_order(str(uuid.uuid4()))
        assert result["status"] == "skipped"
        assert "not found" in result["reason"].lower()

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_when_order_not_paid(self, mock_factory):
        """Returns skipped when order is not in paid status."""
        from app.tasks.order_tasks import process_paid_order

        order = _make_mock_order(status="shipped")

        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = order
        mock_factory.return_value = session

        result = process_paid_order(str(order.id))
        assert result["status"] == "skipped"
        assert "shipped" in result["reason"].lower()

    @patch("app.tasks.order_tasks.auto_fulfill_order")
    @patch("app.tasks.notification_tasks.create_low_stock_notification")
    @patch("app.tasks.notification_tasks.create_order_notification")
    @patch("app.tasks.webhook_tasks.dispatch_webhook_event")
    @patch("app.tasks.email_tasks.send_low_stock_alert")
    @patch("app.tasks.email_tasks.send_order_confirmation")
    @patch("app.tasks.fraud_tasks.run_fraud_check")
    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_dispatches_low_stock_alerts(
        self, mock_factory, mock_fraud, mock_email, mock_low_stock_email,
        mock_webhook, mock_notify, mock_low_stock_notify, mock_auto_fulfill,
    ):
        """Low-stock alerts dispatched for variants with <= 5 units."""
        from app.models.order import Order, OrderItem
        from app.models.product import ProductVariant
        from app.tasks.order_tasks import process_paid_order

        order = _make_mock_order(status="paid")
        product_id = uuid.uuid4()
        variant_id = uuid.uuid4()

        mock_item = MagicMock(spec=OrderItem)
        mock_item.variant_id = variant_id
        mock_item.product_id = product_id

        mock_variant = MagicMock(spec=ProductVariant)
        mock_variant.id = variant_id
        mock_variant.inventory_count = 3  # below threshold

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == "Order":
                chain.filter.return_value.first.return_value = order
            elif hasattr(model, '__name__') and model.__name__ == "OrderItem":
                chain.filter.return_value.all.return_value = [mock_item]
            elif hasattr(model, '__name__') and model.__name__ == "ProductVariant":
                chain.filter.return_value.first.return_value = mock_variant
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        mock_fraud.return_value = {
            "risk_score": 0, "risk_level": "low",
            "is_flagged": False, "signals": [],
        }

        mock_email.delay = MagicMock()
        mock_low_stock_email.delay = MagicMock()
        mock_webhook.delay = MagicMock()
        mock_notify.delay = MagicMock()
        mock_low_stock_notify.delay = MagicMock()
        mock_auto_fulfill.delay = MagicMock()

        result = process_paid_order(str(order.id))
        assert result["low_stock_alerts"] == 1
        mock_low_stock_email.delay.assert_called_once()
        mock_low_stock_notify.delay.assert_called_once()


# ---------------------------------------------------------------------------
# auto_fulfill_order
# ---------------------------------------------------------------------------


class TestAutoFulfillOrder:
    """Tests for the auto_fulfill_order task."""

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_when_order_not_found(self, mock_factory):
        """Returns skipped when order doesn't exist."""
        from app.tasks.order_tasks import auto_fulfill_order

        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        mock_factory.return_value = session

        result = auto_fulfill_order(str(uuid.uuid4()))
        assert result["status"] == "skipped"

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_when_order_not_paid(self, mock_factory):
        """Returns skipped when order is not in paid status."""
        from app.tasks.order_tasks import auto_fulfill_order

        order = _make_mock_order(status="shipped")

        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = order
        mock_factory.return_value = session

        result = auto_fulfill_order(str(order.id))
        assert result["status"] == "skipped"
        assert "shipped" in result["reason"].lower()

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_when_no_order_items(self, mock_factory):
        """Returns skipped when order has no items."""
        from app.models.order import Order, OrderItem
        from app.tasks.order_tasks import auto_fulfill_order

        order = _make_mock_order(status="paid")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == "Order":
                chain.filter.return_value.first.return_value = order
            elif hasattr(model, '__name__') and model.__name__ == "OrderItem":
                chain.filter.return_value.all.return_value = []
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = auto_fulfill_order(str(order.id))
        assert result["status"] == "skipped"
        assert "no order items" in result["reason"].lower()

    @patch("app.tasks.notification_tasks.create_order_notification")
    @patch("app.tasks.webhook_tasks.dispatch_webhook_event")
    @patch("app.tasks.email_tasks.send_order_shipped")
    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_fulfills_with_suppliers(
        self, mock_factory, mock_shipped_email, mock_webhook, mock_notify,
    ):
        """Fulfills order when all items have primary active suppliers."""
        from app.models.order import Order, OrderItem, OrderStatus
        from app.models.supplier import ProductSupplier, Supplier
        from app.tasks.order_tasks import auto_fulfill_order

        order = _make_mock_order(status="paid")
        product_id = uuid.uuid4()

        mock_item = MagicMock(spec=OrderItem)
        mock_item.product_id = product_id

        mock_product_supplier = MagicMock(spec=ProductSupplier)
        mock_product_supplier.is_primary = True

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == "Order":
                chain.filter.return_value.first.return_value = order
            elif hasattr(model, '__name__') and model.__name__ == "OrderItem":
                chain.filter.return_value.all.return_value = [mock_item]
            elif hasattr(model, '__name__') and model.__name__ == "ProductSupplier":
                chain.join.return_value.filter.return_value.first.return_value = mock_product_supplier
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        mock_shipped_email.delay = MagicMock()
        mock_webhook.delay = MagicMock()
        mock_notify.delay = MagicMock()

        result = auto_fulfill_order(str(order.id))
        assert result["status"] == "fulfilled"
        assert result["tracking_number"].startswith("TRK-")
        assert result["carrier"] == "Auto-Fulfill"
        assert order.status == OrderStatus.shipped
        mock_shipped_email.delay.assert_called_once()
        mock_webhook.delay.assert_called_once()
        mock_notify.delay.assert_called_once()
        session.commit.assert_called_once()

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_without_primary_supplier(self, mock_factory):
        """Skips fulfillment when items lack primary suppliers."""
        from app.models.order import Order, OrderItem
        from app.models.supplier import ProductSupplier
        from app.tasks.order_tasks import auto_fulfill_order

        order = _make_mock_order(status="paid")

        mock_item = MagicMock(spec=OrderItem)
        mock_item.product_id = uuid.uuid4()

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if hasattr(model, '__name__') and model.__name__ == "Order":
                chain.filter.return_value.first.return_value = order
            elif hasattr(model, '__name__') and model.__name__ == "OrderItem":
                chain.filter.return_value.all.return_value = [mock_item]
            elif hasattr(model, '__name__') and model.__name__ == "ProductSupplier":
                # No primary supplier found
                chain.join.return_value.filter.return_value.first.return_value = None
            else:
                chain.filter.return_value.first.return_value = None
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = auto_fulfill_order(str(order.id))
        assert result["status"] == "skipped"
        assert "supplier" in result["reason"].lower()


# ---------------------------------------------------------------------------
# check_fulfillment_status
# ---------------------------------------------------------------------------


class TestCheckFulfillmentStatus:
    """Tests for the check_fulfillment_status Beat task."""

    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_no_shipped_orders(self, mock_factory):
        """Returns zero counts when no shipped orders exist."""
        from app.tasks.order_tasks import check_fulfillment_status

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        mock_factory.return_value = session

        result = check_fulfillment_status()
        assert result["checked_count"] == 0
        assert result["delivered_count"] == 0

    @patch("app.tasks.order_tasks.random")
    @patch("app.tasks.notification_tasks.create_order_notification")
    @patch("app.tasks.webhook_tasks.dispatch_webhook_event")
    @patch("app.tasks.email_tasks.send_order_delivered")
    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_delivers_orders_randomly(
        self, mock_factory, mock_email, mock_webhook, mock_notify, mock_random,
    ):
        """Transitions shipped orders to delivered based on random chance."""
        from app.models.order import Order, OrderStatus
        from app.tasks.order_tasks import check_fulfillment_status

        mock_order = MagicMock(spec=Order)
        mock_order.id = uuid.uuid4()
        mock_order.store_id = uuid.uuid4()
        mock_order.status = OrderStatus.shipped
        mock_order.shipped_at = datetime.now(timezone.utc) - timedelta(days=10)

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [mock_order]
        mock_factory.return_value = session

        mock_email.delay = MagicMock()
        mock_webhook.delay = MagicMock()
        mock_notify.delay = MagicMock()

        # Force the random check to pass (< 0.3)
        mock_random.random.return_value = 0.1

        result = check_fulfillment_status()
        assert result["checked_count"] == 1
        assert result["delivered_count"] == 1
        assert mock_order.status == OrderStatus.delivered
        mock_email.delay.assert_called_once()
        session.commit.assert_called_once()

    @patch("app.tasks.order_tasks.random")
    @patch("app.tasks.order_tasks.SyncSessionFactory")
    def test_skips_delivery_on_high_random(self, mock_factory, mock_random):
        """Does not deliver orders when random > 0.3."""
        from app.models.order import Order, OrderStatus
        from app.tasks.order_tasks import check_fulfillment_status

        mock_order = MagicMock(spec=Order)
        mock_order.id = uuid.uuid4()
        mock_order.store_id = uuid.uuid4()
        mock_order.status = OrderStatus.shipped
        mock_order.shipped_at = datetime.now(timezone.utc) - timedelta(days=10)

        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = [mock_order]
        mock_factory.return_value = session

        # Force the random check to fail (>= 0.3)
        mock_random.random.return_value = 0.5

        result = check_fulfillment_status()
        assert result["checked_count"] == 1
        assert result["delivered_count"] == 0
        assert mock_order.status == OrderStatus.shipped
        session.commit.assert_not_called()
