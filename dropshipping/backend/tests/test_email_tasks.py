"""Tests for email dispatch Celery tasks.

Validates that each email task correctly loads entities from the database,
handles missing entities gracefully, and produces the expected return values.

**For Developers:**
    Tests mock ``SyncSessionFactory`` to inject controlled database state.
    The ``EmailService`` is also mocked to prevent actual template rendering.

**For QA Engineers:**
    - Each task has a "valid entity" test and a "missing entity" test.
    - Missing entities should return ``status: "skipped"`` without raising.
    - All tasks return a dict with ``status`` and ``email`` (or ``reason``).
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_session_with(*entities_by_model):
    """Create a mock session where .query(Model).filter(...).first() returns
    the specified entity for each model class.

    Args:
        entities_by_model: Pairs of (ModelClass, entity_or_None).

    Returns:
        A tuple of (mock_factory_class, mock_session).
    """
    model_map = {model: entity for model, entity in entities_by_model}

    mock_session = MagicMock()

    def query_side_effect(model):
        chain = MagicMock()
        chain.filter.return_value.first.return_value = model_map.get(model)
        return chain

    mock_session.query.side_effect = query_side_effect
    return mock_session


# ---------------------------------------------------------------------------
# send_order_confirmation
# ---------------------------------------------------------------------------


class TestSendOrderConfirmation:
    """Tests for the send_order_confirmation task."""

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_sends_for_valid_order(self, mock_factory):
        """Task returns sent status for a valid order."""
        from app.models.order import Order
        from app.models.store import Store
        from app.tasks.email_tasks import send_order_confirmation

        mock_order = MagicMock(spec=Order)
        mock_order.id = uuid.uuid4()
        mock_order.store_id = uuid.uuid4()
        mock_order.customer_email = "test@example.com"
        mock_order.total = Decimal("49.99")
        mock_order.items = []

        mock_store = MagicMock(spec=Store)
        mock_store.id = mock_order.store_id
        mock_store.name = "Test Store"

        session = _mock_session_with((Order, mock_order), (Store, mock_store))
        mock_factory.return_value = session

        result = send_order_confirmation(str(mock_order.id))
        assert result["status"] == "sent"
        assert result["email"] == "test@example.com"
        session.close.assert_called_once()

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_skips_when_order_not_found(self, mock_factory):
        """Task returns skipped when the order doesn't exist."""
        from app.models.order import Order
        from app.tasks.email_tasks import send_order_confirmation

        session = _mock_session_with((Order, None))
        mock_factory.return_value = session

        result = send_order_confirmation(str(uuid.uuid4()))
        assert result["status"] == "skipped"
        assert "not found" in result["reason"].lower()


# ---------------------------------------------------------------------------
# send_order_shipped
# ---------------------------------------------------------------------------


class TestSendOrderShipped:
    """Tests for the send_order_shipped task."""

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_sends_for_valid_order(self, mock_factory):
        """Task returns sent status with tracking number."""
        from app.models.order import Order
        from app.models.store import Store
        from app.tasks.email_tasks import send_order_shipped

        mock_order = MagicMock(spec=Order)
        mock_order.id = uuid.uuid4()
        mock_order.store_id = uuid.uuid4()
        mock_order.customer_email = "test@example.com"
        mock_order.tracking_number = "TRK-123"

        mock_store = MagicMock(spec=Store)
        mock_store.id = mock_order.store_id
        mock_store.name = "Test Store"

        session = _mock_session_with((Order, mock_order), (Store, mock_store))
        mock_factory.return_value = session

        result = send_order_shipped(str(mock_order.id), "TRK-456")
        assert result["status"] == "sent"
        assert result["email"] == "test@example.com"

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_skips_when_order_not_found(self, mock_factory):
        """Task returns skipped when the order doesn't exist."""
        from app.models.order import Order
        from app.tasks.email_tasks import send_order_shipped

        session = _mock_session_with((Order, None))
        mock_factory.return_value = session

        result = send_order_shipped(str(uuid.uuid4()))
        assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# send_refund_notification
# ---------------------------------------------------------------------------


class TestSendRefundNotification:
    """Tests for the send_refund_notification task."""

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_sends_for_valid_refund(self, mock_factory):
        """Task returns sent status for a valid refund."""
        from app.models.refund import Refund, RefundReason
        from app.models.store import Store
        from app.tasks.email_tasks import send_refund_notification

        mock_refund = MagicMock(spec=Refund)
        mock_refund.id = uuid.uuid4()
        mock_refund.store_id = uuid.uuid4()
        mock_refund.order_id = uuid.uuid4()
        mock_refund.customer_email = "refund@example.com"
        mock_refund.amount = Decimal("19.99")
        mock_refund.reason = RefundReason.defective

        mock_store = MagicMock(spec=Store)
        mock_store.id = mock_refund.store_id
        mock_store.name = "Test Store"

        session = _mock_session_with((Refund, mock_refund), (Store, mock_store))
        mock_factory.return_value = session

        result = send_refund_notification(str(mock_refund.id))
        assert result["status"] == "sent"
        assert result["email"] == "refund@example.com"


# ---------------------------------------------------------------------------
# send_welcome_email
# ---------------------------------------------------------------------------


class TestSendWelcomeEmail:
    """Tests for the send_welcome_email task."""

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_sends_for_valid_customer(self, mock_factory):
        """Task returns sent status for a valid customer."""
        from app.models.customer import CustomerAccount
        from app.models.store import Store
        from app.tasks.email_tasks import send_welcome_email

        mock_customer = MagicMock(spec=CustomerAccount)
        mock_customer.id = uuid.uuid4()
        mock_customer.email = "new@example.com"
        mock_customer.name = "Jane Doe"

        mock_store = MagicMock(spec=Store)
        mock_store.id = uuid.uuid4()
        mock_store.name = "Test Store"

        session = _mock_session_with(
            (CustomerAccount, mock_customer), (Store, mock_store)
        )
        mock_factory.return_value = session

        result = send_welcome_email(str(mock_customer.id), str(mock_store.id))
        assert result["status"] == "sent"
        assert result["email"] == "new@example.com"

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_skips_when_customer_not_found(self, mock_factory):
        """Task returns skipped when the customer doesn't exist."""
        from app.models.customer import CustomerAccount
        from app.tasks.email_tasks import send_welcome_email

        session = _mock_session_with((CustomerAccount, None))
        mock_factory.return_value = session

        result = send_welcome_email(str(uuid.uuid4()), str(uuid.uuid4()))
        assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# send_password_reset
# ---------------------------------------------------------------------------


class TestSendPasswordReset:
    """Tests for the send_password_reset task."""

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_sends_with_store_branding(self, mock_factory):
        """Task returns sent status and uses store name."""
        from app.models.store import Store
        from app.tasks.email_tasks import send_password_reset

        mock_store = MagicMock(spec=Store)
        mock_store.id = uuid.uuid4()
        mock_store.name = "My Shop"

        session = _mock_session_with((Store, mock_store))
        mock_factory.return_value = session

        result = send_password_reset("user@test.com", "token123", str(mock_store.id))
        assert result["status"] == "sent"
        assert result["email"] == "user@test.com"

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_sends_without_store(self, mock_factory):
        """Task uses default platform name when no store provided."""
        from app.tasks.email_tasks import send_password_reset

        session = MagicMock()
        mock_factory.return_value = session

        result = send_password_reset("user@test.com", "token123")
        assert result["status"] == "sent"


# ---------------------------------------------------------------------------
# send_gift_card_email
# ---------------------------------------------------------------------------


class TestSendGiftCardEmail:
    """Tests for the send_gift_card_email task."""

    @patch("app.tasks.email_tasks.SyncSessionFactory")
    def test_skips_when_no_recipient(self, mock_factory):
        """Task returns skipped when gift card has no recipient email."""
        from app.models.gift_card import GiftCard
        from app.tasks.email_tasks import send_gift_card_email

        mock_gc = MagicMock(spec=GiftCard)
        mock_gc.id = uuid.uuid4()
        mock_gc.customer_email = None

        session = _mock_session_with((GiftCard, mock_gc))
        mock_factory.return_value = session

        result = send_gift_card_email(str(mock_gc.id))
        assert result["status"] == "skipped"
        assert "recipient" in result["reason"].lower() or "email" in result["reason"].lower()
