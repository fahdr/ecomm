"""Google Cloud DNS provider implementation.

Mock implementation of the Google Cloud DNS API. In production, this would
use the google-cloud-dns client library for real API calls.

**For Developers:**
    This provider wraps the Google Cloud DNS API. Currently returns
    deterministic mock results for development and testing. Replace mock
    logic with real google-cloud-dns client calls for production use.

**For QA Engineers:**
    - All methods return deterministic results based on the input.
    - Zone IDs use the ``gcp-zone-`` prefix.
    - Record IDs use the ``gcp-rec-`` prefix.
    - ``verify_propagation`` always returns True in mock mode.

**For Project Managers:**
    Google Cloud DNS is one of the supported DNS providers. This
    implementation allows merchants using Google Cloud to manage DNS
    records through the platform.

**For End Users:**
    If your domain's DNS is managed by Google Cloud DNS, the platform
    can automatically configure DNS records for you.
"""

import uuid

from app.models.domain import DnsRecordType
from app.services.dns.base import AbstractDnsProvider, DnsRecord


class GoogleCloudDnsProvider(AbstractDnsProvider):
    """Google Cloud DNS provider using mock responses.

    In production, this would use the google-cloud-dns client library.
    Currently returns deterministic mock data for dev/test environments.

    Attributes:
        project_id: Google Cloud project identifier.
        credentials_json: Path to or contents of the service account JSON.
    """

    def __init__(self, project_id: str = "", credentials_json: str = ""):
        """Initialize the Google Cloud DNS provider.

        Args:
            project_id: Google Cloud project ID.
            credentials_json: Service account credentials JSON string or path.
        """
        self.project_id = project_id
        self.credentials_json = credentials_json

    async def create_record(self, zone_id: str, record: DnsRecord) -> DnsRecord:
        """Create a DNS record via Google Cloud DNS (mock).

        Args:
            zone_id: The Google Cloud DNS managed zone name.
            record: The DNS record to create.

        Returns:
            The created DnsRecord with a GCP-prefixed provider_record_id.
        """
        record.provider_record_id = f"gcp-rec-{uuid.uuid4().hex[:12]}"
        return record

    async def list_records(self, zone_id: str) -> list[DnsRecord]:
        """List DNS records for a Google Cloud DNS managed zone (mock).

        Args:
            zone_id: The managed zone name.

        Returns:
            An empty list (mock -- no persisted state).
        """
        return []

    async def update_record(
        self, zone_id: str, record_id: str, record: DnsRecord
    ) -> DnsRecord:
        """Update a DNS record via Google Cloud DNS (mock).

        Args:
            zone_id: The managed zone name.
            record_id: The record identifier to update.
            record: The updated record data.

        Returns:
            The updated DnsRecord with the original provider_record_id.
        """
        record.provider_record_id = record_id
        return record

    async def delete_record(self, zone_id: str, record_id: str) -> bool:
        """Delete a DNS record via Google Cloud DNS (mock).

        Args:
            zone_id: The managed zone name.
            record_id: The record identifier to delete.

        Returns:
            True (mock always succeeds).
        """
        return True

    async def get_zone_id(self, domain: str) -> str | None:
        """Resolve a domain to its Google Cloud DNS managed zone (mock).

        Args:
            domain: The domain name to look up.

        Returns:
            A deterministic managed zone name derived from the domain.
        """
        return f"gcp-zone-{domain.replace('.', '-')}"

    async def verify_propagation(
        self, domain: str, record_type: DnsRecordType, expected_value: str
    ) -> bool:
        """Check DNS propagation via Google Cloud DNS (mock).

        Args:
            domain: The domain to verify.
            record_type: The expected record type.
            expected_value: The expected record value.

        Returns:
            True (mock always reports propagation success).
        """
        return True
