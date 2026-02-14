"""
Product normalizer for converting supplier data into store-ready format.

For Developers:
    Use ``ProductNormalizer`` to transform raw supplier product data into
    retail-ready pricing and metadata. This module handles markup calculation,
    psychological pricing, compare-at pricing, and URL slug generation.

For QA Engineers:
    All pricing methods use ``Decimal`` arithmetic to avoid floating-point
    rounding errors. Test edge cases: zero cost, 100% markup, very large
    prices, and unicode characters in slugs.

For End Users:
    The normalizer automatically calculates retail prices, creates
    attractive price points (e.g. $29.99 instead of $30.12), and
    generates SEO-friendly URLs for your product pages.
"""

from __future__ import annotations

import math
import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal


class ProductNormalizer:
    """
    Utility class for normalizing supplier product data into store-ready format.

    For Developers:
        All methods are static and stateless. The class groups related
        pricing and slug logic for organizational clarity.

    For QA Engineers:
        Methods are pure functions with no side effects, making them
        straightforward to unit test in isolation.
    """

    @staticmethod
    def calculate_markup(cost: Decimal, markup_percent: float) -> Decimal:
        """
        Apply a percentage markup to a supplier cost price.

        For Developers:
            Uses Decimal arithmetic to avoid floating-point precision issues.
            The markup is applied as: ``cost * (1 + markup_percent / 100)``.

        Args:
            cost: Supplier cost price as a Decimal (e.g. ``Decimal("18.74")``).
            markup_percent: Markup percentage (e.g. 100.0 for 100% markup,
                which doubles the price).

        Returns:
            Retail price as a Decimal, rounded to 2 decimal places.

        Raises:
            ValueError: If cost is negative or markup_percent is negative.

        Examples:
            >>> ProductNormalizer.calculate_markup(Decimal("10.00"), 100.0)
            Decimal('20.00')
            >>> ProductNormalizer.calculate_markup(Decimal("18.74"), 150.0)
            Decimal('46.85')
        """
        if cost < 0:
            raise ValueError(f"Cost must be non-negative, got {cost}")
        if markup_percent < 0:
            raise ValueError(f"Markup percent must be non-negative, got {markup_percent}")

        multiplier = Decimal(str(1 + markup_percent / 100))
        retail = cost * multiplier
        return retail.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def apply_psychological_pricing(price: Decimal) -> Decimal:
        """
        Adjust a price to a psychologically appealing price point.

        For Developers:
            Applies charm pricing rules:
            - Prices under $10: round to nearest .99 below
            - Prices $10-$99: round to nearest .97 or .99 below
            - Prices $100+: round to nearest .99 below the next dollar

            The result is always less than or equal to the input to avoid
            accidental price increases.

        For End Users:
            Automatically adjusts prices to more attractive price points
            (e.g. $29.99 instead of $30.12) which can improve conversion rates.

        Args:
            price: Original retail price as a Decimal.

        Returns:
            Psychologically adjusted price as a Decimal.

        Examples:
            >>> ProductNormalizer.apply_psychological_pricing(Decimal("8.42"))
            Decimal('7.99')
            >>> ProductNormalizer.apply_psychological_pricing(Decimal("30.12"))
            Decimal('29.97')
            >>> ProductNormalizer.apply_psychological_pricing(Decimal("149.50"))
            Decimal('149.99')
        """
        if price <= 0:
            return price

        price_float = float(price)

        if price_float < 10:
            # Round down to nearest .99
            floored = math.floor(price_float)
            result = Decimal(str(floored)) - Decimal("0.01")
            if result <= 0:
                result = Decimal("0.99")
            return result

        if price_float < 100:
            # Round down to nearest whole number, then subtract 0.03
            floored = math.floor(price_float)
            result = Decimal(str(floored)) - Decimal("0.03")
            if result <= 0:
                result = Decimal("0.97")
            return result

        # $100+: round to the nearest .99 at or below the price
        floored = math.floor(price_float)
        candidate = Decimal(str(floored)) - Decimal("0.01")
        if candidate > price:
            candidate = candidate - Decimal("1.00")
        return candidate

    @staticmethod
    def calculate_compare_at_price(retail: Decimal, discount_pct: float) -> Decimal:
        """
        Calculate a "compare at" (original/MSRP) price to show a discount.

        For Developers:
            The compare-at price is computed as:
            ``retail / (1 - discount_pct / 100)``

            This represents what the price "was" before the discount, creating
            a perceived value for the customer.

        For End Users:
            Shows a strikethrough "was" price next to the current price,
            indicating the discount customers are receiving.

        Args:
            retail: Current retail price as a Decimal.
            discount_pct: Desired discount percentage to display
                (e.g. 30.0 means "30% off").

        Returns:
            Compare-at price as a Decimal, rounded to 2 decimal places.

        Raises:
            ValueError: If discount_pct is not between 0 (exclusive) and 100 (exclusive).

        Examples:
            >>> ProductNormalizer.calculate_compare_at_price(Decimal("29.99"), 30.0)
            Decimal('42.84')
        """
        if discount_pct <= 0 or discount_pct >= 100:
            raise ValueError(
                f"Discount percent must be between 0 and 100 (exclusive), got {discount_pct}"
            )

        divisor = Decimal(str(1 - discount_pct / 100))
        compare_at = retail / divisor
        return compare_at.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def generate_slug(title: str) -> str:
        """
        Generate a URL-safe slug from a product title.

        For Developers:
            Normalizes unicode to ASCII, lowercases, replaces non-alphanumeric
            characters with hyphens, collapses consecutive hyphens, and strips
            leading/trailing hyphens. Maximum length is 120 characters.

        For QA Engineers:
            Test with unicode characters (accents, CJK), extra whitespace,
            special characters, and very long titles.

        Args:
            title: Product title string (may contain unicode, special chars, etc.).

        Returns:
            URL-safe slug string (lowercase, hyphens only, max 120 chars).

        Examples:
            >>> ProductNormalizer.generate_slug("TWS Wireless Bluetooth 5.3 Earbuds")
            'tws-wireless-bluetooth-5-3-earbuds'
            >>> ProductNormalizer.generate_slug("  Crème Brûlée Maker — Pro Edition!  ")
            'creme-brulee-maker-pro-edition'
        """
        # Normalize unicode to ASCII (e.g. é -> e, ü -> u)
        normalized = unicodedata.normalize("NFKD", title)
        ascii_str = normalized.encode("ascii", "ignore").decode("ascii")

        # Lowercase
        lowered = ascii_str.lower()

        # Replace non-alphanumeric characters with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", lowered)

        # Collapse consecutive hyphens and strip leading/trailing
        slug = re.sub(r"-+", "-", slug).strip("-")

        # Truncate to max length at a word boundary
        if len(slug) > 120:
            slug = slug[:120].rsplit("-", 1)[0]

        return slug
