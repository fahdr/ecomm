"""Pydantic schemas for DNS management endpoints (Feature 6).

These schemas validate incoming requests and shape outgoing responses for
the DNS management API routes.

**For Developers:**
    All schemas use ``from_attributes = True`` for ORM compatibility where
    needed. ``DnsRecordType`` values are validated as enum strings (A, AAAA,
    CNAME, MX, TXT, NS, SRV, CAA).

**For QA Engineers:**
    - ``CreateDnsRecordRequest.record_type`` must be a valid DnsRecordType.
    - ``ttl`` defaults to 3600 and must be between 60 and 86400.
    - ``priority`` is optional and only relevant for MX/SRV records.
    - ``UpdateDnsRecordRequest`` has all fields optional for partial updates.
    - ``DnsRecordResponse`` includes provider_record_id and is_managed.

**For Project Managers:**
    These schemas support Feature 6 (DNS Management), enabling both
    automatic and manual DNS record configuration for custom domains.

**For End Users:**
    DNS records control how your domain name connects to your store.
    The platform manages these records automatically, but you can also
    create, update, or delete records manually if needed.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import DnsRecordType


class CreateDnsRecordRequest(BaseModel):
    """Schema for creating a new DNS record.

    Attributes:
        record_type: The DNS record type (A, AAAA, CNAME, MX, TXT, etc.).
        name: The record hostname/name (e.g., "@", "www", "mail").
        value: The record value (IP address, hostname, text content).
        ttl: Time-to-live in seconds. Range: 60-86400. Default: 3600.
        priority: Priority value for MX/SRV records (optional).
    """

    record_type: DnsRecordType = Field(
        ..., description="DNS record type (A, AAAA, CNAME, MX, TXT, NS, SRV, CAA)"
    )
    name: str = Field(
        ..., min_length=1, max_length=255, description="Record hostname/name"
    )
    value: str = Field(
        ..., min_length=1, max_length=1000, description="Record value"
    )
    ttl: int = Field(
        default=3600, ge=60, le=86400, description="Time-to-live in seconds"
    )
    priority: int | None = Field(
        default=None, ge=0, le=65535, description="Priority for MX/SRV records"
    )


class UpdateDnsRecordRequest(BaseModel):
    """Schema for updating an existing DNS record (partial update).

    All fields are optional. Only provided fields will be updated.

    Attributes:
        record_type: New DNS record type (optional).
        name: New record name (optional).
        value: New record value (optional).
        ttl: New TTL value (optional).
        priority: New priority value (optional).
    """

    record_type: DnsRecordType | None = Field(
        default=None, description="New DNS record type"
    )
    name: str | None = Field(
        default=None, min_length=1, max_length=255, description="New record name"
    )
    value: str | None = Field(
        default=None, min_length=1, max_length=1000, description="New record value"
    )
    ttl: int | None = Field(
        default=None, ge=60, le=86400, description="New TTL in seconds"
    )
    priority: int | None = Field(
        default=None, ge=0, le=65535, description="New priority value"
    )


class DnsRecordResponse(BaseModel):
    """Schema for returning a DNS record in API responses.

    Attributes:
        id: The record's unique identifier (UUID).
        domain_id: The parent domain's UUID.
        record_type: The DNS record type.
        name: The record hostname/name.
        value: The record value.
        ttl: Time-to-live in seconds.
        priority: Priority for MX/SRV records (null for other types).
        provider_record_id: Identifier from the DNS provider (null if pending).
        is_managed: Whether this record is platform-managed (auto-configured).
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    domain_id: uuid.UUID
    record_type: DnsRecordType
    name: str
    value: str
    ttl: int
    priority: int | None
    provider_record_id: str | None
    is_managed: bool
    created_at: datetime
    updated_at: datetime


class AutoConfigureResponse(BaseModel):
    """Schema for the auto-configure DNS response.

    Attributes:
        records_created: Number of DNS records automatically created.
        records: List of created DNS record details.
    """

    records_created: int
    records: list[DnsRecordResponse]


class SslProvisionResponse(BaseModel):
    """Schema for the SSL provisioning response.

    Attributes:
        ssl_provisioned: Whether SSL was successfully provisioned.
        ssl_certificate_id: The certificate identifier (null if not provisioned).
        ssl_expires_at: Certificate expiration timestamp (null if not provisioned).
    """

    ssl_provisioned: bool
    ssl_certificate_id: str | None
    ssl_expires_at: datetime | None


class DnsStatusResponse(BaseModel):
    """Schema for the comprehensive DNS status summary.

    Attributes:
        domain: The domain name.
        dns_configured: Whether auto DNS configuration has been applied.
        ssl_provisioned: Whether SSL certificate has been provisioned.
        records_count: Total number of DNS records for this domain.
        propagation_status: Current propagation status ("propagated" or "pending").
    """

    domain: str
    dns_configured: bool
    ssl_provisioned: bool
    records_count: int
    propagation_status: str
