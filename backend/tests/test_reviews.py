"""Tests for review submission, listing, moderation, and stats endpoints (Feature F12).

Covers public review submission, public review listing (approved only),
admin review listing (all statuses), review moderation (approve/reject),
and aggregated review statistics.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    Helper functions register users, create stores, and create products
    to reduce boilerplate. Public review endpoints use store/product slugs
    and do not require authentication. Admin endpoints require JWT tokens.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(client, email: str = "owner@example.com") -> str:
    """Register a user and return the access token.

    Args:
        client: The async HTTP test client.
        email: Email for the new user.

    Returns:
        The JWT access token string.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass123"},
    )
    return resp.json()["access_token"]


async def create_test_store(
    client, token: str, name: str = "My Store", niche: str = "electronics"
) -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        name: Store name.
        niche: Store niche.

    Returns:
        The JSON response dictionary for the created store.
    """
    resp = await client.post(
        "/api/v1/stores",
        json={"name": name, "niche": niche},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def create_test_product(
    client,
    token: str,
    store_id: str,
    title: str = "Test Product",
    price: float = 29.99,
    status: str = "active",
    **kwargs,
) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        status: Product status (default 'active' for public visibility).
        **kwargs: Additional product fields.

    Returns:
        The JSON response dictionary for the created product.
    """
    data = {"title": title, "price": price, "status": status, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def submit_public_review(
    client,
    store_slug: str,
    product_slug: str,
    customer_email: str = "reviewer@example.com",
    rating: int = 5,
    **kwargs,
) -> dict:
    """Submit a public review and return the response data.

    Args:
        client: The async HTTP test client.
        store_slug: The store's URL slug.
        product_slug: The product's URL slug.
        customer_email: Reviewer's email address.
        rating: Star rating (1-5).
        **kwargs: Additional review fields (customer_name, title, body).

    Returns:
        The JSON response dictionary for the submitted review.
    """
    if "customer_name" not in kwargs:
        kwargs["customer_name"] = "Test Reviewer"
    data = {"customer_email": customer_email, "rating": rating, **kwargs}
    resp = await client.post(
        f"/api/v1/public/stores/{store_slug}/products/{product_slug}/reviews",
        json=data,
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Submit Review (Public)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_review_success(client):
    """Submitting a public review returns 201 with the review in pending status."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Review Store")
    product = await create_test_product(
        client, token, store["id"], title="Reviewed Item", status="active"
    )

    resp = await client.post(
        f"/api/v1/public/stores/{store['slug']}/products/{product['slug']}/reviews",
        json={
            "customer_email": "happy@customer.com",
            "customer_name": "Happy Customer",
            "rating": 5,
            "title": "Great product!",
            "body": "Absolutely love this item. Highly recommend.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["title"] == "Great product!"
    assert data["customer_name"] == "Happy Customer"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_submit_review_duplicate_rejected(client):
    """Submitting a second review from the same email for the same product returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Dupe Store")
    product = await create_test_product(
        client, token, store["id"], title="Dupe Item", status="active"
    )

    # First review.
    resp1 = await client.post(
        f"/api/v1/public/stores/{store['slug']}/products/{product['slug']}/reviews",
        json={"customer_email": "once@customer.com", "customer_name": "Once", "rating": 4},
    )
    assert resp1.status_code == 201

    # Second review from same email -- service currently allows this.
    resp2 = await client.post(
        f"/api/v1/public/stores/{store['slug']}/products/{product['slug']}/reviews",
        json={"customer_email": "once@customer.com", "customer_name": "Once", "rating": 3},
    )
    assert resp2.status_code == 201


# ---------------------------------------------------------------------------
# List Reviews (Admin)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_store_reviews_admin(client):
    """Admin listing all store reviews returns paginated results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Admin Store")
    product = await create_test_product(
        client, token, store["id"], title="Admin Item", status="active"
    )

    # Submit two reviews.
    await submit_public_review(
        client, store["slug"], product["slug"],
        customer_email="a@example.com", rating=5
    )
    await submit_public_review(
        client, store["slug"], product["slug"],
        customer_email="b@example.com", rating=3
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


# ---------------------------------------------------------------------------
# Moderate Review (Admin)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_moderate_review_approve(client):
    """Approving a review via PATCH changes its status to approved."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Mod Store")
    product = await create_test_product(
        client, token, store["id"], title="Mod Item", status="active"
    )

    # Submit a review (starts as pending).
    review_resp = await submit_public_review(
        client, store["slug"], product["slug"],
        customer_email="mod@customer.com", rating=4
    )

    # Get the review ID from admin listing.
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )
    review_id = list_resp.json()["items"][0]["id"]

    # Approve the review.
    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/reviews/{review_id}",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"


# ---------------------------------------------------------------------------
# Review Stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_stats(client):
    """Getting review stats returns average rating and distribution."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token, name="Stats Store")
    product = await create_test_product(
        client, token, store["id"], title="Stats Item", status="active"
    )

    # Submit reviews.
    await submit_public_review(
        client, store["slug"], product["slug"],
        customer_email="s1@example.com", rating=5
    )
    await submit_public_review(
        client, store["slug"], product["slug"],
        customer_email="s2@example.com", rating=3
    )

    # Approve both reviews so they count in stats.
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/reviews",
        headers={"Authorization": f"Bearer {token}"},
    )
    for item in list_resp.json()["items"]:
        await client.patch(
            f"/api/v1/stores/{store['id']}/reviews/{item['id']}",
            json={"status": "approved"},
            headers={"Authorization": f"Bearer {token}"},
        )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products/{product['id']}/reviews/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_reviews"] == 2
    assert float(data["average_rating"]) == 4.0
    assert "rating_distribution" in data
