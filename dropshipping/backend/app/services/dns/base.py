"""Abstract DNS provider and data classes.

Defines the contract that all DNS provider implementations must follow,
along with shared data classes for DNS records.

**For Developers:**
    Subclass ``AbstractDnsProvider`` to add support for a new DNS provider.
    Each method corresponds to a standard DNS management operation. The
    ``DnsRecord`` dataclass is the canonical representation of a DNS record
    shared across all providers.

**For QA Engineers:**
    - All providers must implement the same six methods.
    - ``DnsRecord.priority`` is only relevant for MX/SRV record types.
    - ``provider_record_id`` is populated after creating a record via the
      provider API.
    - ``verify_propagation`` should return True/False without raising.

**For Project Managers:**
    This abstraction allows the platform to support multiple DNS providers
    (Cloudflare, Route53, Google Cloud DNS) behind a single interface,
    with a mock provider for development and testing.

**For End Users:**
    The platform manages your DNS records automatically when you connect
    a custom domain. Behind the scenes, it communicates with your DNS
    provider to set up the correct records.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.domain import DnsRecordType


@dataclass
class DnsRecord:
    """Canonical representation of a DNS record.

    Attributes:
        record_type: The DNS record type (A, AAAA, CNAME, MX, TXT, etc.).
        name: The record hostname/name (e.g., "@", "www", "mail").
        value: The record value (IP address, hostname, text, etc.).
        ttl: Time-to-live in seconds. Defaults to 3600 (1 hour).
        priority: Priority value for MX/SRV records. None for other types.
        provider_record_id: Unique identifier assigned by the DNS provider
            after the record is created. None until created.
    """

    record_type: DnsRecordType
    name: str
    value: str
    ttl: int = 3600
    priority: int | None = None
    provider_record_id: str | None = None


class AbstractDnsProvider(ABC):
    """Base DNS provider interface with CRUD and verification methods.

    All DNS provider implementations (Cloudflare, Route53, Google Cloud DNS,
    Mock) must implement these methods to provide a unified API for DNS
    record management.

    Methods:
        create_record: Create a new DNS record in a zone.
        list_records: List all DNS records in a zone.
        update_record: Update an existing DNS record.
        delete_record: Delete a DNS record.
        get_zone_id: Resolve a domain name to its DNS zone identifier.
        verify_propagation: Check if a DNS record has propagated.
    """

    @abstractmethod
    async def create_record(self, zone_id: str, record: DnsRecord) -> DnsRecord:
        """Create a DNS record in the specified zone.

        Args:
            zone_id: The DNS zone identifier.
            record: The DNS record to create.

        Returns:
            The created DnsRecord with ``provider_record_id`` populated.
        """
        ...

    @abstractmethod
    async def list_records(self, zone_id: str) -> list[DnsRecord]:
        """List all DNS records in a zone.

        Args:
            zone_id: The DNS zone identifier.

        Returns:
            A list of DnsRecord objects for all records in the zone.
        """
        ...

    @abstractmethod
    async def update_record(
        self, zone_id: str, record_id: str, record: DnsRecord
    ) -> DnsRecord:
        """Update an existing DNS record.

        Args:
            zone_id: The DNS zone identifier.
            record_id: The provider-assigned record identifier.
            record: The updated DNS record data.

        Returns:
            The updated DnsRecord with current values.
        """
        ...

    @abstractmethod
    async def delete_record(self, zone_id: str, record_id: str) -> bool:
        """Delete a DNS record from a zone.

        Args:
            zone_id: The DNS zone identifier.
            record_id: The provider-assigned record identifier.

        Returns:
            True if the record was deleted, False if not found.
        """
        ...

    @abstractmethod
    async def get_zone_id(self, domain: str) -> str | None:
        """Resolve a domain name to its DNS zone identifier.

        Args:
            domain: The fully-qualified domain name.

        Returns:
            The zone identifier string, or None if the domain is not found.
        """
        ...

    @abstractmethod
    async def verify_propagation(
        self, domain: str, record_type: DnsRecordType, expected_value: str
    ) -> bool:
        """Check whether a DNS record has propagated globally.

        Args:
            domain: The domain to check.
            record_type: The expected record type.
            expected_value: The expected record value.

        Returns:
            True if the record has propagated with the expected value.
        """
        ...
