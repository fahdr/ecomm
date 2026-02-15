"""Mock domain registrar provider for development and testing.

Provides a fully functional mock domain registrar that returns
deterministic results without making any external API calls.

**For Developers:**
    The mock provider returns deterministic results based on input. Domains
    ending in ``taken.com`` are reported as unavailable. Pricing is fixed
    per TLD. Purchase operations always succeed with predictable order IDs.

**For QA Engineers:**
    - ``search_domains`` returns one result per TLD with fixed pricing.
    - Domains ending in ``taken.com`` are unavailable; all others available.
    - ``purchase_domain`` always returns status="success".
    - ``renew_domain`` always returns status="success".
    - ``set_nameservers`` always returns True.
    - Order IDs use ``mock-order-`` or ``mock-renew-`` prefix.

**For Project Managers:**
    The mock provider enables local development and automated testing
    without requiring real domain registrar credentials or API access.

**For End Users:**
    This provider is used internally during development. In production,
    domain purchases go through real registrars (ResellerClub or
    Squarespace Domains).
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
    "com": Decimal("10.99"),
    "io": Decimal("25.99"),
    "store": Decimal("1.99"),
    "net": Decimal("10.99"),
    "org": Decimal("9.99"),
    "co": Decimal("22.99"),
    "app": Decimal("12.99"),
}


class MockDomainProvider(AbstractDomainProvider):
    """In-memory mock domain registrar for development and testing.

    Returns deterministic results for all operations without making
    any external API calls.
    """

    async def search_domains(
        self, query: str, tlds: list[str]
    ) -> list[DomainSearchResult]:
        """Search for available domains across TLDs (mock).

        Args:
            query: The domain name query (without TLD).
            tlds: List of TLD extensions to search.

        Returns:
            List of DomainSearchResult, one per TLD. Domains ending in
            ``taken`` are reported as unavailable.
        """
        results = []
        for tld in tlds:
            domain = f"{query}.{tld}"
            # Domains with "taken" in the query are unavailable
            available = "taken" not in query.lower()
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
            DomainPurchaseResult with mock order details (always succeeds).
        """
        return DomainPurchaseResult(
            domain=domain,
            order_id=f"mock-order-{uuid.uuid4().hex[:12]}",
            status="success",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365 * years),
        )

    async def check_availability(self, domain: str) -> DomainSearchResult:
        """Check domain availability (mock).

        Args:
            domain: The domain to check.

        Returns:
            DomainSearchResult. Domains with "taken" in the name are
            unavailable; all others are available.
        """
        tld = domain.rsplit(".", 1)[-1] if "." in domain else "com"
        available = "taken" not in domain.lower()
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
            DomainPurchaseResult with renewal details (always succeeds).
        """
        return DomainPurchaseResult(
            domain=domain,
            order_id=f"mock-renew-{uuid.uuid4().hex[:12]}",
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
            "registrar": "mock",
            "expiry_date": (
                datetime.now(timezone.utc) + timedelta(days=365)
            ).isoformat(),
            "nameservers": ["ns1.platform.app", "ns2.platform.app"],
        }
