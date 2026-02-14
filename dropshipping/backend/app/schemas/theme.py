"""Pydantic schemas for store theme API endpoints.

Defines request and response shapes for theme CRUD operations, theme
activation, and the public theme endpoint used by the storefront.

**For Developers:**
    ``CreateThemeRequest`` is used for POST (creating from a preset clone).
    ``UpdateThemeRequest`` is used for PATCH (partial updates to any field).
    ``ThemeResponse`` is the full response for authenticated dashboard users.
    ``PublicThemeResponse`` is the public-facing response for storefronts.

**For QA Engineers:**
    - ``CreateThemeRequest.clone_from`` is optional — if provided, the new theme
      clones the specified preset's config.
    - ``UpdateThemeRequest`` allows partial updates — only provided fields change.
    - ``ThemeResponse`` includes ``is_preset`` and ``is_active`` flags.
    - ``PublicThemeResponse`` omits internal fields (id, store_id, is_preset, etc.).
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateThemeRequest(BaseModel):
    """Request body for creating a new theme.

    Attributes:
        name: Display name for the new theme.
        clone_from: Optional preset theme name to clone configuration from.
    """

    name: str = Field(..., min_length=1, max_length=100)
    clone_from: str | None = Field(
        None,
        description="Name of a preset theme to clone config from (e.g., 'Frosted')",
    )


class UpdateThemeRequest(BaseModel):
    """Request body for updating a theme (partial update).

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: New display name.
        colors: Color palette dict (hex values).
        typography: Typography config dict (font names and weights).
        styles: Style options dict (border_radius, card_style, button_style).
        blocks: Ordered list of page block configurations.
        logo_url: Store logo URL.
        favicon_url: Store favicon URL.
        custom_css: Custom CSS for the storefront.
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    colors: dict[str, str] | None = None
    typography: dict[str, str] | None = None
    styles: dict[str, str] | None = None
    blocks: list[dict[str, Any]] | None = None
    logo_url: str | None = None
    favicon_url: str | None = None
    custom_css: str | None = None


class ThemeResponse(BaseModel):
    """Full theme response for authenticated dashboard API.

    Attributes:
        id: Theme UUID.
        store_id: Owning store UUID.
        name: Theme display name.
        is_active: Whether this is the currently active theme.
        is_preset: Whether this is a system preset.
        colors: Color palette configuration.
        typography: Typography configuration.
        styles: Style options.
        blocks: Ordered page block configurations.
        logo_url: Store logo URL.
        favicon_url: Store favicon URL.
        custom_css: Custom CSS.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    is_active: bool
    is_preset: bool
    colors: dict[str, str]
    typography: dict[str, str]
    styles: dict[str, str]
    blocks: list[dict[str, Any]]
    logo_url: str | None
    favicon_url: str | None
    custom_css: str | None
    created_at: datetime
    updated_at: datetime


class PublicThemeResponse(BaseModel):
    """Public-facing theme response for the storefront.

    Omits internal fields like ``store_id``, ``is_preset``, and timestamps.
    Includes everything the storefront needs to render the theme.

    Attributes:
        name: Theme display name.
        colors: Color palette configuration.
        typography: Typography configuration.
        styles: Style options.
        blocks: Ordered page block configurations.
        logo_url: Store logo URL.
        favicon_url: Store favicon URL.
        custom_css: Custom CSS.
    """

    model_config = {"from_attributes": True}

    name: str
    colors: dict[str, str]
    typography: dict[str, str]
    styles: dict[str, str]
    blocks: list[dict[str, Any]]
    logo_url: str | None
    favicon_url: str | None
    custom_css: str | None
