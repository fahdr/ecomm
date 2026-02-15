"""Mock DNS provider for development and testing.

Provides a fully functional in-memory DNS provider that stores records
in a dictionary. Ideal for development, testing, and CI environments
where no real DNS infrastructure is available.

**For Developers:**
    Records are stored in ``self._zones``, a dict mapping zone IDs to
    lists of DnsRecord objects. The zone ID for any domain is derived
    deterministically as ``mock-zone-{domain}``. Provider record IDs
    use the ``mock-rec-`` prefix with a UUID hex suffix.

**For QA Engineers:**
    - Records persist in memory for the lifetime of the provider instance.
    - ``create_record`` appends to the zone's record list.
    - ``delete_record`` removes the matching record and returns True,
      or returns False if not found.
    - ``verify_propagation`` always returns True.
    - Zone IDs are deterministic: ``mock-zone-{domain_with_dashes}``.

**For Project Managers:**
    The mock provider enables local development and automated testing
    without requiring real DNS infrastructure or API credentials.

**For End Users:**
    This provider is used internally during development. In production,
    your DNS records are managed through your actual DNS provider
    (Cloudflare, Route53, or Google Cloud DNS).
"""

import uuid
from collections import defaultdict

from app.models.domain import DnsRecordType
from app.services.dns.base import AbstractDnsProvider, DnsRecord


class MockDnsProvider(AbstractDnsProvider):
    """In-memory mock DNS provider for development and testing.

    Stores DNS records in a dictionary keyed by zone ID. All operations
    are synchronous in-memory manipulations wrapped in async signatures.

    Attributes:
        _zones: Dictionary mapping zone IDs to lists of DnsRecord objects.
    """

    def __init__(self):
        """Initialize the mock DNS provider with an empty zone store."""
        self._zones: dict[str, list[DnsRecord]] = defaultdict(list)

    async def create_record(self, zone_id: str, record: DnsRecord) -> DnsRecord:
        """Create a DNS record in the mock zone store.

        Args:
            zone_id: The zone identifier (any string).
            record: The DNS record to create.

        Returns:
            The created DnsRecord with a mock provider_record_id.
        """
        record.provider_record_id = f"mock-rec-{uuid.uuid4().hex[:12]}"
        self._zones[zone_id].append(record)
        return record

    async def list_records(self, zone_id: str) -> list[DnsRecord]:
        """List all DNS records in a mock zone.

        Args:
            zone_id: The zone identifier.

        Returns:
            A list of all DnsRecord objects stored for this zone.
        """
        return list(self._zones.get(zone_id, []))

    async def update_record(
        self, zone_id: str, record_id: str, record: DnsRecord
    ) -> DnsRecord:
        """Update an existing DNS record in the mock zone store.

        Finds the record by provider_record_id and replaces it with
        the updated record data.

        Args:
            zone_id: The zone identifier.
            record_id: The provider_record_id of the record to update.
            record: The updated record data.

        Returns:
            The updated DnsRecord with the original provider_record_id.
        """
        records = self._zones.get(zone_id, [])
        for i, existing in enumerate(records):
            if existing.provider_record_id == record_id:
                record.provider_record_id = record_id
                records[i] = record
                return record
        # If not found, still return the record with the ID set
        record.provider_record_id = record_id
        return record

    async def delete_record(self, zone_id: str, record_id: str) -> bool:
        """Delete a DNS record from the mock zone store.

        Args:
            zone_id: The zone identifier.
            record_id: The provider_record_id of the record to delete.

        Returns:
            True if the record was found and deleted, False otherwise.
        """
        records = self._zones.get(zone_id, [])
        for i, existing in enumerate(records):
            if existing.provider_record_id == record_id:
                records.pop(i)
                return True
        return False

    async def get_zone_id(self, domain: str) -> str | None:
        """Derive a mock zone ID from the domain name.

        Args:
            domain: The domain name.

        Returns:
            A deterministic zone ID string: ``mock-zone-{domain_with_dashes}``.
        """
        return f"mock-zone-{domain.replace('.', '-')}"

    async def verify_propagation(
        self, domain: str, record_type: DnsRecordType, expected_value: str
    ) -> bool:
        """Verify DNS propagation (mock always returns True).

        Args:
            domain: The domain to check.
            record_type: The expected record type.
            expected_value: The expected record value.

        Returns:
            True (mock assumes instant propagation).
        """
        return True
