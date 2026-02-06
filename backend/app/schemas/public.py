"""Pydantic schemas for public (unauthenticated) API endpoints.

These schemas shape the responses returned by the public-facing storefront
API. They intentionally omit sensitive fields like ``user_id`` that should
not be exposed to anonymous visitors.

**For Developers:**
    ``PublicStoreResponse`` is the serialisation shape for
    ``GET /api/v1/public/stores/{slug}``. It uses ``from_attributes`` for
    direct ORM-to-schema conversion.

**For QA Engineers:**
    - ``PublicStoreResponse`` must never include ``user_id``.
    - Only active stores should be returned by public endpoints.

**For End Users:**
    These are the data shapes you receive when browsing a store on the
    public storefront.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class PublicStoreResponse(BaseModel):
    """Public-facing store data returned to storefront visitors.

    Attributes:
        id: The store's unique identifier.
        name: Display name of the store.
        slug: URL-friendly unique slug used in the storefront URL.
        niche: The product niche or category.
        description: Optional longer description of the store.
        created_at: When the store was created.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    niche: str
    description: str | None
    created_at: datetime
