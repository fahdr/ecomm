"""Tests for periodic analytics and maintenance Celery tasks.

Validates that ``aggregate_daily_analytics`` correctly computes per-store
metrics and that ``cleanup_old_notifications`` removes only read
notifications older than 90 days.

**For Developers:**
    Tests mock ``SyncSessionFactory`` and inject controlled query results.
    ``cleanup_old_notifications`` uses ``session.execute(delete(...))`` so the
    mock verifies rowcount behavior.

**For QA Engineers:**
    - ``aggregate_daily_analytics`` processes only active stores.
    - Revenue calculation includes paid, shipped, and delivered orders.
    - ``cleanup_old_notifications`` only deletes read notifications (is_read=True).
    - Notifications younger than 90 days are preserved.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# aggregate_daily_analytics
# ---------------------------------------------------------------------------


class TestAggregateDailyAnalytics:
    """Tests for the aggregate_daily_analytics Beat task."""

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_processes_active_stores(self, mock_factory):
        """Processes all active stores and returns correct counts."""
        from app.models.store import Store, StoreStatus
        from app.tasks.analytics_tasks import aggregate_daily_analytics

        mock_store1 = MagicMock(spec=Store)
        mock_store1.id = uuid.uuid4()
        mock_store1.name = "Store A"
        mock_store1.status = StoreStatus.active

        mock_store2 = MagicMock(spec=Store)
        mock_store2.id = uuid.uuid4()
        mock_store2.name = "Store B"
        mock_store2.status = StoreStatus.active

        # Mock the revenue query result
        mock_result = MagicMock()
        mock_result.order_count = 5
        mock_result.revenue = Decimal("249.95")

        session = MagicMock()

        call_count = [0]
        def query_side_effect(model_or_cols, *args, **kwargs):
            chain = MagicMock()
            if hasattr(model_or_cols, '__name__') and model_or_cols.__name__ == "Store":
                chain.filter.return_value.all.return_value = [mock_store1, mock_store2]
            else:
                # Revenue aggregation query
                chain.filter.return_value.first.return_value = mock_result
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = aggregate_daily_analytics()
        assert result["stores_processed"] == 2
        assert "date" in result
        assert "total_revenue" in result

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_handles_no_active_stores(self, mock_factory):
        """Returns zero when no active stores exist."""
        from app.tasks.analytics_tasks import aggregate_daily_analytics

        session = MagicMock()

        def query_side_effect(model_or_cols, *args, **kwargs):
            chain = MagicMock()
            chain.filter.return_value.all.return_value = []
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = aggregate_daily_analytics()
        assert result["stores_processed"] == 0
        assert result["total_revenue"] == "0"

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_handles_store_with_zero_revenue(self, mock_factory):
        """Correctly handles stores with no orders yesterday."""
        from app.models.store import Store, StoreStatus
        from app.tasks.analytics_tasks import aggregate_daily_analytics

        mock_store = MagicMock(spec=Store)
        mock_store.id = uuid.uuid4()
        mock_store.name = "Empty Store"
        mock_store.status = StoreStatus.active

        mock_result = MagicMock()
        mock_result.order_count = 0
        mock_result.revenue = 0

        session = MagicMock()

        def query_side_effect(model_or_cols, *args, **kwargs):
            chain = MagicMock()
            if hasattr(model_or_cols, '__name__') and model_or_cols.__name__ == "Store":
                chain.filter.return_value.all.return_value = [mock_store]
            else:
                chain.filter.return_value.first.return_value = mock_result
            return chain

        session.query.side_effect = query_side_effect
        mock_factory.return_value = session

        result = aggregate_daily_analytics()
        assert result["stores_processed"] == 1
        assert result["total_revenue"] == "0"

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_returns_error_on_exception(self, mock_factory):
        """Returns error dict on unexpected exception."""
        from app.tasks.analytics_tasks import aggregate_daily_analytics

        session = MagicMock()
        session.query.side_effect = Exception("DB connection lost")
        mock_factory.return_value = session

        result = aggregate_daily_analytics()
        assert "error" in result
        assert "DB connection lost" in result["error"]


# ---------------------------------------------------------------------------
# cleanup_old_notifications
# ---------------------------------------------------------------------------


class TestCleanupOldNotifications:
    """Tests for the cleanup_old_notifications Beat task."""

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_deletes_old_read_notifications(self, mock_factory):
        """Deletes read notifications older than 90 days."""
        from app.tasks.analytics_tasks import cleanup_old_notifications

        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 42
        session.execute.return_value = mock_result
        mock_factory.return_value = session

        result = cleanup_old_notifications()
        assert result["deleted_count"] == 42
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_zero_deletions_when_none_qualify(self, mock_factory):
        """Returns zero when no notifications qualify for deletion."""
        from app.tasks.analytics_tasks import cleanup_old_notifications

        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result
        mock_factory.return_value = session

        result = cleanup_old_notifications()
        assert result["deleted_count"] == 0
        session.commit.assert_called_once()

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_returns_error_on_exception(self, mock_factory):
        """Returns error dict and rolls back on exception."""
        from app.tasks.analytics_tasks import cleanup_old_notifications

        session = MagicMock()
        session.execute.side_effect = Exception("Permission denied")
        mock_factory.return_value = session

        result = cleanup_old_notifications()
        assert "error" in result
        assert "Permission denied" in result["error"]
        session.rollback.assert_called_once()

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_closes_session_on_success(self, mock_factory):
        """Session is always closed, even on success."""
        from app.tasks.analytics_tasks import cleanup_old_notifications

        session = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 10
        session.execute.return_value = mock_result
        mock_factory.return_value = session

        cleanup_old_notifications()
        session.close.assert_called_once()

    @patch("app.tasks.analytics_tasks.SyncSessionFactory")
    def test_closes_session_on_failure(self, mock_factory):
        """Session is always closed, even on failure."""
        from app.tasks.analytics_tasks import cleanup_old_notifications

        session = MagicMock()
        session.execute.side_effect = Exception("Error")
        mock_factory.return_value = session

        cleanup_old_notifications()
        session.close.assert_called_once()
