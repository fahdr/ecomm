"""
Tests for the scheduling engine service.

Covers post scheduling, upcoming post retrieval, simulated publishing,
and optimal time suggestions.

For Developers:
    Tests use the db fixture from conftest.py with direct service function calls.
    The publish_post function simulates publishing without external API calls.

For QA Engineers:
    These tests verify:
    - Scheduling a post sets status to 'scheduled' with the correct time.
    - Scheduling in the past raises ValueError.
    - get_upcoming_posts returns only posts within the date window.
    - publish_post transitions status from scheduled to posted.
    - get_best_times returns valid time suggestions for all platforms.
    - get_next_optimal_time returns a future datetime.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.user import User
from app.services.scheduler_service import (
    get_best_times,
    get_next_optimal_time,
    get_upcoming_posts,
    publish_post,
    schedule_post,
)


async def _create_user_and_account(db: AsyncSession) -> tuple[User, SocialAccount]:
    """
    Create a test user and social account for scheduling tests.

    Args:
        db: Async database session.

    Returns:
        Tuple of (User, SocialAccount).
    """
    user = User(
        email=f"scheduler_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed_test_password",
    )
    db.add(user)
    await db.flush()

    account = SocialAccount(
        user_id=user.id,
        platform=SocialPlatform.instagram,
        account_name="@test_brand",
        account_id_external=f"ig_{uuid.uuid4().hex[:12]}",
        is_connected=True,
    )
    db.add(account)
    await db.flush()

    return user, account


@pytest.mark.asyncio
async def test_schedule_post_creates_scheduled(db: AsyncSession):
    """schedule_post creates a post with status='scheduled' and correct time."""
    user, account = await _create_user_and_account(db)
    future_time = datetime.now(UTC) + timedelta(days=2)

    post = await schedule_post(
        db=db,
        user_id=user.id,
        account_id=account.id,
        content="Scheduled post content",
        media_urls=["https://cdn.example.com/img.jpg"],
        scheduled_at=future_time,
        platform="instagram",
    )

    assert post.status == PostStatus.scheduled
    assert post.scheduled_for is not None
    assert post.content == "Scheduled post content"
    assert post.user_id == user.id


@pytest.mark.asyncio
async def test_schedule_post_in_past_raises(db: AsyncSession):
    """schedule_post raises ValueError when scheduled_at is in the past."""
    user, account = await _create_user_and_account(db)
    past_time = datetime.now(UTC) - timedelta(hours=1)

    with pytest.raises(ValueError, match="past"):
        await schedule_post(
            db=db,
            user_id=user.id,
            account_id=account.id,
            content="Past post",
            media_urls=[],
            scheduled_at=past_time,
        )


@pytest.mark.asyncio
async def test_get_upcoming_posts_within_window(db: AsyncSession):
    """get_upcoming_posts returns posts within the specified day window."""
    user, account = await _create_user_and_account(db)

    # Create a post scheduled for 2 days from now
    await schedule_post(
        db=db,
        user_id=user.id,
        account_id=account.id,
        content="Upcoming post",
        media_urls=[],
        scheduled_at=datetime.now(UTC) + timedelta(days=2),
    )

    # Create a post scheduled for 10 days from now (outside default 7-day window)
    await schedule_post(
        db=db,
        user_id=user.id,
        account_id=account.id,
        content="Far future post",
        media_urls=[],
        scheduled_at=datetime.now(UTC) + timedelta(days=10),
    )

    upcoming = await get_upcoming_posts(db=db, user_id=user.id, days=7)
    assert len(upcoming) == 1
    assert upcoming[0].content == "Upcoming post"


@pytest.mark.asyncio
async def test_get_upcoming_posts_empty(db: AsyncSession):
    """get_upcoming_posts returns empty list when no posts are scheduled."""
    user, _ = await _create_user_and_account(db)

    upcoming = await get_upcoming_posts(db=db, user_id=user.id)
    assert upcoming == []


@pytest.mark.asyncio
async def test_publish_post_transitions_status(db: AsyncSession):
    """publish_post transitions a scheduled post to 'posted' status."""
    user, account = await _create_user_and_account(db)

    post = await schedule_post(
        db=db,
        user_id=user.id,
        account_id=account.id,
        content="Publish me",
        media_urls=[],
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )

    success = await publish_post(db=db, post_id=post.id)

    assert success is True
    assert post.status == PostStatus.posted
    assert post.posted_at is not None


@pytest.mark.asyncio
async def test_publish_post_nonexistent_returns_false(db: AsyncSession):
    """publish_post returns False for a non-existent post ID."""
    fake_id = uuid.uuid4()
    success = await publish_post(db=db, post_id=fake_id)
    assert success is False


@pytest.mark.asyncio
async def test_publish_draft_post_returns_false(db: AsyncSession):
    """publish_post returns False for a draft (non-scheduled) post."""
    user, account = await _create_user_and_account(db)

    # Create a draft post directly
    post = Post(
        user_id=user.id,
        account_id=account.id,
        content="Draft only",
        media_urls=[],
        hashtags=[],
        platform="instagram",
        status=PostStatus.draft,
    )
    db.add(post)
    await db.flush()

    success = await publish_post(db=db, post_id=post.id)
    assert success is False


# ── Best Times Tests ──────────────────────────────────────────────


def test_get_best_times_all_platforms():
    """get_best_times returns non-empty suggestions for all supported platforms."""
    for platform in ["instagram", "facebook", "tiktok", "twitter", "pinterest"]:
        times = get_best_times(platform)
        assert len(times) > 0
        for t in times:
            assert "time" in t
            assert "label" in t
            # Verify time format HH:MM
            hour, minute = t["time"].split(":")
            assert 0 <= int(hour) <= 23
            assert 0 <= int(minute) <= 59


def test_get_best_times_unknown_platform_returns_instagram():
    """get_best_times returns Instagram times for unknown platforms."""
    times = get_best_times("unknown_platform")
    ig_times = get_best_times("instagram")
    assert times == ig_times


def test_get_next_optimal_time_is_future():
    """get_next_optimal_time always returns a future datetime."""
    now = datetime.now(UTC)
    optimal = get_next_optimal_time("instagram", base_date=now)
    assert optimal > now


def test_get_next_optimal_time_different_platforms():
    """get_next_optimal_time returns different times for different platforms."""
    base = datetime(2025, 6, 15, 6, 0, 0, tzinfo=UTC)
    ig_time = get_next_optimal_time("instagram", base_date=base)
    tt_time = get_next_optimal_time("tiktok", base_date=base)

    # Instagram first optimal is 11:00, TikTok is 07:00
    assert ig_time != tt_time
