"""Pydantic schemas for domain purchasing endpoints (Feature 7).

These schemas validate incoming requests and shape outgoing responses for
the domain search, purchase, renewal, and management API routes.

**For Developers:**
    All schemas use Pydantic v2 conventions. ``DomainSearchRequest`` takes
    a query string and optional list of TLDs. ``DomainPurchaseRequest``
    includes the domain, registration years, and optional contact info.

**For QA Engineers:**
    - ``DomainSearchRequest.query`` must be at least 1 character.
    - ``DomainSearchRequest.tlds`` defaults to ["com", "io", "store"].
    - ``DomainPurchaseRequest.years`` must be between 1 and 10.
    - ``DomainPurchaseResponse`` includes both purchase and config status.
    - ``AutoRenewRequest.auto_renew`` is a boolean toggle.

**For Project Managers:**
    These schemas support Feature 7 (Domain Purchasing), enabling merchants
    to search for, purchase, and manage domains directly through the
    platform.

**For End Users:**
    Search for available domain names, purchase them with a few clicks,
    and manage renewals and auto-renewal settings from your dashboard.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DomainSearchRequest(BaseModel):
    """Schema for searching available domain names.

    Attributes:
        query: The domain name query (without TLD extension).
        tlds: List of TLD extensions to search. Defaults to
            ["com", "io", "store"].
    """

    query: str = Field(
        ..., min_length=1, max_length=63, description="Domain name query (without TLD)"
    )
    tlds: list[str] = Field(
        default=["com", "io", "store"],
        description="TLD extensions to search",
    )


class DomainSearchResultItem(BaseModel):
    """Schema for a single domain search result.

    Attributes:
        domain: The fully-qualified domain name.
        available: Whether the domain is available for purchase.
        price: The registration price as a string (decimal).
        currency: The currency code (e.g., "USD").
        period_years: The registration period in years.
    """

    domain: str
    available: bool
    price: str
    currency: str
    period_years: int


class DomainSearchResponse(BaseModel):
    """Schema for the domain search response.

    Attributes:
        results: List of domain search results.
    """

    results: list[DomainSearchResultItem]


class DomainPurchaseRequest(BaseModel):
    """Schema for purchasing a domain name.

    Attributes:
        domain: The fully-qualified domain to purchase.
        years: Registration period in years (1-10, default 1).
        contact_info: Optional registrant contact information.
    """

    domain: str = Field(
        ..., min_length=1, max_length=255, description="Domain name to purchase"
    )
    years: int = Field(
        default=1, ge=1, le=10, description="Registration period in years"
    )
    contact_info: dict = Field(
        default_factory=dict, description="Registrant contact information"
    )


class DomainPurchaseResponse(BaseModel):
    """Schema for the domain purchase response.

    Attributes:
        domain: The purchased domain name.
        order_id: The registrar's order identifier.
        status: Purchase status ("success", "pending", "failed").
        expiry_date: Domain expiration date.
        auto_dns_configured: Whether DNS was auto-configured.
        ssl_provisioned: Whether SSL was provisioned.
    """

    domain: str
    order_id: str
    status: str
    expiry_date: str | None
    auto_dns_configured: bool
    ssl_provisioned: bool


class DomainRenewRequest(BaseModel):
    """Schema for renewing a domain registration.

    Attributes:
        years: Number of years to renew for (1-10, default 1).
    """

    years: int = Field(
        default=1, ge=1, le=10, description="Renewal period in years"
    )


class DomainRenewResponse(BaseModel):
    """Schema for the domain renewal response.

    Attributes:
        domain: The renewed domain name.
        new_expiry_date: The new expiration date after renewal.
        order_id: The registrar's renewal order identifier.
    """

    domain: str
    new_expiry_date: str | None
    order_id: str


class OwnedDomainItem(BaseModel):
    """Schema for a single owned domain in the list.

    Attributes:
        id: The domain record's unique identifier.
        store_id: The parent store's UUID.
        domain: The domain name.
        status: Domain status (pending, verified, active, failed).
        purchase_provider: The registrar used for purchase.
        purchase_date: When the domain was purchased.
        expiry_date: When the domain expires.
        auto_renew: Whether auto-renewal is enabled.
        is_purchased: Whether the domain was purchased via the platform.
        ssl_provisioned: Whether SSL is provisioned.
        auto_dns_configured: Whether DNS was auto-configured.
    """

    id: str
    store_id: str
    domain: str
    status: str
    purchase_provider: str | None
    purchase_date: str | None
    expiry_date: str | None
    auto_renew: bool
    is_purchased: bool
    ssl_provisioned: bool
    auto_dns_configured: bool


class OwnedDomainResponse(BaseModel):
    """Schema for the list of owned domains response.

    Attributes:
        domains: List of owned domain items.
    """

    domains: list[OwnedDomainItem]


class AutoRenewRequest(BaseModel):
    """Schema for toggling domain auto-renewal.

    Attributes:
        auto_renew: Whether to enable or disable auto-renewal.
    """

    auto_renew: bool = Field(
        ..., description="Enable or disable auto-renewal"
    )


class AutoRenewResponse(BaseModel):
    """Schema for the auto-renewal toggle response.

    Attributes:
        domain: The domain name.
        auto_renew: The new auto-renewal status.
    """

    domain: str
    auto_renew: bool
