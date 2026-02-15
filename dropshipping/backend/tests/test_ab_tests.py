"""Tests for A/B testing endpoints (Feature F29).

Covers creating A/B tests, listing tests, retrieving a test with results,
starting/stopping tests via status updates, recording events, and deleting
tests.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    A/B test endpoints are store-scoped: ``/stores/{store_id}/ab-tests``.
    Tests start in ``draft`` status and must be explicitly started.
    Variant weights must sum to 100.
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


async def create_ab_test(
    client,
    token: str,
    store_id: str,
    name: str = "Button Color Test",
    variants: list | None = None,
) -> dict:
    """Create an A/B test and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token for authorization.
        store_id: UUID of the store.
        name: Test name.
        variants: List of variant configs. Defaults to a control/variant_a pair.

    Returns:
        The JSON response dictionary for the created A/B test.
    """
    if variants is None:
        variants = [
            {"name": "control", "weight": 50, "description": "Original design"},
            {"name": "variant_a", "weight": 50, "description": "New design"},
        ]
    resp = await client.post(
        f"/api/v1/stores/{store_id}/ab-tests",
        json={
            "name": name,
            "variants": variants,
            "metric": "conversion_rate",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Create A/B Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_ab_test_success(client):
    """Creating an A/B test returns 201 with draft status and variant configs."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.post(
        f"/api/v1/stores/{store['id']}/ab-tests",
        json={
            "name": "Hero Banner Test",
            "description": "Testing hero banner designs",
            "metric": "click_through_rate",
            "variants": [
                {"name": "control", "weight": 50},
                {"name": "variant_a", "weight": 50},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Hero Banner Test"
    assert data["status"] == "draft"
    assert data["metric"] == "click_through_rate"
    assert data["store_id"] == store["id"]
    assert len(data["variants"]) == 2
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_ab_test_no_auth(client):
    """Creating an A/B test without authentication returns 401."""
    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/ab-tests",
        json={
            "name": "Test",
            "metric": "conversion_rate",
            "variants": [
                {"name": "control", "weight": 50},
                {"name": "variant_a", "weight": 50},
            ],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_ab_test_store_not_found(client):
    """Creating an A/B test on a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/ab-tests",
        json={
            "name": "Test",
            "metric": "conversion_rate",
            "variants": [
                {"name": "control", "weight": 50},
                {"name": "variant_a", "weight": 50},
            ],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# List A/B Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_ab_tests_success(client):
    """Listing A/B tests returns paginated data with created tests."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    await create_ab_test(client, token, store["id"], name="Test A")
    await create_ab_test(client, token, store["id"], name="Test B")

    response = await client.get(
        f"/api/v1/stores/{store['id']}/ab-tests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_ab_tests_empty(client):
    """Listing A/B tests when none exist returns an empty paginated response."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/ab-tests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Get A/B Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ab_test_success(client):
    """Retrieving an A/B test by ID returns the test data with results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    test = await create_ab_test(client, token, store["id"])

    response = await client.get(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test["id"]
    assert data["name"] == test["name"]
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_get_ab_test_not_found(client):
    """Retrieving a non-existent A/B test returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/ab-tests/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Start / Stop A/B Test (status update via PATCH)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_ab_test(client):
    """Starting an A/B test changes status from draft to running."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    test = await create_ab_test(client, token, store["id"])

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_stop_ab_test(client):
    """Completing an A/B test changes status to completed."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    test = await create_ab_test(client, token, store["id"])

    # Start the test first.
    await client.patch(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Stop the test.
    response = await client.patch(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# Record Event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_event_on_running_test(client):
    """Recording an event on a running test returns success confirmation."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    test = await create_ab_test(client, token, store["id"])

    # Get a variant_id from the created test's variants.
    variant_id = test["variants"][0]["id"]

    # Start the test.
    await client.patch(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}",
        json={"status": "running"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.post(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}/events",
        json={
            "variant_id": variant_id,
            "event_type": "impression",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recorded"] is True
    assert "message" in data


@pytest.mark.asyncio
async def test_record_event_on_draft_test_fails(client):
    """Recording an event on a draft (not running) test returns 400."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    test = await create_ab_test(client, token, store["id"])

    # Get a variant_id from the created test's variants.
    variant_id = test["variants"][0]["id"]

    response = await client.post(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}/events",
        json={
            "variant_id": variant_id,
            "event_type": "impression",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Delete A/B Test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_ab_test_success(client):
    """Deleting a draft A/B test returns 204 with no content."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)
    test = await create_ab_test(client, token, store["id"])

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/ab-tests/{test['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_ab_test_not_found(client):
    """Deleting a non-existent A/B test returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.delete(
        f"/api/v1/stores/{store['id']}/ab-tests/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
