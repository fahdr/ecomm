"""
Factory for creating supplier client instances.

For Developers:
    Use ``SupplierFactory.create(supplier_type)`` to obtain the right
    supplier client without hard-coding supplier-specific imports in your
    service code. Supports all registered supplier integrations.

    Example::

        from ecomm_suppliers.factory import SupplierFactory

        client = SupplierFactory.create("aliexpress")
        results = await client.search_products("wireless earbuds")
        await client.close()

For QA Engineers:
    The factory validates the supplier type and raises ``SupplierError``
    for unknown types. Use ``SupplierFactory.supported_suppliers()`` to
    verify the list of registered suppliers.

For End Users:
    The system automatically selects the correct supplier integration
    based on where you want to source products from.
"""

from __future__ import annotations

from ecomm_suppliers.aliexpress import AliExpressClient
from ecomm_suppliers.base import BaseSupplierClient, SupplierError
from ecomm_suppliers.cjdropship import CJDropshipClient

# Registry mapping supplier type strings to their client classes
_SUPPLIER_REGISTRY: dict[str, type[BaseSupplierClient]] = {
    "aliexpress": AliExpressClient,
    "cjdropship": CJDropshipClient,
}


class SupplierFactory:
    """
    Factory for creating supplier client instances by type name.

    For Developers:
        Centralizes supplier client construction so service code does not
        need to import specific supplier modules. New suppliers can be added
        by registering them in the ``_SUPPLIER_REGISTRY`` dict.

    For QA Engineers:
        The factory is stateless; ``create()`` and ``supported_suppliers()``
        are both static methods with no side effects.
    """

    @staticmethod
    def create(supplier_type: str, **kwargs: str | None) -> BaseSupplierClient:
        """
        Create a supplier client instance for the given supplier type.

        Args:
            supplier_type: Supplier platform identifier. Supported values:
                ``"aliexpress"``, ``"cjdropship"``.
            **kwargs: Additional keyword arguments passed to the supplier
                client constructor (e.g. ``api_key="your-key-here"``).

        Returns:
            An initialized ``BaseSupplierClient`` subclass instance ready
            for API calls.

        Raises:
            SupplierError: If the supplier type is not recognized.

        Examples:
            >>> client = SupplierFactory.create("aliexpress")
            >>> client = SupplierFactory.create("cjdropship", api_key="abc123")
        """
        supplier_key = supplier_type.lower().strip()
        client_class = _SUPPLIER_REGISTRY.get(supplier_key)

        if client_class is None:
            supported = ", ".join(sorted(_SUPPLIER_REGISTRY.keys()))
            raise SupplierError(
                f"Unsupported supplier type: '{supplier_type}'. "
                f"Supported types: {supported}",
                supplier=supplier_type,
            )

        return client_class(**kwargs)

    @staticmethod
    def supported_suppliers() -> list[str]:
        """
        Return a sorted list of all supported supplier type identifiers.

        Returns:
            List of supplier type strings (e.g. ["aliexpress", "cjdropship"]).
        """
        return sorted(_SUPPLIER_REGISTRY.keys())

    @staticmethod
    def register(supplier_type: str, client_class: type[BaseSupplierClient]) -> None:
        """
        Register a new supplier client class in the factory.

        For Developers:
            Use this to extend the factory with custom supplier integrations
            at runtime. The supplier type string is case-insensitive and will
            be lowercased for storage.

        Args:
            supplier_type: Unique identifier for the supplier (e.g. "spocket").
            client_class: The supplier client class (must be a subclass of
                ``BaseSupplierClient``).

        Raises:
            TypeError: If client_class is not a subclass of BaseSupplierClient.
        """
        if not (isinstance(client_class, type) and issubclass(client_class, BaseSupplierClient)):
            raise TypeError(
                f"client_class must be a subclass of BaseSupplierClient, "
                f"got {type(client_class)}"
            )
        _SUPPLIER_REGISTRY[supplier_type.lower().strip()] = client_class
