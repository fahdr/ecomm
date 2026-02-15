"""Domain registrar provider factory.

Creates and returns the appropriate domain registrar provider instance
based on the application configuration. Defaults to the mock provider
for development.

**For Developers:**
    Call ``get_domain_provider()`` to obtain a provider instance. The
    provider mode is read from ``settings.domain_provider_mode``. Supported
    modes: ``mock``, ``resellerclub``, ``squarespace``.

**For QA Engineers:**
    - In test environments, ``domain_provider_mode`` defaults to ``"mock"``.
    - The factory returns a new instance on each call (no singleton).
    - Unknown modes fall back to the MockDomainProvider.

**For Project Managers:**
    The factory pattern decouples domain operations from a specific
    registrar, allowing the platform to switch registrars via a single
    config value.

**For End Users:**
    The platform automatically selects the right domain registrar based
    on your configuration. No manual setup is required.
"""

from app.services.domain_registrar.base import AbstractDomainProvider
from app.services.domain_registrar.mock import MockDomainProvider


def get_domain_provider() -> AbstractDomainProvider:
    """Create and return a domain registrar provider based on app settings.

    Reads ``settings.domain_provider_mode`` to determine which provider
    to instantiate. Falls back to MockDomainProvider for unknown modes.

    Returns:
        An instance of AbstractDomainProvider matching the configured mode.
    """
    from app.config import settings

    mode = getattr(settings, "domain_provider_mode", "mock")

    if mode == "resellerclub":
        from app.services.domain_registrar.resellerclub import ResellerClubProvider

        return ResellerClubProvider(
            api_key=getattr(settings, "resellerclub_api_key", ""),
            reseller_id=getattr(settings, "resellerclub_reseller_id", ""),
        )
    elif mode == "squarespace":
        from app.services.domain_registrar.squarespace import SquarespaceDomainProvider

        return SquarespaceDomainProvider(
            api_key=getattr(settings, "squarespace_api_key", ""),
        )

    return MockDomainProvider()
