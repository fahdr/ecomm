"""
Tests for the metrics tracking service and API endpoint.

Covers recording metrics, retrieving post performance, account analytics,
and the POST /api/v1/posts/{id}/metrics endpoint.

For Developers:
    Tests use direct service calls and HTTP endpoint tests. The fixture
    creates a user, account, and post to record metrics against.

For QA Engineers:
    These tests verify:
    - Recording metrics creates a PostMetrics record.
    - Recording metrics a second time updates (upsert) the existing record.
    - Engagement rate is correctly calculated.
    - get_post_performance returns None for posts without metrics.
    - get_account_analytics returns zeroed data when no posts exist.
    - The POST /api/v1/posts/{id}/metrics endpoint records and returns metrics.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, PostStatus
from app.models.social_account import SocialAccount, SocialPlatform
from app.models.user import User
from app.services.metrics_service import (
    get_account_analytics,
    get_post_performance,
    record_metrics,
)
from tests.conftest import register_and_login


async def _create_test_post(db: AsyncSession) -> tuple[User, SocialAccount, Post]:
    """
    Create a user, account, and post for metrics tests.

    Args:
        db: Async database session.

    Returns:
        Tuple of (User, SocialAccount, Post).
    """
    user = User(
        email=f"metrics_{uuid.uuid4().hex[:8]}@test.com",
        hashed_password="hashed_test",
    )
    db.add(user)
    await db.flush()

    account = SocialAccount(
        user_id=user.id,
        platform=SocialPlatform.instagram,
        account_name="@metrics_brand",
        account_id_external=f"ig_{uuid.uuid4().hex[:12]}",
        is_connected=True,
    )
    db.add(account)
    await db.flush()

    post = Post(
        user_id=user.id,
        account_id=account.id,
        content="Metrics test post",
        media_urls=[],
        hashtags=[],
        platform="instagram",
        status=PostStatus.posted,
    )
    db.add(post)
    await db.flush()

    return user, account, post


# ── Service Function Tests ────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_metrics_creates_new(db: AsyncSession):
    """record_metrics creates a new PostMetrics record for a post."""
    _, _, post = await _create_test_post(db)

    metrics = await record_metrics(
        db=db,
        post_id=post.id,
        metrics_data={
            "impressions": 1000,
            "reach": 800,
            "likes": 50,
            "comments": 10,
            "shares": 5,
            "clicks": 20,
        },
    )

    assert metrics.post_id == post.id
    assert metrics.impressions == 1000
    assert metrics.reach == 800
    assert metrics.likes == 50
    assert metrics.comments == 10
    assert metrics.shares == 5
    assert metrics.clicks == 20


@pytest.mark.asyncio
async def test_record_metrics_upsert(db: AsyncSession):
    """record_metrics updates existing metrics on second call (upsert)."""
    _, _, post = await _create_test_post(db)

    # First recording
    await record_metrics(
        db=db,
        post_id=post.id,
        metrics_data={"impressions": 100, "likes": 10},
    )

    # Second recording (update)
    metrics = await record_metrics(
        db=db,
        post_id=post.id,
        metrics_data={"impressions": 500, "likes": 50, "comments": 20},
    )

    assert metrics.impressions == 500
    assert metrics.likes == 50
    assert metrics.comments == 20


@pytest.mark.asyncio
async def test_record_metrics_nonexistent_post(db: AsyncSession):
    """record_metrics raises ValueError for a non-existent post."""
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await record_metrics(
            db=db,
            post_id=fake_id,
            metrics_data={"impressions": 100},
        )


@pytest.mark.asyncio
async def test_get_post_performance(db: AsyncSession):
    """get_post_performance returns metrics with computed engagement rate."""
    _, _, post = await _create_test_post(db)

    await record_metrics(
        db=db,
        post_id=post.id,
        metrics_data={
            "impressions": 1000,
            "likes": 50,
            "comments": 10,
            "shares": 5,
        },
    )

    performance = await get_post_performance(db=db, post_id=post.id)

    assert performance is not None
    assert performance["impressions"] == 1000
    # engagement_rate = (50 + 10 + 5) / 1000 * 100 = 6.5
    assert performance["engagement_rate"] == 6.5


@pytest.mark.asyncio
async def test_get_post_performance_no_metrics(db: AsyncSession):
    """get_post_performance returns None when no metrics exist."""
    _, _, post = await _create_test_post(db)

    performance = await get_post_performance(db=db, post_id=post.id)
    assert performance is None


@pytest.mark.asyncio
async def test_get_post_performance_zero_impressions(db: AsyncSession):
    """get_post_performance returns 0.0 engagement rate with zero impressions."""
    _, _, post = await _create_test_post(db)

    await record_metrics(
        db=db,
        post_id=post.id,
        metrics_data={"impressions": 0, "likes": 0},
    )

    performance = await get_post_performance(db=db, post_id=post.id)
    assert performance["engagement_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_account_analytics_empty(db: AsyncSession):
    """get_account_analytics returns zeroed data when no posts exist."""
    _, account, _ = await _create_test_post(db)

    # Use a different account with no posts
    empty_account = SocialAccount(
        user_id=account.user_id,
        platform=SocialPlatform.facebook,
        account_name="@empty_brand",
        account_id_external=f"fb_{uuid.uuid4().hex[:12]}",
        is_connected=True,
    )
    db.add(empty_account)
    await db.flush()

    analytics = await get_account_analytics(db=db, account_id=empty_account.id)

    assert analytics["total_posts"] == 0
    assert analytics["total_impressions"] == 0
    assert analytics["avg_engagement_rate"] == 0.0
    assert analytics["period_days"] == 30


# ── API Endpoint Tests ────────────────────────────────────────────


@pytest_asyncio.fixture
async def auth_post_with_account(client: AsyncClient) -> tuple[dict, str]:
    """
    Create a user, connect an account, and create a post for metrics API tests.

    Returns:
        Tuple of (auth_headers, post_id).
    """
    headers = await register_and_login(client)

    # Connect account
    acct_resp = await client.post(
        "/api/v1/accounts",
        json={
            "platform": "instagram",
            "account_name": "@metrics_api_brand",
        },
        headers=headers,
    )
    account_id = acct_resp.json()["id"]

    # Create a post
    post_resp = await client.post(
        "/api/v1/posts",
        json={
            "account_id": account_id,
            "content": "Post for metrics testing",
            "platform": "instagram",
        },
        headers=headers,
    )
    post_id = post_resp.json()["id"]

    return headers, post_id


@pytest.mark.asyncio
async def test_record_metrics_api(
    client: AsyncClient, auth_post_with_account: tuple[dict, str]
):
    """POST /api/v1/posts/{id}/metrics records metrics and returns response."""
    headers, post_id = auth_post_with_account

    resp = await client.post(
        f"/api/v1/posts/{post_id}/metrics",
        json={
            "impressions": 2000,
            "reach": 1500,
            "likes": 100,
            "comments": 25,
            "shares": 10,
            "clicks": 50,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["post_id"] == post_id
    assert data["impressions"] == 2000
    assert data["likes"] == 100
    # engagement_rate = (100 + 25 + 10) / 2000 * 100 = 6.75
    assert data["engagement_rate"] == 6.75


@pytest.mark.asyncio
async def test_record_metrics_api_nonexistent_post(
    client: AsyncClient,
):
    """POST /api/v1/posts/{random_id}/metrics returns 404 for unknown post."""
    headers = await register_and_login(client)
    fake_id = str(uuid.uuid4())

    resp = await client.post(
        f"/api/v1/posts/{fake_id}/metrics",
        json={"impressions": 100, "likes": 10},
        headers=headers,
    )
    assert resp.status_code == 404
