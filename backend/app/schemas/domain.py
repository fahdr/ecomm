"""Pydantic schemas for custom domain endpoints (Feature 22).

These schemas validate incoming requests and shape outgoing responses for
the ``/api/v1/stores/{store_id}/domains/*`` routes.

**For Developers:**
    ``CreateDomainRequest`` is the input schema. ``DomainResponse`` uses
    ``from_attributes``. ``VerifyDomainResponse`` returns the result of
    a DNS verification check.

**For QA Engineers:**
    - ``CreateDomainRequest.domain`` must be a valid domain name.
    - ``DomainResponse.status`` cycles through ``"pending"``,
      ``"verified"``, ``"failed"``.
    - ``DomainResponse.verification_token`` is a TXT record value the
      merchant must add to their DNS.
    - ``ssl_provisioned`` becomes ``true`` after the TLS certificate is
      issued.

**For Project Managers:**
    Custom domains let merchants use their own brand domain (e.g.
    ``shop.mybrand.com``) for their storefront instead of the
    platform subdomain. DNS verification and automatic SSL
    provisioning are handled by the platform.

**For End Users:**
    Connect your own domain to your store. Add the provided DNS
    record, then click verify. SSL is provisioned automatically
    once the domain is verified.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateDomainRequest(BaseModel):
    """Schema for adding a custom domain to a store.

    Attributes:
        domain: The fully-qualified domain name (e.g.
            ``"shop.mybrand.com"``).
    """

    domain: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Fully-qualified domain name",
    )


class DomainResponse(BaseModel):
    """Schema for returning custom domain data in API responses.

    Attributes:
        id: The domain record's unique identifier.
        store_id: The parent store's UUID.
        domain: The fully-qualified domain name.
        status: Verification status (``"pending"``, ``"verified"``,
            ``"failed"``).
        verification_token: TXT record value the merchant must add
            to their DNS for verification.
        verified_at: When the domain was successfully verified
            (null until verified).
        ssl_provisioned: Whether the TLS certificate has been issued.
        created_at: When the domain was added.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    domain: str
    status: str
    verification_token: str
    verified_at: datetime | None
    ssl_provisioned: bool
    created_at: datetime


class VerifyDomainResponse(BaseModel):
    """Schema for the result of a domain verification check.

    Attributes:
        verified: Whether the DNS records matched and the domain is
            now verified.
        message: Human-readable message explaining the verification
            result.
    """

    verified: bool
    message: str
