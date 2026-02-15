"""Abstract domain registrar provider and data classes.

Defines the contract that all domain registrar implementations must follow,
along with shared data classes for domain search and purchase results.

**For Developers:**
    Subclass ``AbstractDomainProvider`` to add support for a new domain
    registrar. Each method corresponds to a standard domain registration
    operation. The data classes (``DomainSearchResult``,
    ``DomainPurchaseResult``) are the canonical representations shared
    across all providers.

**For QA Engineers:**
    - All providers must implement the same six methods.
    - ``DomainSearchResult.available`` indicates if a domain can be purchased.
    - ``DomainPurchaseResult.status`` is one of "success", "pending", "failed".
    - ``set_nameservers`` should return True on success, False on failure.

**For Project Managers:**
    This abstraction allows the platform to support multiple domain
    registrars (ResellerClub, Squarespace/Google Domains) behind a
    single interface, with a mock provider for development and testing.

**For End Users:**
    The platform lets you search for and purchase domain names directly.
    Behind the scenes, it communicates with domain registrars to handle
    registration and configuration.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class DomainSearchResult:
    """Result of a domain availability search.

    Attributes:
        domain: The fully-qualified domain name that was searched.
        available: Whether the domain is available for purchase.
        price: The price for the domain registration.
        currency: The currency code (default "USD").
        period_years: The registration period in years (default 1).
    """

    domain: str
    available: bool
    price: Decimal
    currency: str = "USD"
    period_years: int = 1


@dataclass
class DomainPurchaseResult:
    """Result of a domain purchase or renewal operation.

    Attributes:
        domain: The fully-qualified domain name purchased/renewed.
        order_id: The registrar's order identifier.
        status: The operation status ("success", "pending", "failed").
        expiry_date: The domain expiration date (None if pending/failed).
    """

    domain: str
    order_id: str
    status: str
    expiry_date: datetime | None = None


class AbstractDomainProvider(ABC):
    """Base domain registrar interface for search, purchase, and management.

    All domain registrar implementations (ResellerClub, Squarespace, Mock)
    must implement these methods to provide a unified API for domain
    registration and management.

    Methods:
        search_domains: Search for available domains matching a query.
        purchase_domain: Purchase a domain name.
        check_availability: Check if a specific domain is available.
        renew_domain: Renew a domain registration.
        set_nameservers: Set nameservers for a domain.
        get_domain_info: Get detailed information about a domain.
    """

    @abstractmethod
    async def search_domains(
        self, query: str, tlds: list[str]
    ) -> list[DomainSearchResult]:
        """Search for available domains matching a query across TLDs.

        Args:
            query: The domain name query (without TLD).
            tlds: List of TLD extensions to search (e.g., ["com", "io"]).

        Returns:
            A list of DomainSearchResult objects, one per TLD.
        """
        ...

    @abstractmethod
    async def purchase_domain(
        self, domain: str, years: int, contact_info: dict
    ) -> DomainPurchaseResult:
        """Purchase a domain name.

        Args:
            domain: The fully-qualified domain to purchase.
            years: Registration period in years.
            contact_info: Registrant contact information dict.

        Returns:
            A DomainPurchaseResult with the order details.
        """
        ...

    @abstractmethod
    async def check_availability(self, domain: str) -> DomainSearchResult:
        """Check if a specific domain is available for registration.

        Args:
            domain: The fully-qualified domain name to check.

        Returns:
            A DomainSearchResult with availability and pricing info.
        """
        ...

    @abstractmethod
    async def renew_domain(
        self, domain: str, years: int
    ) -> DomainPurchaseResult:
        """Renew a domain registration.

        Args:
            domain: The domain to renew.
            years: Number of years to renew for.

        Returns:
            A DomainPurchaseResult with the renewal details.
        """
        ...

    @abstractmethod
    async def set_nameservers(
        self, domain: str, nameservers: list[str]
    ) -> bool:
        """Set nameservers for a domain.

        Args:
            domain: The domain to configure.
            nameservers: List of nameserver hostnames.

        Returns:
            True if nameservers were set successfully, False otherwise.
        """
        ...

    @abstractmethod
    async def get_domain_info(self, domain: str) -> dict:
        """Get detailed information about a registered domain.

        Args:
            domain: The domain to query.

        Returns:
            A dict with domain details (status, expiry, nameservers, etc.).
        """
        ...
