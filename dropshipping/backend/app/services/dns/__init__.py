"""DNS provider abstraction package for managing DNS records.

Provides a unified interface for DNS record management across multiple
providers (Cloudflare, Route53, Google Cloud DNS) with a mock provider
for development and testing.
"""

from app.services.dns.base import AbstractDnsProvider, DnsRecord
from app.services.dns.factory import get_dns_provider
from app.services.dns.mock import MockDnsProvider

__all__ = [
    "AbstractDnsProvider",
    "DnsRecord",
    "MockDnsProvider",
    "get_dns_provider",
]
