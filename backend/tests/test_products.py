"""Tests for product CRUD and public product endpoints.

Covers product creation, listing (pagination, search, status filter),
retrieval, update, soft-delete, slug generation, store scoping,
variant management, image upload, and public product endpoints.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Helper functions register users and create stores/products to reduce
    boilerplate. Tests verify tenant isolation, pagination, and that
    sensitive fields (cost, store_id) are excluded from public responses.
"""

import io

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
    **kwargs,
) -> dict:
    """Create a product and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        title: Product title.
        price: Product price.
        **kwargs: Additional product fields.

    Returns:
        The JSON response dictionary for the created product.
    """
    data = {"title": title, "price": price, **kwargs}
    resp = await client.post(
        f"/api/v1/stores/{store_id}/products",
        json=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Product CRUD Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_product(client):
    """Creating a product returns 201 with slug and default draft status."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={"title": "Widget Pro", "price": 49.99, "description": "A great widget"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Widget Pro"
    assert data["slug"] == "widget-pro"
    assert data["price"] == "49.99"
    assert data["status"] == "draft"
    assert data["store_id"] == store["id"]
    assert data["description"] == "A great widget"


@pytest.mark.anyio
async def test_create_product_with_variants(client):
    """Creating a product with variants includes them in the response."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={
            "title": "T-Shirt",
            "price": 25.00,
            "variants": [
                {"name": "Small", "sku": "TS-S", "price": 25.00, "inventory_count": 10},
                {"name": "Large", "sku": "TS-L", "price": 27.00, "inventory_count": 5},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["variants"]) == 2
    names = {v["name"] for v in data["variants"]}
    assert names == {"Small", "Large"}


@pytest.mark.anyio
async def test_create_product_auto_slug_collision(client):
    """Products with the same title get unique slugs (-2, -3, etc.)."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    p1 = await create_test_product(client, token, store["id"], title="Widget")
    p2 = await create_test_product(client, token, store["id"], title="Widget")

    assert p1["slug"] == "widget"
    assert p2["slug"] == "widget-2"


@pytest.mark.anyio
async def test_list_products_empty(client):
    """Listing products for a store with none returns empty items."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.anyio
async def test_list_products_pagination(client):
    """Products are paginated correctly."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    for i in range(5):
        await create_test_product(
            client, token, store["id"], title=f"Product {i}", price=10.00
        )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products?page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3


@pytest.mark.anyio
async def test_list_products_search(client):
    """Search filters products by title (case-insensitive)."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_product(client, token, store["id"], title="Red Widget")
    await create_test_product(client, token, store["id"], title="Blue Gadget")

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products?search=widget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Red Widget"


@pytest.mark.anyio
async def test_list_products_status_filter(client):
    """Status filter returns only products with that status."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_product(client, token, store["id"], title="Draft One")
    await create_test_product(
        client, token, store["id"], title="Active One", status="active"
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products?status=active",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Active One"


@pytest.mark.anyio
async def test_list_products_excludes_archived(client):
    """Archived products are excluded from default listing."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    product = await create_test_product(client, token, store["id"], title="To Delete")

    # Soft-delete
    await client.delete(
        f"/api/v1/stores/{store['id']}/products/{product['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.anyio
async def test_get_product(client):
    """Retrieving a product by ID returns its full data with variants."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    product = await create_test_product(client, token, store["id"])

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products/{product['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == product["id"]


@pytest.mark.anyio
async def test_get_product_not_found(client):
    """Requesting a non-existent product returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_update_product(client):
    """Updating a product changes only the provided fields."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    product = await create_test_product(client, token, store["id"], title="Old Title")

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/products/{product['id']}",
        json={"title": "New Title", "price": 99.99},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    assert data["price"] == "99.99"
    assert data["slug"] == "new-title"


@pytest.mark.anyio
async def test_update_product_replace_variants(client):
    """Providing variants in an update replaces existing variants."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    product = await create_test_product(
        client,
        token,
        store["id"],
        variants=[{"name": "Original", "inventory_count": 5}],
    )
    assert len(product["variants"]) == 1

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/products/{product['id']}",
        json={
            "variants": [
                {"name": "New A", "inventory_count": 10},
                {"name": "New B", "inventory_count": 20},
            ]
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["variants"]) == 2
    names = {v["name"] for v in data["variants"]}
    assert names == {"New A", "New B"}


@pytest.mark.anyio
async def test_delete_product_soft_delete(client):
    """Deleting a product sets its status to archived."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    product = await create_test_product(client, token, store["id"])

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/products/{product['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.anyio
async def test_product_requires_auth(client):
    """Product endpoints return 401 without authentication."""
    resp = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/products"
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_product_wrong_store_owner(client):
    """A user cannot access products in another user's store."""
    token_a = await register_and_get_token(client, email="owner_a@example.com")
    token_b = await register_and_get_token(client, email="owner_b@example.com")

    store = await create_test_store(client, token_a)
    product = await create_test_product(client, token_a, store["id"])

    # User B tries to list products
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # User B tries to get product
    resp = await client.get(
        f"/api/v1/stores/{store['id']}/products/{product['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_product_create_with_all_fields(client):
    """Creating a product with all optional fields works correctly."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products",
        json={
            "title": "Premium Widget",
            "description": "The best widget money can buy",
            "price": 99.99,
            "compare_at_price": 149.99,
            "cost": 30.00,
            "images": ["/uploads/img1.jpg", "/uploads/img2.jpg"],
            "status": "active",
            "seo_title": "Buy Premium Widget | My Store",
            "seo_description": "Get the best widget at an amazing price",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["compare_at_price"] == "149.99"
    assert data["cost"] == "30.00"
    assert len(data["images"]) == 2
    assert data["status"] == "active"
    assert data["seo_title"] == "Buy Premium Widget | My Store"


# ---------------------------------------------------------------------------
# Image Upload Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_upload_image(client):
    """Uploading an image returns a URL path."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products/upload",
        files={"file": ("test.png", fake_image, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"].startswith(f"/uploads/{store['id']}/")
    assert data["url"].endswith(".png")


@pytest.mark.anyio
async def test_upload_image_invalid_type(client):
    """Uploading a non-image file returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    fake_file = io.BytesIO(b"not an image")

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/products/upload",
        files={"file": ("test.txt", fake_file, "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Public Product Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_public_list_products(client):
    """Public product listing returns only active products."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    # Create one active and one draft product
    await create_test_product(
        client, token, store["id"], title="Active Product", status="active"
    )
    await create_test_product(
        client, token, store["id"], title="Draft Product", status="draft"
    )

    resp = await client.get(
        f"/api/v1/public/stores/{store['slug']}/products"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Active Product"


@pytest.mark.anyio
async def test_public_list_excludes_cost(client):
    """Public product listing does not expose cost field."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_product(
        client, token, store["id"], title="Widget", status="active", cost=10.00
    )

    resp = await client.get(
        f"/api/v1/public/stores/{store['slug']}/products"
    )
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert "cost" not in item
    assert "store_id" not in item


@pytest.mark.anyio
async def test_public_get_product_by_slug(client):
    """Public product detail returns a single active product by slug."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_product(
        client, token, store["id"], title="Widget Pro", status="active"
    )

    resp = await client.get(
        f"/api/v1/public/stores/{store['slug']}/products/widget-pro"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Widget Pro"
    assert "cost" not in data


@pytest.mark.anyio
async def test_public_get_product_draft_404(client):
    """Public product detail returns 404 for draft products."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_product(
        client, token, store["id"], title="Draft Widget", status="draft"
    )

    resp = await client.get(
        f"/api/v1/public/stores/{store['slug']}/products/draft-widget"
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_public_products_unknown_store(client):
    """Public product listing returns 404 for unknown store slugs."""
    resp = await client.get("/api/v1/public/stores/nonexistent/products")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_public_products_no_auth_required(client):
    """Public product endpoints work without authentication."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_test_product(
        client, token, store["id"], title="Public Item", status="active"
    )

    # No auth header
    resp = await client.get(
        f"/api/v1/public/stores/{store['slug']}/products"
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
