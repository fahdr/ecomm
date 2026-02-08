"""Tests for fraud detection endpoints (Feature F28).

Covers listing fraud checks, retrieving a single fraud check, and reviewing
(approving/rejecting) a fraud check. Fraud checks are created automatically
when orders are placed, so tests verify the list/read endpoints and the
review workflow.

**For QA Engineers:**
    Each test is independent — the database is reset between tests.
    Fraud check endpoints are store-scoped: ``/stores/{store_id}/fraud-checks``.
    Tests verify pagination structure, flagged_only filtering, and the
    review status update flow.
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


# ---------------------------------------------------------------------------
# List Fraud Checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_fraud_checks_empty(client):
    """Listing fraud checks for a store with no orders returns empty results."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/fraud-checks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["per_page"] == 20
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_list_fraud_checks_no_auth(client):
    """Listing fraud checks without authentication returns 401."""
    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/fraud-checks",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_fraud_checks_store_not_found(client):
    """Listing fraud checks for a non-existent store returns 404."""
    token = await register_and_get_token(client)

    response = await client.get(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/fraud-checks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_fraud_checks_flagged_only(client):
    """Listing with flagged_only filter returns only medium+ risk checks."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/fraud-checks?flagged_only=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Get Fraud Check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_fraud_check_not_found(client):
    """Retrieving a non-existent fraud check returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.get(
        f"/api/v1/stores/{store['id']}/fraud-checks/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Review Fraud Check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_fraud_check_not_found(client):
    """Reviewing a non-existent fraud check returns 404."""
    token = await register_and_get_token(client)
    store = await create_test_store(client, token)

    response = await client.patch(
        f"/api/v1/stores/{store['id']}/fraud-checks/00000000-0000-0000-0000-000000000000",
        json={"is_flagged": False, "notes": "Looks safe"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_review_fraud_check_no_auth(client):
    """Reviewing a fraud check without authentication returns 401."""
    response = await client.patch(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/fraud-checks/00000000-0000-0000-0000-000000000000",
        json={"is_flagged": False},
    )
    assert response.status_code == 401
