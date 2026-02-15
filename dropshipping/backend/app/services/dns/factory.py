"""DNS provider factory.

Creates and returns the appropriate DNS provider instance based on the
application configuration. Defaults to the mock provider for development.

**For Developers:**
    Call ``get_dns_provider()`` to obtain a provider instance. The provider
    mode is read from ``settings.dns_provider_mode``. Supported modes:
    ``mock``, ``cloudflare``, ``route53``, ``google``.

**For QA Engineers:**
    - In test environments, ``dns_provider_mode`` defaults to ``"mock"``.
    - The factory returns a new instance on each call (no singleton).
    - Unknown modes fall back to the MockDnsProvider.

**For Project Managers:**
    The factory pattern decouples DNS operations from a specific provider,
    allowing the platform to switch providers via a single config value.

**For End Users:**
    The platform automatically selects the right DNS provider based on
    your configuration. No manual setup is required.
"""

from app.services.dns.base import AbstractDnsProvider
from app.services.dns.mock import MockDnsProvider


def get_dns_provider() -> AbstractDnsProvider:
    """Create and return a DNS provider based on application settings.

    Reads ``settings.dns_provider_mode`` to determine which provider
    to instantiate. Falls back to MockDnsProvider for unknown modes.

    Returns:
        An instance of AbstractDnsProvider matching the configured mode.
    """
    from app.config import settings

    mode = getattr(settings, "dns_provider_mode", "mock")

    if mode == "cloudflare":
        from app.services.dns.cloudflare import CloudflareDnsProvider

        return CloudflareDnsProvider(
            api_token=getattr(settings, "cloudflare_api_token", ""),
        )
    elif mode == "route53":
        from app.services.dns.route53 import Route53DnsProvider

        return Route53DnsProvider(
            access_key_id=getattr(settings, "route53_access_key_id", ""),
            secret_access_key=getattr(settings, "route53_secret_access_key", ""),
            region=getattr(settings, "route53_region", "us-east-1"),
        )
    elif mode == "google":
        from app.services.dns.google_dns import GoogleCloudDnsProvider

        return GoogleCloudDnsProvider(
            project_id=getattr(settings, "google_dns_project_id", ""),
            credentials_json=getattr(settings, "google_dns_credentials_json", ""),
        )

    return MockDnsProvider()
