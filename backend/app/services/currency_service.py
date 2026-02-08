"""Currency conversion service.

Provides multi-currency support with static exchange rates for MVP.
In production, rates would be fetched from a live API (e.g. Open
Exchange Rates, Fixer.io) and cached.

**For Developers:**
    Exchange rates are stored as a module-level dict relative to USD
    as the base currency. ``convert_price`` handles bidirectional
    conversion through USD as an intermediary. ``get_store_currency``
    reads the store's configured currency (defaults to USD).

**For QA Engineers:**
    - ``get_supported_currencies`` returns all available currencies with
      metadata (name, symbol, code).
    - ``convert_price`` validates both source and target currencies.
    - Conversion goes from_currency -> USD -> to_currency for accuracy.
    - ``get_store_currency`` returns "USD" if the store doesn't have a
      ``currency`` field.

**For Project Managers:**
    This service powers Feature 21 (Multi-Currency) from the backlog.
    It enables storefronts to display prices in the customer's preferred
    currency.

**For End Users:**
    View product prices in your preferred currency. The conversion rate
    is approximate and the actual charge will be in the store's base
    currency.
"""

import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store


# ---------------------------------------------------------------------------
# Static exchange rates relative to USD (base currency).
# In production, these would be fetched from an external API and cached.
# ---------------------------------------------------------------------------
EXCHANGE_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.53,
    "JPY": 149.5,
    "CHF": 0.88,
    "CNY": 7.24,
    "INR": 83.12,
    "BRL": 4.97,
    "MXN": 17.15,
    "SGD": 1.34,
    "HKD": 7.82,
    "KRW": 1325.0,
    "SEK": 10.42,
    "NOK": 10.53,
    "DKK": 6.87,
    "NZD": 1.63,
    "ZAR": 18.65,
    "PLN": 4.02,
}

CURRENCY_INFO: dict[str, dict] = {
    "USD": {"name": "US Dollar", "symbol": "$", "decimals": 2},
    "EUR": {"name": "Euro", "symbol": "\u20ac", "decimals": 2},
    "GBP": {"name": "British Pound", "symbol": "\u00a3", "decimals": 2},
    "CAD": {"name": "Canadian Dollar", "symbol": "CA$", "decimals": 2},
    "AUD": {"name": "Australian Dollar", "symbol": "A$", "decimals": 2},
    "JPY": {"name": "Japanese Yen", "symbol": "\u00a5", "decimals": 0},
    "CHF": {"name": "Swiss Franc", "symbol": "CHF", "decimals": 2},
    "CNY": {"name": "Chinese Yuan", "symbol": "\u00a5", "decimals": 2},
    "INR": {"name": "Indian Rupee", "symbol": "\u20b9", "decimals": 2},
    "BRL": {"name": "Brazilian Real", "symbol": "R$", "decimals": 2},
    "MXN": {"name": "Mexican Peso", "symbol": "MX$", "decimals": 2},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$", "decimals": 2},
    "HKD": {"name": "Hong Kong Dollar", "symbol": "HK$", "decimals": 2},
    "KRW": {"name": "South Korean Won", "symbol": "\u20a9", "decimals": 0},
    "SEK": {"name": "Swedish Krona", "symbol": "kr", "decimals": 2},
    "NOK": {"name": "Norwegian Krone", "symbol": "kr", "decimals": 2},
    "DKK": {"name": "Danish Krone", "symbol": "kr", "decimals": 2},
    "NZD": {"name": "New Zealand Dollar", "symbol": "NZ$", "decimals": 2},
    "ZAR": {"name": "South African Rand", "symbol": "R", "decimals": 2},
    "PLN": {"name": "Polish Zloty", "symbol": "z\u0142", "decimals": 2},
}


def get_supported_currencies() -> list[dict]:
    """Get a list of all supported currencies with metadata.

    Returns:
        A list of dicts, each containing ``code``, ``name``, ``symbol``,
        ``decimals``, and ``rate`` (exchange rate relative to USD).
    """
    currencies = []
    for code, rate in EXCHANGE_RATES.items():
        info = CURRENCY_INFO.get(code, {})
        currencies.append({
            "code": code,
            "name": info.get("name", code),
            "symbol": info.get("symbol", code),
            "decimals": info.get("decimals", 2),
            "rate": rate,
        })
    return currencies


def convert_price(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
) -> dict:
    """Convert a price between two currencies.

    Conversion is performed via USD as the intermediary base currency:
    ``amount / from_rate * to_rate``.

    Args:
        amount: The monetary amount to convert.
        from_currency: The source currency code (e.g. ``"USD"``).
        to_currency: The target currency code (e.g. ``"EUR"``).

    Returns:
        A dict with ``converted_amount`` (Decimal) and ``rate`` (float)
        representing the direct conversion rate.

    Raises:
        ValueError: If either currency code is not supported.
    """
    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code not in EXCHANGE_RATES:
        raise ValueError(f"Unsupported currency: {from_code}")
    if to_code not in EXCHANGE_RATES:
        raise ValueError(f"Unsupported currency: {to_code}")

    if from_code == to_code:
        return {
            "converted_amount": amount,
            "rate": 1.0,
        }

    from_rate = Decimal(str(EXCHANGE_RATES[from_code]))
    to_rate = Decimal(str(EXCHANGE_RATES[to_code]))

    # Convert: amount in from_currency -> USD -> to_currency
    usd_amount = amount / from_rate
    converted = usd_amount * to_rate

    # Determine decimal places for target currency
    decimals = CURRENCY_INFO.get(to_code, {}).get("decimals", 2)
    quantize_str = "0." + "0" * decimals if decimals > 0 else "1"
    converted = converted.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)

    direct_rate = float(to_rate / from_rate)

    return {
        "converted_amount": converted,
        "rate": round(direct_rate, 6),
    }


async def get_store_currency(
    db: AsyncSession,
    store_id: uuid.UUID,
) -> str:
    """Get the configured currency for a store.

    Returns the store's currency setting, defaulting to ``"USD"`` if the
    store doesn't have a ``currency`` field or it is not set.

    Args:
        db: Async database session.
        store_id: The store's UUID.

    Returns:
        The currency code string (e.g. ``"USD"``).
    """
    result = await db.execute(select(Store).where(Store.id == store_id))
    store = result.scalar_one_or_none()

    if store is None:
        raise ValueError("Store not found")

    return getattr(store, "default_currency", "USD") or "USD"
