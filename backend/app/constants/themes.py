"""Preset theme definitions for the store theme engine.

Contains the 7 built-in theme presets that are seeded for every new store.
Each preset includes a complete color palette, typography config, style options,
and a default block layout tailored to its aesthetic.

**For Developers:**
    Import ``PRESET_THEMES`` to seed themes for new stores or in migrations.
    Each preset is a dict matching the StoreTheme model's JSON columns.
    The ``CURATED_FONTS`` dicts list all supported Google Fonts for headings
    and body text — the dashboard theme editor uses these lists.

**For QA Engineers:**
    - Every new store should get all 7 presets, with "Frosted" as the active default.
    - Color values are CSS color strings (hex for storage, converted to OKLCH in frontend).
    - Font names must match exactly what Google Fonts provides.

**For Project Managers:**
    These presets provide immediate value out of the box. Store owners can use
    them as-is or clone them to create custom themes. AI automation will also
    use this structure to generate new themes based on product genre.
"""

# Curated heading fonts available for theme customization.
HEADING_FONTS: list[dict[str, str]] = [
    {"name": "Bricolage Grotesque", "category": "sans-serif"},
    {"name": "Fraunces", "category": "serif"},
    {"name": "Playfair Display", "category": "serif"},
    {"name": "Syne", "category": "sans-serif"},
    {"name": "Outfit", "category": "sans-serif"},
    {"name": "DM Serif Display", "category": "serif"},
    {"name": "Unbounded", "category": "sans-serif"},
    {"name": "Archivo Black", "category": "sans-serif"},
    {"name": "Cormorant Garamond", "category": "serif"},
    {"name": "Josefin Sans", "category": "sans-serif"},
    {"name": "Bitter", "category": "serif"},
    {"name": "Libre Baskerville", "category": "serif"},
]

# Curated body fonts available for theme customization.
BODY_FONTS: list[dict[str, str]] = [
    {"name": "Instrument Sans", "category": "sans-serif"},
    {"name": "Source Sans 3", "category": "sans-serif"},
    {"name": "Nunito", "category": "sans-serif"},
    {"name": "Lora", "category": "serif"},
    {"name": "Work Sans", "category": "sans-serif"},
    {"name": "DM Sans", "category": "sans-serif"},
    {"name": "Karla", "category": "sans-serif"},
    {"name": "Crimson Text", "category": "serif"},
]

# Block types available for page composition.
BLOCK_TYPES: list[str] = [
    "hero_banner",
    "featured_products",
    "categories_grid",
    "product_carousel",
    "reviews",
    "newsletter",
    "custom_text",
    "image_banner",
    "spacer",
]


def _default_blocks() -> list[dict]:
    """Return the default block layout for most themes.

    Returns:
        Ordered list of block configurations for a typical homepage.
    """
    return [
        {
            "id": "hero",
            "type": "hero_banner",
            "enabled": True,
            "config": {
                "title": "Welcome to our store",
                "subtitle": "Discover amazing products at great prices",
                "cta_text": "Shop Now",
                "cta_link": "/products",
                "bg_type": "gradient",
                "bg_value": "",
                "text_align": "center",
            },
        },
        {
            "id": "featured",
            "type": "featured_products",
            "enabled": True,
            "config": {
                "title": "Featured Products",
                "count": 8,
                "columns": 4,
                "show_prices": True,
                "show_badges": True,
            },
        },
        {
            "id": "categories",
            "type": "categories_grid",
            "enabled": True,
            "config": {
                "title": "Shop by Category",
                "columns": 3,
                "show_product_count": True,
            },
        },
        {
            "id": "reviews",
            "type": "reviews",
            "enabled": True,
            "config": {
                "title": "What Our Customers Say",
                "count": 6,
                "layout": "grid",
            },
        },
        {
            "id": "newsletter",
            "type": "newsletter",
            "enabled": True,
            "config": {
                "title": "Stay in the loop",
                "subtitle": "Subscribe to get the latest deals and updates",
                "button_text": "Subscribe",
            },
        },
    ]


# The 7 preset themes, each with complete configuration.
PRESET_THEMES: list[dict] = [
    {
        "name": "Frosted",
        "colors": {
            "background": "#faf9f7",
            "foreground": "#1a1a2e",
            "card": "#f5f4f1",
            "card_foreground": "#1a1a2e",
            "primary": "#0d9488",
            "primary_foreground": "#faf9f7",
            "secondary": "#f0efec",
            "secondary_foreground": "#1a1a2e",
            "muted": "#e8e7e4",
            "muted_foreground": "#6b6b7b",
            "accent": "#d4a259",
            "accent_foreground": "#1a1a2e",
            "destructive": "#dc4a3a",
            "border": "#e2e1de",
            "ring": "#0d9488",
        },
        "typography": {
            "heading_font": "Bricolage Grotesque",
            "body_font": "Instrument Sans",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "700",
        },
        "styles": {
            "border_radius": "md",
            "card_style": "elevated",
            "button_style": "rounded",
        },
        "blocks": _default_blocks(),
    },
    {
        "name": "Midnight",
        "colors": {
            "background": "#0f1729",
            "foreground": "#e2e8f0",
            "card": "#1a2540",
            "card_foreground": "#e2e8f0",
            "primary": "#22d3ee",
            "primary_foreground": "#0f1729",
            "secondary": "#1e293b",
            "secondary_foreground": "#e2e8f0",
            "muted": "#1e293b",
            "muted_foreground": "#94a3b8",
            "accent": "#c0c0d0",
            "accent_foreground": "#0f1729",
            "destructive": "#f87171",
            "border": "#2a3a5c",
            "ring": "#22d3ee",
        },
        "typography": {
            "heading_font": "Syne",
            "body_font": "Instrument Sans",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "700",
        },
        "styles": {
            "border_radius": "sm",
            "card_style": "glass",
            "button_style": "rounded",
        },
        "blocks": _default_blocks(),
    },
    {
        "name": "Botanical",
        "colors": {
            "background": "#fdf8f0",
            "foreground": "#2d3b2d",
            "card": "#f5efe3",
            "card_foreground": "#2d3b2d",
            "primary": "#2d6a4f",
            "primary_foreground": "#fdf8f0",
            "secondary": "#ede8dc",
            "secondary_foreground": "#2d3b2d",
            "muted": "#e6dfd3",
            "muted_foreground": "#6b7b6b",
            "accent": "#c67a4a",
            "accent_foreground": "#fdf8f0",
            "destructive": "#c0392b",
            "border": "#d9d2c5",
            "ring": "#2d6a4f",
        },
        "typography": {
            "heading_font": "Fraunces",
            "body_font": "Lora",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "600",
        },
        "styles": {
            "border_radius": "lg",
            "card_style": "elevated",
            "button_style": "rounded",
        },
        "blocks": _default_blocks(),
    },
    {
        "name": "Neon",
        "colors": {
            "background": "#0a0a0f",
            "foreground": "#f0f0f5",
            "card": "#15151f",
            "card_foreground": "#f0f0f5",
            "primary": "#e91e90",
            "primary_foreground": "#0a0a0f",
            "secondary": "#1a1a25",
            "secondary_foreground": "#f0f0f5",
            "muted": "#1a1a25",
            "muted_foreground": "#8888a0",
            "accent": "#84cc16",
            "accent_foreground": "#0a0a0f",
            "destructive": "#ff4444",
            "border": "#2a2a3a",
            "ring": "#e91e90",
        },
        "typography": {
            "heading_font": "Unbounded",
            "body_font": "DM Sans",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "700",
        },
        "styles": {
            "border_radius": "sm",
            "card_style": "flat",
            "button_style": "square",
        },
        "blocks": _default_blocks(),
    },
    {
        "name": "Luxe",
        "colors": {
            "background": "#faf8f5",
            "foreground": "#1a1a1a",
            "card": "#f5f2ed",
            "card_foreground": "#1a1a1a",
            "primary": "#b8860b",
            "primary_foreground": "#faf8f5",
            "secondary": "#ede9e3",
            "secondary_foreground": "#1a1a1a",
            "muted": "#e5e0d8",
            "muted_foreground": "#7a7a7a",
            "accent": "#1a1a1a",
            "accent_foreground": "#faf8f5",
            "destructive": "#b91c1c",
            "border": "#d9d4cc",
            "ring": "#b8860b",
        },
        "typography": {
            "heading_font": "Playfair Display",
            "body_font": "Crimson Text",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "700",
        },
        "styles": {
            "border_radius": "sm",
            "card_style": "flat",
            "button_style": "rounded",
        },
        "blocks": _default_blocks(),
    },
    {
        "name": "Playful",
        "colors": {
            "background": "#ffffff",
            "foreground": "#1e293b",
            "card": "#f8fafc",
            "card_foreground": "#1e293b",
            "primary": "#f97316",
            "primary_foreground": "#ffffff",
            "secondary": "#f1f5f9",
            "secondary_foreground": "#1e293b",
            "muted": "#e2e8f0",
            "muted_foreground": "#64748b",
            "accent": "#38bdf8",
            "accent_foreground": "#1e293b",
            "destructive": "#ef4444",
            "border": "#e2e8f0",
            "ring": "#f97316",
        },
        "typography": {
            "heading_font": "Outfit",
            "body_font": "Nunito",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "700",
        },
        "styles": {
            "border_radius": "lg",
            "card_style": "elevated",
            "button_style": "pill",
        },
        "blocks": _default_blocks(),
    },
    {
        "name": "Industrial",
        "colors": {
            "background": "#f0f0f0",
            "foreground": "#1a1a1a",
            "card": "#e8e8e8",
            "card_foreground": "#1a1a1a",
            "primary": "#333333",
            "primary_foreground": "#f0f0f0",
            "secondary": "#d5d5d5",
            "secondary_foreground": "#1a1a1a",
            "muted": "#cccccc",
            "muted_foreground": "#666666",
            "accent": "#b34a2a",
            "accent_foreground": "#f0f0f0",
            "destructive": "#c0392b",
            "border": "#c0c0c0",
            "ring": "#333333",
        },
        "typography": {
            "heading_font": "Archivo Black",
            "body_font": "Work Sans",
            "mono_font": "IBM Plex Mono",
            "heading_weight": "400",
        },
        "styles": {
            "border_radius": "sm",
            "card_style": "flat",
            "button_style": "square",
        },
        "blocks": [
            {
                "id": "featured",
                "type": "featured_products",
                "enabled": True,
                "config": {
                    "title": "Products",
                    "count": 12,
                    "columns": 4,
                    "show_prices": True,
                    "show_badges": False,
                },
            },
            {
                "id": "categories",
                "type": "categories_grid",
                "enabled": True,
                "config": {
                    "title": "Categories",
                    "columns": 4,
                    "show_product_count": True,
                },
            },
            {
                "id": "spacer",
                "type": "spacer",
                "enabled": True,
                "config": {"height": "lg"},
            },
        ],
    },
]

# The default theme name that gets activated for new stores.
DEFAULT_THEME_NAME = "Frosted"
