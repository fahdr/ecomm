"""Squarespace Domains (formerly Google Domains) registrar implementation.

Mock implementation of the Squarespace Domains API. In production, this would
use httpx to make real API calls to the Squarespace Domains API.

**For Developers:**
    This provider wraps the Squarespace Domains API (which acquired Google
    Domains). Currently returns deterministic mock results for development
    and testing. Replace mock logic with real httpx calls for production use.

**For QA Engineers:**
    - All methods return deterministic results based on the input.
    - Order IDs use the ``sq-order-`` prefix.
    - Domains ending in ``taken.com`` are reported as unavailable.
    - Pricing follows Squarespace's typical rates.

**For Project Managers:**
    Squarespace Domains (formerly Google Domains) is one of the supported
    registrars. This implementation provides an alternative domain
    purchasing channel for merchants.

**For End Users:**
    You can purchase domain names through the platform using the
    Squarespace Domains registrar (formerly Google Domains).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.domain_registrar.base import (
    AbstractDomainProvider,
    DomainPurchaseResult,
    DomainSearchResult,
)


# Deterministic pricing by TLD (Squarespace pricing)
_TLD_PRICES = {
    "com": Decimal("14.00"),
    "io": Decimal("35.00"),
    "store": Decimal("5.00"),
    "net": Decimal("13.00"),
    "org": Decimal("12.00"),
    "co": Decimal("28.00"),
    "app": Decimal("16.00"),
}


class SquarespaceDomainProvider(AbstractDomainProvider):
    """Squarespace Domains registrar using mock responses.

    In production, this would use httpx to call the Squarespace API.
    Currently returns deterministic mock data for dev/test environments.

    Attributes:
        api_key: The Squarespace Domains API key.
    """

    def __init__(self, api_key: str = ""):
        """Initialize the Squarespace Domains provider.

        Args:
            api_key: Squarespace Domains API key.
        """
        self.api_key = api_key

    async def search_domains(
        self, query: str, tlds: list[str]
    ) -> list[DomainSearchResult]:
        """Search for available domains across TLDs (mock).

        Args:
            query: The domain name query (without TLD).
            tlds: List of TLD extensions to search.

        Returns:
            List of DomainSearchResult with availability and pricing.
        """
        results = []
        for tld in tlds:
            domain = f"{query}.{tld}"
            available = not domain.endswith("taken.com")
            price = _TLD_PRICES.get(tld, Decimal("12.00"))
            results.append(
                DomainSearchResult(
                    domain=domain,
                    available=available,
                    price=price,
                    currency="USD",
                    period_years=1,
                )
            )
        return results

    async def purchase_domain(
        self, domain: str, years: int, contact_info: dict
    ) -> DomainPurchaseResult:
        """Purchase a domain (mock).

        Args:
            domain: The domain to purchase.
            years: Registration period in years.
            contact_info: Registrant contact information.

        Returns:
            DomainPurchaseResult with mock order details.
        """
        return DomainPurchaseResult(
            domain=domain,
            order_id=f"sq-order-{uuid.uuid4().hex[:12]}",
            status="success",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365 * years),
        )

    async def check_availability(self, domain: str) -> DomainSearchResult:
        """Check domain availability (mock).

        Args:
            domain: The domain to check.

        Returns:
            DomainSearchResult with availability info.
        """
        tld = domain.rsplit(".", 1)[-1] if "." in domain else "com"
        available = not domain.endswith("taken.com")
        price = _TLD_PRICES.get(tld, Decimal("12.00"))
        return DomainSearchResult(
            domain=domain,
            available=available,
            price=price,
            currency="USD",
            period_years=1,
        )

    async def renew_domain(
        self, domain: str, years: int
    ) -> DomainPurchaseResult:
        """Renew a domain registration (mock).

        Args:
            domain: The domain to renew.
            years: Number of years to renew for.

        Returns:
            DomainPurchaseResult with renewal details.
        """
        return DomainPurchaseResult(
            domain=domain,
            order_id=f"sq-renew-{uuid.uuid4().hex[:12]}",
            status="success",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365 * years),
        )

    async def set_nameservers(
        self, domain: str, nameservers: list[str]
    ) -> bool:
        """Set nameservers for a domain (mock).

        Args:
            domain: The domain to configure.
            nameservers: List of nameserver hostnames.

        Returns:
            True (mock always succeeds).
        """
        return True

    async def get_domain_info(self, domain: str) -> dict:
        """Get domain information (mock).

        Args:
            domain: The domain to query.

        Returns:
            A mock dict with domain details.
        """
        return {
            "domain": domain,
            "status": "active",
            "registrar": "squarespace",
            "expiry_date": (
                datetime.now(timezone.utc) + timedelta(days=365)
            ).isoformat(),
            "nameservers": ["ns1.platform.app", "ns2.platform.app"],
        }
