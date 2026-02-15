"""Tests for DNS management (Feature 6).

Covers MockDnsProvider CRUD, auto-configure DNS, SSL provisioning,
DNS record CRUD via API, DNS status endpoint, factory, and propagation
verification.

**For QA Engineers:**
    Each test is independent -- the database is reset between tests.
    DNS endpoints are store-scoped: ``/stores/{store_id}/domain/dns/...``
    and ``/stores/{store_id}/domain/ssl/...``. Tests verify authentication,
    ownership, and correct DNS record lifecycle.
"""

import pytest

from app.models.domain import DnsRecordType
from app.services.dns.mock import MockDnsProvider
from app.services.dns.base import DnsRecord
from app.services.dns.factory import get_dns_provider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def register_and_get_token(client, email: str = "dns@example.com") -> str:
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
    client, token: str, name: str = "DNS Store", niche: str = "electronics"
) -> dict:
    """Create a store and return the response data.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
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


async def set_domain(client, token: str, store_id: str, domain: str) -> dict:
    """Set a custom domain for a store.

    Args:
        client: The async HTTP test client.
        token: JWT access token.
        store_id: UUID of the store.
        domain: The custom domain name.

    Returns:
        The JSON response dictionary.
    """
    resp = await client.post(
        f"/api/v1/stores/{store_id}/domain",
        json={"domain": domain},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def setup_store_with_domain(client, email: str, domain: str) -> tuple:
    """Create a store, set a domain, and return (token, store, domain_data).

    Args:
        client: The async HTTP test client.
        email: Email for the user.
        domain: The custom domain name.

    Returns:
        Tuple of (token, store_data, domain_data).
    """
    token = await register_and_get_token(client, email)
    store = await create_test_store(client, token)
    domain_data = await set_domain(client, token, store["id"], domain)
    return token, store, domain_data


# ---------------------------------------------------------------------------
# MockDnsProvider unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_create_record():
    """MockDnsProvider.create_record stores the record and assigns an ID."""
    provider = MockDnsProvider()
    record = DnsRecord(
        record_type=DnsRecordType.A, name="@", value="1.2.3.4"
    )
    result = await provider.create_record("zone-1", record)
    assert result.provider_record_id is not None
    assert result.provider_record_id.startswith("mock-rec-")
    assert result.value == "1.2.3.4"


@pytest.mark.asyncio
async def test_mock_provider_list_records():
    """MockDnsProvider.list_records returns all created records."""
    provider = MockDnsProvider()
    await provider.create_record(
        "zone-1",
        DnsRecord(record_type=DnsRecordType.A, name="@", value="1.2.3.4"),
    )
    await provider.create_record(
        "zone-1",
        DnsRecord(record_type=DnsRecordType.CNAME, name="www", value="proxy.example.com"),
    )
    records = await provider.list_records("zone-1")
    assert len(records) == 2


@pytest.mark.asyncio
async def test_mock_provider_list_records_empty_zone():
    """MockDnsProvider.list_records returns empty list for unknown zone."""
    provider = MockDnsProvider()
    records = await provider.list_records("nonexistent-zone")
    assert records == []


@pytest.mark.asyncio
async def test_mock_provider_update_record():
    """MockDnsProvider.update_record modifies an existing record."""
    provider = MockDnsProvider()
    created = await provider.create_record(
        "zone-1",
        DnsRecord(record_type=DnsRecordType.A, name="@", value="1.2.3.4"),
    )
    updated_record = DnsRecord(
        record_type=DnsRecordType.A, name="@", value="5.6.7.8"
    )
    result = await provider.update_record(
        "zone-1", created.provider_record_id, updated_record
    )
    assert result.value == "5.6.7.8"
    assert result.provider_record_id == created.provider_record_id

    # Verify the list reflects the update
    records = await provider.list_records("zone-1")
    assert len(records) == 1
    assert records[0].value == "5.6.7.8"


@pytest.mark.asyncio
async def test_mock_provider_delete_record():
    """MockDnsProvider.delete_record removes the record and returns True."""
    provider = MockDnsProvider()
    created = await provider.create_record(
        "zone-1",
        DnsRecord(record_type=DnsRecordType.A, name="@", value="1.2.3.4"),
    )
    deleted = await provider.delete_record("zone-1", created.provider_record_id)
    assert deleted is True
    records = await provider.list_records("zone-1")
    assert len(records) == 0


@pytest.mark.asyncio
async def test_mock_provider_delete_nonexistent():
    """MockDnsProvider.delete_record returns False for unknown record."""
    provider = MockDnsProvider()
    deleted = await provider.delete_record("zone-1", "nonexistent-id")
    assert deleted is False


@pytest.mark.asyncio
async def test_mock_provider_get_zone_id():
    """MockDnsProvider.get_zone_id returns deterministic zone ID."""
    provider = MockDnsProvider()
    zone_id = await provider.get_zone_id("example.com")
    assert zone_id == "mock-zone-example-com"


@pytest.mark.asyncio
async def test_mock_provider_verify_propagation():
    """MockDnsProvider.verify_propagation always returns True."""
    provider = MockDnsProvider()
    result = await provider.verify_propagation("example.com", DnsRecordType.A, "1.2.3.4")
    assert result is True


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_returns_mock_by_default():
    """get_dns_provider returns MockDnsProvider when mode is 'mock'."""
    provider = get_dns_provider()
    assert isinstance(provider, MockDnsProvider)


@pytest.mark.asyncio
async def test_factory_returns_cloudflare():
    """get_dns_provider returns CloudflareDnsProvider when mode is 'cloudflare'."""
    from unittest.mock import patch
    from app.services.dns.cloudflare import CloudflareDnsProvider

    with patch("app.config.settings") as mock_settings:
        mock_settings.dns_provider_mode = "cloudflare"
        mock_settings.cloudflare_api_token = "test-token"
        provider = get_dns_provider()
        assert isinstance(provider, CloudflareDnsProvider)


@pytest.mark.asyncio
async def test_factory_returns_route53():
    """get_dns_provider returns Route53DnsProvider when mode is 'route53'."""
    from unittest.mock import patch
    from app.services.dns.route53 import Route53DnsProvider

    with patch("app.config.settings") as mock_settings:
        mock_settings.dns_provider_mode = "route53"
        mock_settings.route53_access_key_id = "key"
        mock_settings.route53_secret_access_key = "secret"
        mock_settings.route53_region = "us-east-1"
        provider = get_dns_provider()
        assert isinstance(provider, Route53DnsProvider)


@pytest.mark.asyncio
async def test_factory_returns_google():
    """get_dns_provider returns GoogleCloudDnsProvider when mode is 'google'."""
    from unittest.mock import patch
    from app.services.dns.google_dns import GoogleCloudDnsProvider

    with patch("app.config.settings") as mock_settings:
        mock_settings.dns_provider_mode = "google"
        mock_settings.google_dns_project_id = "project"
        mock_settings.google_dns_credentials_json = "{}"
        provider = get_dns_provider()
        assert isinstance(provider, GoogleCloudDnsProvider)


# ---------------------------------------------------------------------------
# Auto-configure DNS endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_configure_dns_success(client):
    """Auto-configure creates A and CNAME records and returns them."""
    token, store, _ = await setup_store_with_domain(
        client, "autoconf@example.com", "shop.autoconf.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/auto-configure",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["records_created"] == 2
    assert len(data["records"]) == 2

    record_types = {r["record_type"] for r in data["records"]}
    assert "A" in record_types
    assert "CNAME" in record_types


@pytest.mark.asyncio
async def test_auto_configure_dns_no_auth(client):
    """Auto-configure without authentication returns 401."""
    resp = await client.post(
        "/api/v1/stores/00000000-0000-0000-0000-000000000000/domain/dns/auto-configure",
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auto_configure_dns_no_domain(client):
    """Auto-configure when no domain exists returns 404."""
    token = await register_and_get_token(client, "nodom@example.com")
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/auto-configure",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SSL Provisioning endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_ssl_success(client):
    """SSL provisioning sets ssl_provisioned=True and returns certificate info."""
    token, store, _ = await setup_store_with_domain(
        client, "ssl@example.com", "shop.ssl-test.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/ssl/provision",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ssl_provisioned"] is True
    assert data["ssl_certificate_id"] is not None
    assert data["ssl_certificate_id"].startswith("ssl-cert-")
    assert data["ssl_expires_at"] is not None


@pytest.mark.asyncio
async def test_provision_ssl_no_domain(client):
    """SSL provisioning when no domain exists returns 404."""
    token = await register_and_get_token(client, "nossl@example.com")
    store = await create_test_store(client, token)

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/ssl/provision",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DNS Records CRUD via API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dns_record_success(client):
    """Creating a DNS record returns 201 with record details."""
    token, store, _ = await setup_store_with_domain(
        client, "create-rec@example.com", "shop.create-rec.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={
            "record_type": "TXT",
            "name": "@",
            "value": "v=spf1 include:_spf.google.com ~all",
            "ttl": 300,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["record_type"] == "TXT"
    assert data["name"] == "@"
    assert data["value"] == "v=spf1 include:_spf.google.com ~all"
    assert data["ttl"] == 300
    assert data["is_managed"] is False
    assert data["provider_record_id"] is not None


@pytest.mark.asyncio
async def test_create_dns_record_mx_with_priority(client):
    """Creating an MX record with priority works correctly."""
    token, store, _ = await setup_store_with_domain(
        client, "mx-rec@example.com", "shop.mx-rec.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={
            "record_type": "MX",
            "name": "@",
            "value": "mail.example.com",
            "ttl": 3600,
            "priority": 10,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["record_type"] == "MX"
    assert data["priority"] == 10


@pytest.mark.asyncio
async def test_list_dns_records_success(client):
    """Listing DNS records returns all records for the domain."""
    token, store, _ = await setup_store_with_domain(
        client, "list-rec@example.com", "shop.list-rec.com"
    )

    # Create a record first
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={"record_type": "TXT", "name": "@", "value": "test-value"},
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_dns_records_empty(client):
    """Listing DNS records for a domain with no records returns empty list."""
    token, store, _ = await setup_store_with_domain(
        client, "empty-rec@example.com", "shop.empty-rec.com"
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


@pytest.mark.asyncio
async def test_update_dns_record_success(client):
    """Updating a DNS record changes its value."""
    token, store, _ = await setup_store_with_domain(
        client, "update-rec@example.com", "shop.update-rec.com"
    )

    # Create a record
    create_resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={"record_type": "A", "name": "sub", "value": "1.2.3.4"},
        headers={"Authorization": f"Bearer {token}"},
    )
    record_id = create_resp.json()["id"]

    # Update it
    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/domain/dns/records/{record_id}",
        json={"value": "5.6.7.8", "ttl": 7200},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["value"] == "5.6.7.8"
    assert data["ttl"] == 7200


@pytest.mark.asyncio
async def test_update_dns_record_not_found(client):
    """Updating a nonexistent DNS record returns 404."""
    token, store, _ = await setup_store_with_domain(
        client, "update-nf@example.com", "shop.update-nf.com"
    )

    resp = await client.patch(
        f"/api/v1/stores/{store['id']}/domain/dns/records/00000000-0000-0000-0000-000000000000",
        json={"value": "5.6.7.8"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_dns_record_success(client):
    """Deleting a DNS record returns 204."""
    token, store, _ = await setup_store_with_domain(
        client, "delete-rec@example.com", "shop.delete-rec.com"
    )

    # Create a record
    create_resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={"record_type": "A", "name": "temp", "value": "1.2.3.4"},
        headers={"Authorization": f"Bearer {token}"},
    )
    record_id = create_resp.json()["id"]

    # Delete it
    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/domain/dns/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_dns_record_not_found(client):
    """Deleting a nonexistent DNS record returns 404."""
    token, store, _ = await setup_store_with_domain(
        client, "del-nf@example.com", "shop.del-nf.com"
    )

    resp = await client.delete(
        f"/api/v1/stores/{store['id']}/domain/dns/records/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DNS Status endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dns_status_before_configuration(client):
    """DNS status before auto-configure shows dns_configured=False."""
    token, store, _ = await setup_store_with_domain(
        client, "status-pre@example.com", "shop.status-pre.com"
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "shop.status-pre.com"
    assert data["dns_configured"] is False
    assert data["ssl_provisioned"] is False
    assert data["records_count"] == 0


@pytest.mark.asyncio
async def test_dns_status_after_auto_configure(client):
    """DNS status after auto-configure shows dns_configured=True."""
    token, store, _ = await setup_store_with_domain(
        client, "status-post@example.com", "shop.status-post.com"
    )

    # Auto-configure DNS
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/auto-configure",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dns_configured"] is True
    assert data["records_count"] == 2
    assert data["propagation_status"] == "propagated"


@pytest.mark.asyncio
async def test_dns_status_after_ssl_provision(client):
    """DNS status after SSL provision shows ssl_provisioned=True."""
    token, store, _ = await setup_store_with_domain(
        client, "status-ssl@example.com", "shop.status-ssl.com"
    )

    # Provision SSL
    await client.post(
        f"/api/v1/stores/{store['id']}/domain/ssl/provision",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ssl_provisioned"] is True


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dns_full_lifecycle(client):
    """Full lifecycle: set domain -> auto-configure -> create record -> provision SSL -> check status -> delete record."""
    token, store, _ = await setup_store_with_domain(
        client, "lifecycle-dns@example.com", "shop.lifecycle-dns.com"
    )

    # 1. Auto-configure DNS
    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/auto-configure",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["records_created"] == 2

    # 2. Create a manual record
    create_resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={"record_type": "TXT", "name": "@", "value": "verification=123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201
    record_id = create_resp.json()["id"]

    # 3. List records (should have 3 total: 2 auto + 1 manual)
    list_resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(list_resp.json()) == 3

    # 4. Provision SSL
    ssl_resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/ssl/provision",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ssl_resp.status_code == 200
    assert ssl_resp.json()["ssl_provisioned"] is True

    # 5. Check status
    status_resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["dns_configured"] is True
    assert status_data["ssl_provisioned"] is True
    assert status_data["records_count"] == 3

    # 6. Delete the manual record
    del_resp = await client.delete(
        f"/api/v1/stores/{store['id']}/domain/dns/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_auto_configure_a_record_values(client):
    """Auto-configured A record uses the platform IP address."""
    token, store, _ = await setup_store_with_domain(
        client, "arecord@example.com", "shop.arecord.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/auto-configure",
        headers={"Authorization": f"Bearer {token}"},
    )
    records = resp.json()["records"]
    a_records = [r for r in records if r["record_type"] == "A"]
    assert len(a_records) == 1
    assert a_records[0]["value"] == "192.0.2.1"
    assert a_records[0]["name"] == "@"
    assert a_records[0]["is_managed"] is True


@pytest.mark.asyncio
async def test_auto_configure_cname_record_values(client):
    """Auto-configured CNAME record uses the platform CNAME target."""
    token, store, _ = await setup_store_with_domain(
        client, "cname@example.com", "shop.cname.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/auto-configure",
        headers={"Authorization": f"Bearer {token}"},
    )
    records = resp.json()["records"]
    cname_records = [r for r in records if r["record_type"] == "CNAME"]
    assert len(cname_records) == 1
    assert cname_records[0]["value"] == "proxy.platform.app"
    assert cname_records[0]["name"] == "www"
    assert cname_records[0]["is_managed"] is True


@pytest.mark.asyncio
async def test_dns_record_response_shape(client):
    """DNS record response includes all expected fields."""
    token, store, _ = await setup_store_with_domain(
        client, "shape@example.com", "shop.shape.com"
    )

    resp = await client.post(
        f"/api/v1/stores/{store['id']}/domain/dns/records",
        json={"record_type": "A", "name": "@", "value": "1.2.3.4"},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    expected_keys = {
        "id", "domain_id", "record_type", "name", "value", "ttl",
        "priority", "provider_record_id", "is_managed", "created_at",
        "updated_at",
    }
    assert set(data.keys()) == expected_keys


@pytest.mark.asyncio
async def test_dns_status_response_shape(client):
    """DNS status response includes all expected fields."""
    token, store, _ = await setup_store_with_domain(
        client, "status-shape@example.com", "shop.status-shape.com"
    )

    resp = await client.get(
        f"/api/v1/stores/{store['id']}/domain/dns/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()
    expected_keys = {
        "domain", "dns_configured", "ssl_provisioned",
        "records_count", "propagation_status",
    }
    assert set(data.keys()) == expected_keys
