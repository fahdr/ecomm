"""ResellerClub domain registrar implementation.

Mock implementation of the ResellerClub API. In production, this would
use httpx to make real API calls to the ResellerClub HTTP API.

**For Developers:**
    This provider wraps the ResellerClub reseller API. Currently returns
    deterministic mock results for development and testing. Replace mock
    logic with real httpx calls for production use.

**For QA Engineers:**
    - All methods return deterministic results based on the input.
    - Order IDs use the ``rc-order-`` prefix.
    - Domains ending in ``taken.com`` are reported as unavailable.
    - Pricing is deterministic: .com=$12.99, .io=$29.99, .store=$2.99,
      others=$9.99.

**For Project Managers:**
    ResellerClub is one of the supported domain registrars. This
    implementation allows the platform to offer domain purchasing to
    merchants through the ResellerClub reseller program.

**For End Users:**
    You can purchase domain names through the platform. ResellerClub
    is one of the registrars available for domain registration.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.services.domain_registrar.base import (
    AbstractDomainProvider,
    DomainPurchaseResult,
    DomainSearchResult,
)


# Deterministic pricing by TLD
_TLD_PRICES = {
    "com": Decimal("12.99"),
    "io": Decimal("29.99"),
    "store": Decimal("2.99"),
    "net": Decimal("11.99"),
    "org": Decimal("10.99"),
    "co": Decimal("24.99"),
    "app": Decimal("14.99"),
}


class ResellerClubProvider(AbstractDomainProvider):
    """ResellerClub domain registrar using mock responses.

    In production, this would use httpx to call the ResellerClub API.
    Currently returns deterministic mock data for dev/test environments.

    Attributes:
        api_key: The ResellerClub API key.
        reseller_id: The ResellerClub reseller identifier.
    """

    def __init__(self, api_key: str = "", reseller_id: str = ""):
        """Initialize the ResellerClub provider.

        Args:
            api_key: ResellerClub API key.
            reseller_id: ResellerClub reseller ID.
        """
        self.api_key = api_key
        self.reseller_id = reseller_id

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
            price = _TLD_PRICES.get(tld, Decimal("9.99"))
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
            order_id=f"rc-order-{uuid.uuid4().hex[:12]}",
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
        price = _TLD_PRICES.get(tld, Decimal("9.99"))
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
            order_id=f"rc-renew-{uuid.uuid4().hex[:12]}",
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
            "registrar": "resellerclub",
            "expiry_date": (
                datetime.now(timezone.utc) + timedelta(days=365)
            ).isoformat(),
            "nameservers": ["ns1.platform.app", "ns2.platform.app"],
        }
