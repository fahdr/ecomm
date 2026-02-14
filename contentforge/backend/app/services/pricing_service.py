"""
Pricing calculation service — applies markup and psychological rounding
strategies to product costs.

For Developers:
    `calculate_price()` is the main entry point. It takes a base cost,
    markup percentage, and rounding strategy, and returns the final price.

    Strategies:
    - "round_99": Rounds to $X.99 (e.g., $24.99) — most common in e-commerce
    - "round_95": Rounds to $X.95 (e.g., $24.95) — slightly premium feel
    - "round_00": Rounds to whole dollars (e.g., $25.00) — luxury/clean pricing
    - "none": Exact markup, no rounding (e.g., $24.37)

    The markup is applied as: final = cost * (1 + markup_percent / 100)
    Then the rounding strategy adjusts the result.

For QA Engineers:
    Test edge cases:
    - Zero cost should return 0 regardless of markup
    - Very large markups (1000%) should calculate correctly
    - Negative costs should raise ValueError
    - Each strategy should produce predictable outputs
    - Floating point precision: verify results are rounded to 2 decimal places

For Project Managers:
    Pricing strategy is critical for dropshipping profitability. The
    psychological rounding strategies are proven to increase conversions:
    $X.99 creates a "deal" perception, while whole numbers signal quality.

For End Users:
    Use the pricing calculator to determine optimal selling prices. Choose
    a markup percentage and a rounding strategy that matches your brand.
"""

import math


def calculate_price(
    cost: float,
    markup_percent: float,
    strategy: str = "round_99",
) -> float:
    """
    Calculate a selling price from cost with markup and psychological rounding.

    Applies the markup percentage to the base cost, then applies the selected
    rounding strategy for psychological pricing.

    Args:
        cost: Base cost of the product (must be >= 0).
        markup_percent: Markup as a percentage (e.g., 50 for 50% markup).
        strategy: Rounding strategy — "round_99", "round_95", "round_00", or "none".

    Returns:
        The calculated selling price, rounded to 2 decimal places.

    Raises:
        ValueError: If cost is negative or strategy is unknown.

    Examples:
        >>> calculate_price(10.00, 50, "round_99")
        14.99
        >>> calculate_price(10.00, 50, "round_95")
        14.95
        >>> calculate_price(10.00, 50, "round_00")
        15.0
        >>> calculate_price(10.00, 50, "none")
        15.0
    """
    if cost < 0:
        raise ValueError("Cost must be non-negative")

    if strategy not in ("round_99", "round_95", "round_00", "none"):
        raise ValueError(f"Unknown pricing strategy: {strategy}")

    if cost == 0:
        return 0.0

    # Apply markup
    price = cost * (1 + markup_percent / 100)

    # Apply rounding strategy
    if strategy == "round_99":
        # Round up to nearest dollar, then subtract 0.01
        price = math.ceil(price) - 0.01
    elif strategy == "round_95":
        # Round up to nearest dollar, then subtract 0.05
        price = math.ceil(price) - 0.05
    elif strategy == "round_00":
        # Round to nearest whole dollar
        price = round(price)
    # "none" — keep exact markup result

    return round(price, 2)


def calculate_bulk_prices(
    items: list[dict],
    default_markup: float = 50.0,
    default_strategy: str = "round_99",
) -> list[dict]:
    """
    Calculate prices for a list of product items.

    Each item dict should have a "cost" key. Optional "markup_percent"
    and "strategy" keys override the defaults for that item.

    Args:
        items: List of dicts with at least {"cost": float}.
        default_markup: Default markup percentage for items without one.
        default_strategy: Default rounding strategy for items without one.

    Returns:
        List of dicts with original data plus "selling_price" and "profit" keys.

    Examples:
        >>> calculate_bulk_prices([{"cost": 10, "name": "Widget"}], 50, "round_99")
        [{"cost": 10, "name": "Widget", "selling_price": 14.99, "profit": 4.99}]
    """
    results = []
    for item in items:
        cost = item.get("cost", 0)
        markup = item.get("markup_percent", default_markup)
        strategy = item.get("strategy", default_strategy)

        selling_price = calculate_price(cost, markup, strategy)
        profit = round(selling_price - cost, 2)

        result = {**item, "selling_price": selling_price, "profit": profit}
        results.append(result)

    return results
