"""
Alert service — CRUD operations and alert triggering logic.

Handles creating, reading, updating, and deleting price alerts,
and checking whether alerts should trigger based on scan results.

For Developers:
    The `check_alerts_for_scan` function is called after each scan to
    evaluate whether any active alerts should trigger. It compares
    scan results against alert thresholds and creates AlertHistory
    records when conditions are met.

For QA Engineers:
    Test alert CRUD via /api/v1/alerts endpoints. Verify alert
    triggering by creating an alert, running a scan that meets the
    threshold, and checking the alert history.

For Project Managers:
    Alerts are a key engagement feature — they keep users coming back
    by notifying them of important competitor changes.

For End Users:
    Set up alerts to be notified when competitors change prices,
    add new products, or have items go out of stock.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import AlertHistory, PriceAlert
from app.models.competitor import Competitor, CompetitorProduct
from app.models.scan import ScanResult


async def create_alert(
    db: AsyncSession,
    user_id: uuid.UUID,
    alert_type: str,
    competitor_product_id: uuid.UUID | None = None,
    competitor_id: uuid.UUID | None = None,
    threshold: float | None = None,
) -> PriceAlert:
    """
    Create a new price alert for the user.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        alert_type: Type of alert ('price_drop', 'price_increase',
            'new_product', 'out_of_stock', 'back_in_stock').
        competitor_product_id: Optional product to monitor.
        competitor_id: Optional competitor to monitor.
        threshold: Percentage threshold for price alerts.

    Returns:
        The newly created PriceAlert record.
    """
    alert = PriceAlert(
        user_id=user_id,
        alert_type=alert_type,
        competitor_product_id=competitor_product_id,
        competitor_id=competitor_id,
        threshold=threshold,
    )
    db.add(alert)
    await db.flush()
    return alert


async def list_alerts(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    per_page: int = 20,
    is_active: bool | None = None,
) -> tuple[list[PriceAlert], int]:
    """
    List alerts for a user with pagination.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        page: Page number (1-based).
        per_page: Items per page.
        is_active: Optional filter for active/inactive alerts.

    Returns:
        Tuple of (list of PriceAlert records, total count).
    """
    base_filter = PriceAlert.user_id == user_id
    if is_active is not None:
        base_filter = base_filter & (PriceAlert.is_active == is_active)

    count_result = await db.execute(
        select(func.count(PriceAlert.id)).where(base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(PriceAlert)
        .where(base_filter)
        .order_by(PriceAlert.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    alerts = list(result.scalars().all())

    return alerts, total


async def get_alert(
    db: AsyncSession, user_id: uuid.UUID, alert_id: uuid.UUID
) -> PriceAlert | None:
    """
    Get a single alert by ID, scoped to the user.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        alert_id: The alert's UUID.

    Returns:
        The PriceAlert if found and owned by the user, None otherwise.
    """
    result = await db.execute(
        select(PriceAlert).where(
            PriceAlert.id == alert_id,
            PriceAlert.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_alert(
    db: AsyncSession,
    user_id: uuid.UUID,
    alert_id: uuid.UUID,
    alert_type: str | None = None,
    threshold: float | None = ...,
    is_active: bool | None = None,
) -> PriceAlert | None:
    """
    Update an alert's fields.

    Uses sentinel value (...) for threshold to distinguish between
    "not provided" and "set to None".

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        alert_id: The alert's UUID.
        alert_type: Updated alert type (optional).
        threshold: Updated threshold (... = not provided, None = clear).
        is_active: Updated active status (optional).

    Returns:
        The updated PriceAlert record, or None if not found.
    """
    alert = await get_alert(db, user_id, alert_id)
    if not alert:
        return None

    if alert_type is not None:
        alert.alert_type = alert_type
    if threshold is not ...:
        alert.threshold = threshold
    if is_active is not None:
        alert.is_active = is_active

    await db.flush()
    return alert


async def delete_alert(
    db: AsyncSession, user_id: uuid.UUID, alert_id: uuid.UUID
) -> bool:
    """
    Delete an alert and its history.

    Args:
        db: Async database session.
        user_id: The user's UUID (for authorization).
        alert_id: The alert's UUID.

    Returns:
        True if the alert was deleted, False if not found.
    """
    alert = await get_alert(db, user_id, alert_id)
    if not alert:
        return False

    await db.delete(alert)
    await db.flush()
    return True


async def list_alert_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    alert_id: uuid.UUID | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[AlertHistory], int]:
    """
    List alert history entries for a user with pagination.

    Optionally filter by a specific alert. Results are ordered by
    creation time (most recent first).

    Args:
        db: Async database session.
        user_id: The user's UUID.
        alert_id: Optional alert filter.
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Tuple of (list of AlertHistory records, total count).
    """
    # Get user's alert IDs
    alert_query = select(PriceAlert.id).where(PriceAlert.user_id == user_id)
    if alert_id:
        alert_query = alert_query.where(PriceAlert.id == alert_id)

    alert_result = await db.execute(alert_query)
    alert_ids = [row[0] for row in alert_result.all()]

    if not alert_ids:
        return [], 0

    base_filter = AlertHistory.alert_id.in_(alert_ids)

    count_result = await db.execute(
        select(func.count(AlertHistory.id)).where(base_filter)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * per_page
    result = await db.execute(
        select(AlertHistory)
        .where(base_filter)
        .order_by(AlertHistory.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    history = list(result.scalars().all())

    return history, total


async def check_alerts_for_scan(
    db: AsyncSession, scan_result_id: uuid.UUID
) -> list[AlertHistory]:
    """
    Check if any alerts should trigger based on a scan result.

    Evaluates all active alerts for the scanned competitor against
    the scan results. Creates AlertHistory entries for triggered alerts.

    Logic:
    - new_product alerts: trigger if scan found new products
    - price_drop alerts: trigger if scan found price decreases
    - price_increase alerts: trigger if scan found price increases
    - out_of_stock alerts: trigger if scan found removed products
    - back_in_stock alerts: trigger if scan found new products (re-appeared)

    Args:
        db: Async database session.
        scan_result_id: The scan result to check against.

    Returns:
        List of newly created AlertHistory records.
    """
    # Load scan result
    scan_query = await db.execute(
        select(ScanResult).where(ScanResult.id == scan_result_id)
    )
    scan = scan_query.scalar_one_or_none()
    if not scan:
        return []

    # Load competitor to get user_id
    comp_query = await db.execute(
        select(Competitor).where(Competitor.id == scan.competitor_id)
    )
    competitor = comp_query.scalar_one_or_none()
    if not competitor:
        return []

    # Get all active alerts for this user
    alert_query = await db.execute(
        select(PriceAlert).where(
            PriceAlert.user_id == competitor.user_id,
            PriceAlert.is_active.is_(True),
            (
                (PriceAlert.competitor_id == scan.competitor_id)
                | (PriceAlert.competitor_id.is_(None))
            ),
        )
    )
    alerts = list(alert_query.scalars().all())

    now = datetime.now(UTC)
    triggered: list[AlertHistory] = []

    for alert in alerts:
        should_trigger = False
        message = ""
        data: dict = {}

        if alert.alert_type == "new_product" and scan.new_products_count > 0:
            should_trigger = True
            message = (
                f"{scan.new_products_count} new product(s) found on "
                f"{competitor.name}"
            )
            data = {
                "new_products": scan.new_products_count,
                "competitor": competitor.name,
            }

        elif alert.alert_type == "price_drop" and scan.price_changes_count > 0:
            should_trigger = True
            message = (
                f"{scan.price_changes_count} price change(s) detected on "
                f"{competitor.name}"
            )
            data = {
                "price_changes": scan.price_changes_count,
                "competitor": competitor.name,
            }

        elif alert.alert_type == "price_increase" and scan.price_changes_count > 0:
            should_trigger = True
            message = (
                f"{scan.price_changes_count} price change(s) detected on "
                f"{competitor.name}"
            )
            data = {
                "price_changes": scan.price_changes_count,
                "competitor": competitor.name,
            }

        elif alert.alert_type == "out_of_stock" and scan.removed_products_count > 0:
            should_trigger = True
            message = (
                f"{scan.removed_products_count} product(s) removed from "
                f"{competitor.name}"
            )
            data = {
                "removed_products": scan.removed_products_count,
                "competitor": competitor.name,
            }

        elif alert.alert_type == "back_in_stock" and scan.new_products_count > 0:
            should_trigger = True
            message = (
                f"{scan.new_products_count} product(s) appeared on "
                f"{competitor.name}"
            )
            data = {
                "new_products": scan.new_products_count,
                "competitor": competitor.name,
            }

        if should_trigger:
            history_entry = AlertHistory(
                alert_id=alert.id,
                message=message,
                data=data,
            )
            db.add(history_entry)
            alert.last_triggered = now
            triggered.append(history_entry)

    await db.flush()
    return triggered
