"""
Tests for the content calendar API endpoint.

Covers the calendar view with suggested posting times per platform,
and verifies the enhanced CalendarView response format.

For Developers:
    Tests use the HTTP client with auth fixtures. Posts must be scheduled
    to appear in the calendar view.

For QA Engineers:
    These tests verify:
    - GET /api/v1/posts/calendar returns suggested_times per platform.
    - Calendar days include SuggestedTime entries for all platforms.
    - The calendar correctly groups posts by date.

For Project Managers:
    The content calendar with suggested times helps users plan their
    social media posting schedule for maximum engagement.

For End Users:
    View your content calendar with optimal posting time suggestions
    for each social media platform.
"""

from datetime import datetime, timedelta, UTC

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import register_and_login


@pytest_asyncio.fixture
async def auth_and_account(client: AsyncClient) -> tuple[dict, str]:
    """
    Register a user and connect an Instagram account.

    Returns:
        Tuple of (auth_headers dict, account_id string).
    """
    headers = await register_and_login(client)

    account_resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@calendar_test_brand",
        },
        headers=headers,
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    return headers, account_id


@pytest.mark.asyncio
async def test_calendar_includes_suggested_times(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """GET /api/v1/posts/calendar includes suggested_times in day entries."""
    headers, account_id = auth_and_account

    # Create a scheduled post
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    await client.post(
        "/api/v1/posts",
        json={
            "account_id": account_id,
            "content": "Calendar test post",
            "platform": "instagram",
            "scheduled_for": tomorrow.isoformat(),
        },
        headers=headers,
    )

    start = datetime.now(UTC).strftime("%Y-%m-%d")
    end = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")

    resp = await client.get(
        f"/api/v1/posts/calendar?start_date={start}&end_date={end}",
        headers=headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["total_posts"] == 1
    assert len(data["days"]) >= 1

    # Check suggested times are included
    day = data["days"][0]
    assert "suggested_times" in day
    assert len(day["suggested_times"]) > 0

    # Verify suggested time structure
    sample_time = day["suggested_times"][0]
    assert "platform" in sample_time
    assert "time" in sample_time
    assert "label" in sample_time


@pytest.mark.asyncio
async def test_calendar_suggested_times_cover_all_platforms(
    client: AsyncClient, auth_and_account: tuple[dict, str]
):
    """Calendar suggested times include entries for all 5 supported platforms."""
    headers, account_id = auth_and_account

    # Create a scheduled post to get calendar data
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    await client.post(
        "/api/v1/posts",
        json={
            "account_id": account_id,
            "content": "Platform coverage test",
            "platform": "instagram",
            "scheduled_for": tomorrow.isoformat(),
        },
        headers=headers,
    )

    start = datetime.now(UTC).strftime("%Y-%m-%d")
    end = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")

    resp = await client.get(
        f"/api/v1/posts/calendar?start_date={start}&end_date={end}",
        headers=headers,
    )
    data = resp.json()

    day = data["days"][0]
    platforms_in_suggestions = {t["platform"] for t in day["suggested_times"]}
    expected_platforms = {"instagram", "facebook", "tiktok", "twitter", "pinterest"}
    assert platforms_in_suggestions == expected_platforms
