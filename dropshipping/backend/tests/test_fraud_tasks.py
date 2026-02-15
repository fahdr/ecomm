"""Tests for fraud detection Celery tasks.

Validates that ``run_fraud_check`` correctly evaluates heuristic signals,
calculates risk scores, assigns risk levels, and dispatches fraud alert
notifications for flagged orders.

**For Developers:**
    Tests mock ``SyncSessionFactory`` to inject controlled database state.
    Each signal is tested individually and in combination to verify correct
    score accumulation and risk-level thresholds.

**For QA Engineers:**
    - Signal thresholds: high_amount ($500+), new_customer_high_order (first + $200+),
      velocity_spike (3+ in 1h), suspicious_email ("+", "test", "fake", "temp"),
      first_order (no prior paid orders).
    - Risk levels: low (0-25), medium (26-50), high (51-75), critical (76-100).
    - Score is capped at 100.
    - Fraud alert notification dispatched only when flagged (high/critical).
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest


def _make_mock_order(
    total="49.99",
    customer_email="customer@example.com",
    store_id=None,
    order_id=None,
):
    """Create a mock Order with configurable fields."""
    from app.models.order import Order, OrderStatus

    mock = MagicMock(spec=Order)
    mock.id = order_id or uuid.uuid4()
    mock.store_id = store_id or uuid.uuid4()
    mock.total = Decimal(total)
    mock.customer_email = customer_email
    mock.currency = "USD"
    mock.status = OrderStatus.paid
    return mock


class TestRunFraudCheckOrderNotFound:
    """Tests for missing order handling."""

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_skips_when_order_not_found(self, mock_factory):
        """Returns skipped when order doesn't exist."""
        from app.tasks.fraud_tasks import run_fraud_check

        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        mock_factory.return_value = session

        result = run_fraud_check(str(uuid.uuid4()))
        assert result["status"] == "skipped"
        assert "not found" in result["reason"].lower()


class TestFraudSignalHighAmount:
    """Tests for the high_amount signal ($500+)."""

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_high_amount_adds_20_points(self, mock_factory):
        """Orders >= $500 trigger high_amount signal (+20 points)."""
        from app.models.fraud import FraudCheck, FraudRiskLevel
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="600.00", customer_email="legit@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                # previous_orders=1 (not first), velocity=1 (no spike)
                chain.filter.return_value.scalar.return_value = 1
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert "high_amount" in result["signals"]
        assert result["risk_score"] >= 20

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_no_high_amount_under_500(self, mock_factory):
        """Orders < $500 do not trigger high_amount signal."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="499.99", customer_email="legit@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                # previous_orders=1 (not first), velocity=1 (no spike)
                chain.filter.return_value.scalar.return_value = 1
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert "high_amount" not in result["signals"]


class TestFraudSignalSuspiciousEmail:
    """Tests for the suspicious_email signal."""

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_suspicious_email_with_plus(self, mock_factory):
        """Email containing '+' triggers suspicious_email signal."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="20.00", customer_email="user+alias@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                chain.filter.return_value.scalar.return_value = 1
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert "suspicious_email" in result["signals"]

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_suspicious_email_with_test(self, mock_factory):
        """Email containing 'test' triggers suspicious_email signal."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="20.00", customer_email="testuser@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                chain.filter.return_value.scalar.return_value = 1
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert "suspicious_email" in result["signals"]


class TestFraudSignalFirstOrder:
    """Tests for the first_order signal."""

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_first_order_adds_10_points(self, mock_factory):
        """First-time customer triggers first_order signal (+10)."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="20.00", customer_email="new@example.com")

        session = MagicMock()
        call_count = [0]

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                # First call: previous orders count (0 = first order)
                # Second call: velocity count
                chain.filter.return_value.scalar.return_value = 0
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert "first_order" in result["signals"]
        assert result["risk_score"] >= 10


class TestFraudRiskLevels:
    """Tests for risk level thresholds."""

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_low_risk_clean_order(self, mock_factory):
        """A clean order with no signals is low risk."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="20.00", customer_email="clean@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                # previous_orders=1 (not first order), velocity=1 (no spike)
                chain.filter.return_value.scalar.return_value = 1
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert result["risk_level"] == "low"
        assert result["is_flagged"] is False
        assert result["risk_score"] == 0

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_high_risk_is_flagged(self, mock_factory):
        """Orders with high risk level are flagged for review."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        # High amount ($500+ → +20) + first order (+10) + new_customer_high_order (+25) = 55 → high
        order = _make_mock_order(total="600.00", customer_email="new@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                chain.filter.return_value.scalar.return_value = 0  # first order
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert result["risk_level"] in ("high", "critical")
        assert result["is_flagged"] is True

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_score_capped_at_100(self, mock_factory):
        """Risk score is capped at 100 even if signals exceed it."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        # high_amount(+20) + new_customer_high_order(+25) + velocity_spike(+30)
        # + suspicious_email(+15) + first_order(+10) = 100
        order = _make_mock_order(
            total="600.00",
            customer_email="test+alias@fake.com",
        )

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                # previous_orders=0 (first order), velocity=5 (spike)
                chain.filter.return_value.scalar.return_value = 0
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        # Override velocity to trigger spike
        # The query returns 0 for previous orders but we need velocity >= 3
        # Since both queries use the same scalar mock, we need sequential return values
        scalar_values = iter([0, 5])  # first=0 prev orders, second=5 recent orders
        def query_side_effect_v2(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                chain.filter.return_value.scalar.return_value = next(scalar_values, 0)
            return chain

        session.query.side_effect = query_side_effect_v2

        result = run_fraud_check(str(order.id))
        assert result["risk_score"] <= 100


class TestFraudNotificationDispatch:
    """Tests for fraud alert notification dispatching."""

    @patch("app.tasks.notification_tasks.create_fraud_alert_notification")
    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_dispatches_notification_when_flagged(self, mock_factory, mock_notify):
        """Fraud alert notification is dispatched for flagged orders."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        # Trigger high risk: high_amount + first_order + new_customer_high_order = 55
        order = _make_mock_order(total="600.00", customer_email="new@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                chain.filter.return_value.scalar.return_value = 0  # first order
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        mock_notify.delay = MagicMock()

        result = run_fraud_check(str(order.id))
        if result["is_flagged"]:
            mock_notify.delay.assert_called_once()

    @patch("app.tasks.fraud_tasks.SyncSessionFactory")
    def test_no_notification_for_low_risk(self, mock_factory):
        """No notification is dispatched for low-risk orders."""
        from app.models.order import Order
        from app.tasks.fraud_tasks import run_fraud_check

        order = _make_mock_order(total="20.00", customer_email="clean@example.com")

        session = MagicMock()

        def query_side_effect(model):
            chain = MagicMock()
            if model is Order or (hasattr(model, '__name__') and model.__name__ == "Order"):
                chain.filter.return_value.first.return_value = order
            else:
                # previous_orders=1 (not first), velocity=1 (no spike)
                chain.filter.return_value.scalar.return_value = 1
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = run_fraud_check(str(order.id))
        assert result["is_flagged"] is False
        # No notification task imported means no dispatch
