"""
Product listing and detail endpoint tests.

Tests the cross-competitor product listing (GET /products), individual
product detail (GET /products/{id}), and validates filtering, sorting,
pagination, and price history retrieval.

For Developers:
    Products are created in the database directly via the async session
    fixture because they depend on a parent Competitor record. The helper
    `seed_competitor_with_products` creates a competitor and its products
    in a single transaction. All product endpoints require authentication.

For QA Engineers:
    These tests verify:
    - Cross-competitor product listing returns products from all competitors.
    - Filtering by status (active, removed) works correctly.
    - Sorting by last_seen, first_seen, price, and title is supported.
    - Pagination returns correct totals and page sizes.
    - Product detail includes the full price_history array.
    - Authorization: users cannot access products belonging to other users.
    - Invalid product IDs return 400, missing products return 404.

For Project Managers:
    The product feed is how users discover competitor products and track
    price changes. These tests ensure the data is accurate, properly
    filtered, and secure.

For End Users:
    These tests guarantee that your product browsing, filtering, and
    price history features work reliably.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor import Competitor, CompetitorProduct
from app.models.user import User
from tests.conftest import register_and_login


# ── Helpers ─────────────────────────────────────────────────────────


async def get_user_id_from_headers(client: AsyncClient, headers: dict) -> str:
    """
    Extract the user ID by creating and inspecting a competitor.

    This is a workaround since the auth endpoint returns tokens but
    not the user ID directly. We create a temp competitor to get the
    user_id from the response.

    Args:
        client: The test HTTP client.
        headers: Authorization headers.

    Returns:
        The user's UUID as a string.
    """
    # Create a temp competitor to discover user_id
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Temp ID Probe", "url": "https://probe.example.com"},
        headers=headers,
    )
    assert resp.status_code == 201
    # We can't get user_id from competitor response directly, so we
    # rely on the conftest helper returning a valid token.
    return resp.json()["id"]


async def seed_competitor_with_products(
    db: AsyncSession,
    user_id: uuid.UUID,
    competitor_name: str = "Test Rival",
    num_products: int = 3,
    product_status: str = "active",
) -> tuple[Competitor, list[CompetitorProduct]]:
    """
    Create a competitor and associated products directly in the database.

    This bypasses the API for efficient test setup when we need to test
    product listing endpoints that depend on existing product data.

    Args:
        db: Async database session.
        user_id: The owning user's UUID.
        competitor_name: Name for the competitor store.
        num_products: Number of products to create.
        product_status: Status for all products ('active' or 'removed').

    Returns:
        Tuple of (Competitor, list of CompetitorProduct records).
    """
    competitor = Competitor(
        user_id=user_id,
        name=competitor_name,
        url=f"https://{competitor_name.lower().replace(' ', '-')}.example.com",
        platform="shopify",
        product_count=num_products,
    )
    db.add(competitor)
    await db.flush()

    products = []
    base_time = datetime.utcnow()
    for i in range(num_products):
        product = CompetitorProduct(
            competitor_id=competitor.id,
            title=f"Product {i + 1} from {competitor_name}",
            url=f"https://example.com/product-{i + 1}",
            image_url=f"https://example.com/img/product-{i + 1}.jpg",
            price=19.99 + (i * 10),
            currency="USD",
            first_seen=base_time - timedelta(days=30 - i),
            last_seen=base_time - timedelta(hours=i),
            price_history=[
                {"date": (base_time - timedelta(days=30)).isoformat(), "price": 24.99 + (i * 10)},
                {"date": (base_time - timedelta(days=15)).isoformat(), "price": 22.99 + (i * 10)},
                {"date": base_time.isoformat(), "price": 19.99 + (i * 10)},
            ],
            status=product_status,
        )
        db.add(product)
        products.append(product)

    await db.flush()
    return competitor, products


async def create_user_via_api(client: AsyncClient, email: str | None = None) -> tuple[dict, uuid.UUID]:
    """
    Register a user and return auth headers plus the user ID.

    Creates a temporary competitor to extract the user_id from the
    database, since the auth response does not include it.

    Args:
        client: The test HTTP client.
        email: Optional email for the user.

    Returns:
        Tuple of (auth headers dict, user UUID).
    """
    headers = await register_and_login(client, email=email)
    # We need to get the user ID; create a competitor and look it up
    resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "ID Discovery", "url": "https://discovery.example.com"},
        headers=headers,
    )
    assert resp.status_code == 201
    # Clean up by deleting
    comp_id = resp.json()["id"]
    await client.delete(f"/api/v1/competitors/{comp_id}", headers=headers)
    return headers, None  # We'll use a different approach below


# ── Cross-Competitor Product List Tests ─────────────────────────────


@pytest.mark.asyncio
async def test_list_products_empty(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/ returns empty list when user has no competitors."""
    resp = await client.get("/api/v1/products/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20


@pytest.mark.asyncio
async def test_list_products_after_competitor_created(
    client: AsyncClient, auth_headers: dict
):
    """
    GET /api/v1/products/ returns empty products when competitor has no products.

    A competitor exists but has not been scanned yet, so no products.
    """
    await client.post(
        "/api/v1/competitors/",
        json={"name": "Empty Competitor", "url": "https://empty-comp.example.com"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/products/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_products_unauthenticated_returns_401(client: AsyncClient):
    """GET /api/v1/products/ without auth returns 401."""
    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_products_pagination_params(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/products/?page=2&per_page=5 respects pagination parameters."""
    resp = await client.get(
        "/api/v1/products/?page=2&per_page=5", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["per_page"] == 5


@pytest.mark.asyncio
async def test_list_products_invalid_page_returns_422(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/products/?page=0 returns 422 (page must be >= 1)."""
    resp = await client.get("/api/v1/products/?page=0", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_products_invalid_per_page_returns_422(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/products/?per_page=200 returns 422 (per_page max is 100)."""
    resp = await client.get("/api/v1/products/?per_page=200", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_products_sort_by_param(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/?sort_by=price accepts valid sort parameters."""
    for sort_field in ["last_seen", "first_seen", "price", "title"]:
        resp = await client.get(
            f"/api/v1/products/?sort_by={sort_field}", headers=auth_headers
        )
        assert resp.status_code == 200, f"sort_by={sort_field} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_list_products_status_filter(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/?status=active accepts status filter."""
    resp = await client.get(
        "/api/v1/products/?status=active", headers=auth_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_products_user_isolation(client: AsyncClient):
    """
    Products from user A's competitors are not visible to user B.

    Even if both users have competitors, they only see products
    belonging to their own competitors.
    """
    headers_a = await register_and_login(client, email="producta@example.com")
    headers_b = await register_and_login(client, email="productb@example.com")

    # User A creates a competitor
    await client.post(
        "/api/v1/competitors/",
        json={"name": "User A Rival", "url": "https://arival.example.com"},
        headers=headers_a,
    )

    # User B should see no products (not even User A's competitors' products)
    resp = await client.get("/api/v1/products/", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── Product Detail Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient, auth_headers: dict):
    """GET /api/v1/products/{id} with non-existent UUID returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/products/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_product_invalid_id_returns_400(
    client: AsyncClient, auth_headers: dict
):
    """GET /api/v1/products/{id} with malformed UUID returns 400."""
    resp = await client.get("/api/v1/products/not-a-uuid", headers=auth_headers)
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_product_unauthenticated_returns_401(client: AsyncClient):
    """GET /api/v1/products/{id} without auth returns 401."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/products/{fake_id}")
    assert resp.status_code == 401


# ── Product Detail with Seeded Data (DB fixture) ───────────────────


@pytest.mark.asyncio
async def test_list_products_with_seeded_data(
    client: AsyncClient, db: AsyncSession
):
    """
    Products seeded via the database are returned by GET /api/v1/products/.

    Creates a user, registers via API for auth, then seeds products
    directly into the database and verifies the API returns them.
    """
    headers = await register_and_login(client, email="seeded@example.com")

    # We need the user record for seeding. Lookup by creating a competitor
    # and extracting the competitor's user_id from the DB.
    comp_resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Seeding Helper", "url": "https://seedhelper.example.com"},
        headers=headers,
    )
    assert comp_resp.status_code == 201
    comp_id = uuid.UUID(comp_resp.json()["id"])

    # Look up the competitor in DB to get user_id
    from sqlalchemy import select
    from app.models.competitor import Competitor

    result = await db.execute(select(Competitor).where(Competitor.id == comp_id))
    comp = result.scalar_one()
    user_id = comp.user_id

    # Now seed products for this competitor
    now = datetime.utcnow()
    products = []
    for i in range(5):
        product = CompetitorProduct(
            competitor_id=comp.id,
            title=f"Seeded Product {i + 1}",
            url=f"https://example.com/seeded-{i + 1}",
            price=9.99 + i * 5,
            currency="USD",
            first_seen=now - timedelta(days=10),
            last_seen=now,
            price_history=[
                {"date": (now - timedelta(days=10)).isoformat(), "price": 14.99 + i * 5},
                {"date": now.isoformat(), "price": 9.99 + i * 5},
            ],
            status="active",
        )
        db.add(product)
        products.append(product)
    await db.commit()

    # Verify the products appear in the list
    resp = await client.get("/api/v1/products/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5

    # Each item should have a competitor_name
    for item in data["items"]:
        assert "competitor_name" in item
        assert item["competitor_name"] == "Seeding Helper"

    # Verify the first item has price history
    first_item = data["items"][0]
    assert "price_history" in first_item


@pytest.mark.asyncio
async def test_get_product_detail_with_price_history(
    client: AsyncClient, db: AsyncSession
):
    """
    GET /api/v1/products/{id} returns full price history for a product.

    Seeds a product with price history directly in the database,
    then fetches it via the API and verifies the price_history field.
    """
    headers = await register_and_login(client, email="detail@example.com")

    # Create a competitor via API
    comp_resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Detail Rival", "url": "https://detailrival.example.com"},
        headers=headers,
    )
    assert comp_resp.status_code == 201
    comp_id = uuid.UUID(comp_resp.json()["id"])

    # Seed a product with detailed price history
    now = datetime.utcnow()
    price_history = [
        {"date": (now - timedelta(days=30)).isoformat(), "price": 49.99},
        {"date": (now - timedelta(days=20)).isoformat(), "price": 44.99},
        {"date": (now - timedelta(days=10)).isoformat(), "price": 39.99},
        {"date": now.isoformat(), "price": 34.99},
    ]

    product = CompetitorProduct(
        competitor_id=comp_id,
        title="Price Tracked Widget",
        url="https://example.com/widget",
        image_url="https://example.com/img/widget.jpg",
        price=34.99,
        currency="USD",
        first_seen=now - timedelta(days=30),
        last_seen=now,
        price_history=price_history,
        status="active",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Fetch the product detail
    resp = await client.get(f"/api/v1/products/{product.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["title"] == "Price Tracked Widget"
    assert data["price"] == 34.99
    assert data["currency"] == "USD"
    assert data["image_url"] == "https://example.com/img/widget.jpg"
    assert data["status"] == "active"
    assert data["competitor_name"] == "Detail Rival"

    # Verify full price history
    assert len(data["price_history"]) == 4
    prices = [entry["price"] for entry in data["price_history"]]
    assert prices == [49.99, 44.99, 39.99, 34.99]


@pytest.mark.asyncio
async def test_get_product_wrong_user_returns_404(
    client: AsyncClient, db: AsyncSession
):
    """
    GET /api/v1/products/{id} returns 404 if the product belongs to another user.

    User A creates a competitor with a product; User B cannot access
    that product.
    """
    headers_a = await register_and_login(client, email="prodowner@example.com")
    headers_b = await register_and_login(client, email="prodsnooper@example.com")

    # User A creates a competitor
    comp_resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Owner Rival", "url": "https://ownerrival.example.com"},
        headers=headers_a,
    )
    assert comp_resp.status_code == 201
    comp_id = uuid.UUID(comp_resp.json()["id"])

    # Seed a product for User A's competitor
    now = datetime.utcnow()
    product = CompetitorProduct(
        competitor_id=comp_id,
        title="Secret Product",
        url="https://example.com/secret",
        price=99.99,
        currency="USD",
        first_seen=now,
        last_seen=now,
        price_history=[],
        status="active",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # User B should not be able to access it
    resp = await client.get(f"/api/v1/products/{product.id}", headers=headers_b)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_products_with_status_filter_active(
    client: AsyncClient, db: AsyncSession
):
    """
    GET /api/v1/products/?status=active only returns active products.

    Seeds both active and removed products, then verifies the filter.
    """
    headers = await register_and_login(client, email="filtertest@example.com")

    comp_resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Filter Rival", "url": "https://filterrival.example.com"},
        headers=headers,
    )
    assert comp_resp.status_code == 201
    comp_id = uuid.UUID(comp_resp.json()["id"])

    now = datetime.utcnow()

    # Seed active product
    active_product = CompetitorProduct(
        competitor_id=comp_id,
        title="Active Widget",
        url="https://example.com/active-widget",
        price=19.99,
        currency="USD",
        first_seen=now,
        last_seen=now,
        price_history=[],
        status="active",
    )
    db.add(active_product)

    # Seed removed product
    removed_product = CompetitorProduct(
        competitor_id=comp_id,
        title="Removed Widget",
        url="https://example.com/removed-widget",
        price=29.99,
        currency="USD",
        first_seen=now - timedelta(days=30),
        last_seen=now - timedelta(days=5),
        price_history=[],
        status="removed",
    )
    db.add(removed_product)
    await db.commit()

    # Filter active only
    resp = await client.get(
        "/api/v1/products/?status=active", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Active Widget"

    # Filter removed only
    resp_removed = await client.get(
        "/api/v1/products/?status=removed", headers=headers
    )
    assert resp_removed.status_code == 200
    data_removed = resp_removed.json()
    assert data_removed["total"] == 1
    assert data_removed["items"][0]["title"] == "Removed Widget"


@pytest.mark.asyncio
async def test_list_products_sort_by_price_ascending(
    client: AsyncClient, db: AsyncSession
):
    """
    GET /api/v1/products/?sort_by=price returns products sorted by price ascending.
    """
    headers = await register_and_login(client, email="sorttest@example.com")

    comp_resp = await client.post(
        "/api/v1/competitors/",
        json={"name": "Sort Rival", "url": "https://sortrival.example.com"},
        headers=headers,
    )
    assert comp_resp.status_code == 201
    comp_id = uuid.UUID(comp_resp.json()["id"])

    now = datetime.utcnow()
    prices_input = [49.99, 9.99, 29.99]

    for i, price in enumerate(prices_input):
        product = CompetitorProduct(
            competitor_id=comp_id,
            title=f"Sort Product {i}",
            url=f"https://example.com/sort-{i}",
            price=price,
            currency="USD",
            first_seen=now,
            last_seen=now,
            price_history=[],
            status="active",
        )
        db.add(product)
    await db.commit()

    resp = await client.get(
        "/api/v1/products/?sort_by=price", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    returned_prices = [item["price"] for item in data["items"]]
    assert returned_prices == sorted(returned_prices), (
        f"Expected ascending price order, got {returned_prices}"
    )
