"""
Connector factory — maps platform types to concrete connector instances.

For Developers:
    Use ``get_connector(platform, store_url, credentials)`` to obtain
    the right adapter without hard-coding platform-specific imports in
    your service code.

    Example::

        from ecomm_connectors.factory import get_connector
        from ecomm_connectors.base import PlatformType

        connector = get_connector(PlatformType.shopify, url, creds)
        products, cursor = await connector.fetch_products(limit=50)

For QA Engineers:
    The factory validates that the platform type is supported and
    raises ``ConnectorError`` for unknown types.
"""

from __future__ import annotations

from ecomm_connectors.base import AbstractPlatformConnector, ConnectorError, PlatformType
from ecomm_connectors.platform import PlatformConnector
from ecomm_connectors.shopify import ShopifyConnector
from ecomm_connectors.woocommerce import WooCommerceConnector


def get_connector(
    platform: PlatformType | str,
    store_url: str,
    credentials: dict[str, str],
) -> AbstractPlatformConnector:
    """
    Instantiate the correct connector for the given platform type.

    For Developers:
        Accepts either a ``PlatformType`` enum or its string value.
        Returns a fully-initialized connector ready for API calls.

    Args:
        platform: Platform identifier (PlatformType enum or string).
        store_url: The remote store's base URL.
        credentials: Platform-specific credentials dict.

    Returns:
        An instance of the appropriate connector subclass.

    Raises:
        ConnectorError: If the platform type is not supported.
    """
    if isinstance(platform, str):
        try:
            platform = PlatformType(platform)
        except ValueError:
            raise ConnectorError(
                f"Unsupported platform: {platform}",
                platform=platform,
            )

    connectors: dict[PlatformType, type[AbstractPlatformConnector]] = {
        PlatformType.shopify: ShopifyConnector,
        PlatformType.woocommerce: WooCommerceConnector,
        PlatformType.platform: PlatformConnector,
    }

    connector_class = connectors.get(platform)
    if not connector_class:
        raise ConnectorError(
            f"Unsupported platform: {platform.value}",
            platform=platform.value,
        )

    return connector_class(store_url, credentials)
