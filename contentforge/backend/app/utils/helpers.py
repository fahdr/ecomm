"""
Common utility functions.

For Developers:
    Add service-agnostic helpers here. Service-specific utilities
    should go in the service's own utils module.
"""

from datetime import date


def get_current_billing_period() -> tuple[date, date]:
    """
    Get the current billing period (first of month to first of next month).

    Returns:
        Tuple of (period_start, period_end) as date objects.
    """
    today = date.today()
    period_start = today.replace(day=1)
    if today.month == 12:
        period_end = today.replace(year=today.year + 1, month=1, day=1)
    else:
        period_end = today.replace(month=today.month + 1, day=1)
    return period_start, period_end
