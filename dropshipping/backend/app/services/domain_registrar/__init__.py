"""Domain registrar abstraction package for purchasing and managing domains.

Provides a unified interface for domain registration across multiple
registrars (ResellerClub, Squarespace Domains) with a mock provider
for development and testing.
"""

from app.services.domain_registrar.base import (
    AbstractDomainProvider,
    DomainPurchaseResult,
    DomainSearchResult,
)
from app.services.domain_registrar.factory import get_domain_provider
from app.services.domain_registrar.mock import MockDomainProvider

__all__ = [
    "AbstractDomainProvider",
    "DomainPurchaseResult",
    "DomainSearchResult",
    "MockDomainProvider",
    "get_domain_provider",
]
