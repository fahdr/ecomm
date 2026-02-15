"""Cloudflare DNS provider implementation.

Mock implementation of the Cloudflare DNS API. In production, this would
use httpx to make real API calls to the Cloudflare API v4 endpoints.

**For Developers:**
    This provider wraps the Cloudflare API (https://api.cloudflare.com/client/v4/).
    Currently returns deterministic mock results for development and testing.
    Replace mock logic with real httpx calls for production use.

**For QA Engineers:**
    - All methods return deterministic results based on the input.
    - Zone IDs are derived from the domain name (``cf-zone-{domain}``).
    - Record IDs use the ``cf-rec-`` prefix.
    - ``verify_propagation`` always returns True in mock mode.

**For Project Managers:**
    Cloudflare is one of the supported DNS providers. This implementation
    allows merchants to manage DNS records through the platform using their
    Cloudflare account.

**For End Users:**
    If your domain's DNS is managed by Cloudflare, the platform can
    automatically configure DNS records for you.
"""

import uuid

from app.models.domain import DnsRecordType
from app.services.dns.base import AbstractDnsProvider, DnsRecord


class CloudflareDnsProvider(AbstractDnsProvider):
    """Cloudflare DNS provider using mock responses.

    In production, this would use httpx to call the Cloudflare API v4.
    Currently returns deterministic mock data for dev/test environments.

    Attributes:
        api_token: The Cloudflare API token for authentication.
        base_url: The Cloudflare API base URL.
    """

    def __init__(self, api_token: str = "", base_url: str = "https://api.cloudflare.com/client/v4"):
        """Initialize the Cloudflare DNS provider.

        Args:
            api_token: Cloudflare API token for authentication.
            base_url: Base URL for the Cloudflare API.
        """
        self.api_token = api_token
        self.base_url = base_url

    async def create_record(self, zone_id: str, record: DnsRecord) -> DnsRecord:
        """Create a DNS record via the Cloudflare API (mock).

        Args:
            zone_id: The Cloudflare zone identifier.
            record: The DNS record to create.

        Returns:
            The created DnsRecord with a Cloudflare-prefixed provider_record_id.
        """
        record.provider_record_id = f"cf-rec-{uuid.uuid4().hex[:12]}"
        return record

    async def list_records(self, zone_id: str) -> list[DnsRecord]:
        """List DNS records for a Cloudflare zone (mock).

        Args:
            zone_id: The Cloudflare zone identifier.

        Returns:
            An empty list (mock -- no persisted state).
        """
        return []

    async def update_record(
        self, zone_id: str, record_id: str, record: DnsRecord
    ) -> DnsRecord:
        """Update a DNS record via the Cloudflare API (mock).

        Args:
            zone_id: The Cloudflare zone identifier.
            record_id: The record identifier to update.
            record: The updated record data.

        Returns:
            The updated DnsRecord with the original provider_record_id.
        """
        record.provider_record_id = record_id
        return record

    async def delete_record(self, zone_id: str, record_id: str) -> bool:
        """Delete a DNS record via the Cloudflare API (mock).

        Args:
            zone_id: The Cloudflare zone identifier.
            record_id: The record identifier to delete.

        Returns:
            True (mock always succeeds).
        """
        return True

    async def get_zone_id(self, domain: str) -> str | None:
        """Resolve a domain to its Cloudflare zone ID (mock).

        Args:
            domain: The domain name to look up.

        Returns:
            A deterministic zone ID string derived from the domain.
        """
        return f"cf-zone-{domain.replace('.', '-')}"

    async def verify_propagation(
        self, domain: str, record_type: DnsRecordType, expected_value: str
    ) -> bool:
        """Check DNS propagation via Cloudflare (mock).

        Args:
            domain: The domain to verify.
            record_type: The expected record type.
            expected_value: The expected record value.

        Returns:
            True (mock always reports propagation success).
        """
        return True
