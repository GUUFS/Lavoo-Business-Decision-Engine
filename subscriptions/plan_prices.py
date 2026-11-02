"""
One place to get Lavoo's plan prices. Stripe is the source of truth: each
price lives in Stripe, and its Price ID is in an environment variable.
Every page and every backend check reads prices through here, so changing
a price in Stripe updates everything.

Env var names (one per plan, billing period and currency):
  Pro:      STRIPE_PRO_MONTHLY_PRICE_ID_USD, STRIPE_PRO_QUARTERLY_PRICE_ID_NGN, ...
  Premium:  STRIPE_PREMIUM_MONTHLY_PRICE_ID_USD, ...
  For Pro, the older names (STRIPE_MONTHLY_PRICE_ID_USD, ...) still work.
"""
import logging
import os
import time
from decimal import Decimal
from typing import Optional

import stripe

logger = logging.getLogger(__name__)

TIERS = ("pro", "premium")
PERIODS = ("monthly", "quarterly", "yearly")
CURRENCIES = ("USD", "GBP", "NGN")
DEFAULT_TIER = "pro"

# How close a paid amount must be to a price to count as that price
# (covers small rounding differences).
MATCH_TOLERANCE = Decimal("0.50")

# Prices are saved for 10 minutes so we don't ask Stripe on every request.
_CACHE_SECONDS = 10 * 60
_cache: dict = {}
_cache_at: float = 0.0


def normalise_tier(tier: Optional[str]) -> str:
    """Turns whatever the request sent into 'pro' or 'premium'."""
    t = (tier or "").strip().lower()
    return t if t in TIERS else DEFAULT_TIER


def env_keys(tier: str, period: str, currency: str) -> list[str]:
    """The env var names to try for this price, in order."""
    tier, period, currency = normalise_tier(tier), period.lower(), currency.upper()
    keys = [f"STRIPE_{tier.upper()}_{period.upper()}_PRICE_ID_{currency}"]
    # Pro was the only plan before, so its old names still count.
    if tier == "pro":
        keys += [f"STRIPE_{period.upper()}_PRICE_ID_{currency}", f"STRIPE_{period.upper()}_PRICE_ID"]
    return keys


def get_price_id(tier: str, period: str, currency: str) -> str:
    """The Stripe Price ID for this plan, or "" if it isn't set up."""
    # Try each env var name in turn and use the first one that is set.
    for key in env_keys(tier, period, currency):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def get_plan_prices(force_refresh: bool = False) -> dict:
    """All prices from Stripe: {tier: {currency: {period: amount or None}}}.
    Amounts are in normal units (naira, dollars, pounds), not kobo/cents."""
    global _cache, _cache_at

    # 1. Use the saved copy if it's recent enough.
    if not force_refresh and _cache and time.time() - _cache_at < _CACHE_SECONDS:
        return _cache

    api_key = os.getenv("STRIPE_SECRET_KEY")
    result: dict = {t: {c: {p: None for p in PERIODS} for c in CURRENCIES} for t in TIERS}
    if not api_key:
        logger.error("[plan_prices] STRIPE_SECRET_KEY not set; no prices available")
        return result

    # 2. Ask Stripe for each price that has a Price ID set.
    for tier in TIERS:
        for currency in CURRENCIES:
            for period in PERIODS:
                price_id = get_price_id(tier, period, currency)
                if not price_id:
                    continue
                try:
                    price = stripe.Price.retrieve(price_id, api_key=api_key)
                    unit_amount = getattr(price, "unit_amount", None)
                    if unit_amount is not None:
                        result[tier][currency][period] = unit_amount / 100
                except Exception as e:
                    logger.error(f"[plan_prices] {tier}/{period}/{currency} ({price_id}): {e}")

    # 3. Save the copy, but only if Stripe gave us at least one price.
    if any(v for t in result.values() for c in t.values() for v in c.values()):
        _cache, _cache_at = result, time.time()
    return result


def get_plan_price(tier: str, period: str, currency: str) -> Optional[Decimal]:
    """The price of one plan, or None if it isn't set up in Stripe."""
    amount = get_plan_prices().get(normalise_tier(tier), {}).get(currency.upper(), {}).get(period.lower())
    return Decimal(str(amount)) if amount else None


def resolve_tier(amount, currency: str, period: Optional[str] = None) -> Optional[str]:
    """Works out if a payment was for Pro or Premium from the amount paid.
    Checks the given billing period first, then any period. Returns None
    if the amount doesn't match any current price."""
    try:
        amount = Decimal(str(amount))
    except Exception:
        return None
    prices = get_plan_prices()
    currency = (currency or "USD").upper()

    # 1. Best match: same billing period.
    periods_to_try = [period.lower()] if period and period.lower() in PERIODS else []
    # 2. Otherwise: any billing period.
    periods_to_try += [p for p in PERIODS if p not in periods_to_try]

    for p in periods_to_try:
        for tier in TIERS:
            price = prices.get(tier, {}).get(currency, {}).get(p)
            if price and abs(amount - Decimal(str(price))) <= MATCH_TOLERANCE:
                return tier
    return None
