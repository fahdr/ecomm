"""
Ecommerce platform connectors for the ecomm SaaS suite.

For Developers:
    Provides abstract and concrete connectors for Shopify, WooCommerce,
    and the internal dropshipping platform. Use ``get_connector()`` to
    obtain the right adapter for a given platform type.

For QA Engineers:
    All connectors share the same interface (``AbstractPlatformConnector``)
    so integration tests can be written once and run against any backend.
"""

__version__ = "0.1.0"
