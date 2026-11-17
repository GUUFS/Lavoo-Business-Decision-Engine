"""
One place to get Lavoo's plan prices. Stripe is the source of truth: each
price lives in Stripe, and its Price ID is in an environment variable.
Every page and every backend check reads prices through here, so changing
a price in Stripe updates everything.

There are two sets of prices (see subscriptions/founding.py for who pays which):
  founding: what everyone pays before the founding end date (31 Jan 2027).
  standard: what everyone else pays.

Env var names (one per plan, billing period and currency):
  Founding: STRIPE_PRO_MONTHLY_PRICE_ID_USD, STRIPE_PREMIUM_QUARTERLY_PRICE_ID_NGN, ...
            (for Pro, the older names STRIPE_MONTHLY_PRICE_ID_USD, ... still work)
  Standard: STRIPE_PRO_MONTHLY_STANDARD_PRICE_ID_USD, STRIPE_PREMIUM_YEARLY_STANDARD_PRICE_ID_GBP, ...
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
PRICE_TYPES = ("founding", "standard")
DEFAULT_TIER = "pro"
FOUNDING = "founding"
STANDARD = "standard"

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


def normalise_price_type(price_type: Optional[str]) -> str:
    """Turns whatever was passed into 'founding' or 'standard'."""
    return STANDARD if (price_type or "").strip().lower() == STANDARD else FOUNDING


def env_keys(tier: str, period: str, currency: str, price_type: str = FOUNDING) -> list[str]:
    """The env var names to try for this price, in order."""
    tier, period, currency = normalise_tier(tier), period.lower(), currency.upper()
    if normalise_price_type(price_type) == STANDARD:
        return [f"STRIPE_{tier.upper()}_{period.upper()}_STANDARD_PRICE_ID_{currency}"]
    keys = [f"STRIPE_{tier.upper()}_{period.upper()}_PRICE_ID_{currency}"]
    # Pro was the only plan before, so its old names still count.
    if tier == "pro":
        keys += [f"STRIPE_{period.upper()}_PRICE_ID_{currency}", f"STRIPE_{period.upper()}_PRICE_ID"]
    return keys


def get_price_id(tier: str, period: str, currency: str, price_type: str = FOUNDING) -> str:
    """The Stripe Price ID for this plan, or "" if it isn't set up."""
    # Try each env var name in turn and use the first one that is set.
    for key in env_keys(tier, period, currency, price_type):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def identify_price_id(price_id: Optional[str]) -> Optional[dict]:
    """Works out which plan a Stripe Price ID belongs to, from the env vars.
    Returns {tier, period, currency, price_type}, or None if it's unknown."""
    if not price_id:
        return None
    for price_type in PRICE_TYPES:
        for tier in TIERS:
            for currency in CURRENCIES:
                for period in PERIODS:
                    if get_price_id(tier, period, currency, price_type) == price_id:
                        return {"tier": tier, "period": period, "currency": currency, "price_type": price_type}
    return None


def get_all_plan_prices(force_refresh: bool = False) -> dict:
    """Both price sets from Stripe:
    {price_type: {tier: {currency: {period: amount or None}}}}.
    Amounts are in normal units (naira, dollars, pounds), not kobo/cents."""
    global _cache, _cache_at

    # 1. Use the saved copy if it's recent enough.
    if not force_refresh and _cache and time.time() - _cache_at < _CACHE_SECONDS:
        return _cache

    result: dict = {
        pt: {t: {c: {p: None for p in PERIODS} for c in CURRENCIES} for t in TIERS}
        for pt in PRICE_TYPES
    }
    api_key = os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        logger.error("[plan_prices] STRIPE_SECRET_KEY not set; no prices available")
        return result

    # 2. Ask Stripe for each price that has a Price ID set.
    for price_type in PRICE_TYPES:
        for tier in TIERS:
            for currency in CURRENCIES:
                for period in PERIODS:
                    price_id = get_price_id(tier, period, currency, price_type)
                    if not price_id:
                        continue
                    try:
                        price = stripe.Price.retrieve(price_id, api_key=api_key)
                        unit_amount = getattr(price, "unit_amount", None)
                        if unit_amount is not None:
                            result[price_type][tier][currency][period] = unit_amount / 100
                    except Exception as e:
                        logger.error(f"[plan_prices] {price_type}/{tier}/{period}/{currency} ({price_id}): {e}")

    # 3. Save the copy, but only if Stripe gave us at least one price.
    if any(v for pt in result.values() for t in pt.values() for c in t.values() for v in c.values()):
        _cache, _cache_at = result, time.time()
    return result


def get_plan_prices(force_refresh: bool = False, price_type: str = FOUNDING) -> dict:
    """One price set from Stripe: {tier: {currency: {period: amount or None}}}."""
    return get_all_plan_prices(force_refresh)[normalise_price_type(price_type)]


def get_plan_price(tier: str, period: str, currency: str, price_type: str = FOUNDING) -> Optional[Decimal]:
    """The price of one plan, or None if it isn't set up in Stripe."""
    amount = (
        get_plan_prices(price_type=price_type)
        .get(normalise_tier(tier), {}).get(currency.upper(), {}).get(period.lower())
    )
    return Decimal(str(amount)) if amount else None


def resolve_tier(amount, currency: str, period: Optional[str] = None) -> Optional[str]:
    """Works out if a payment was for Pro or Premium from the amount paid.
    Only for old payment rows that were saved before the plan was recorded
    (Subscriptions.plan_tier); new rows store the plan, so use that instead.
    Checks founding prices before standard ones (old rows predate standard
    prices), and the given billing period before any other. Returns None if
    the amount doesn't match any current price."""
    try:
        amount = Decimal(str(amount))
    except Exception:
        return None
    all_prices = get_all_plan_prices()
    currency = (currency or "USD").upper()

    # 1. Best match: same billing period.
    periods_to_try = [period.lower()] if period and period.lower() in PERIODS else []
    # 2. Otherwise: any billing period.
    periods_to_try += [p for p in PERIODS if p not in periods_to_try]

    for price_type in PRICE_TYPES:
        for p in periods_to_try:
            for tier in TIERS:
                price = all_prices[price_type].get(tier, {}).get(currency, {}).get(p)
                if price and abs(amount - Decimal(str(price))) <= MATCH_TOLERANCE:
                    return tier
    return None
