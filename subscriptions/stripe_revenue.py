"""
Stripe revenue counted when the money is AVAILABLE, not when it is charged.

WHY
  Stripe holds new payments for a few days ("Incoming") before the money
  is "Available" to pay out. The admin Revenue page used to count a Stripe
  payment the moment it was recorded, so the monthly and subscription
  revenue ran ahead of the Stripe available balance. Now a Stripe payment
  counts:
    - only once Stripe marks its money available,
    - in the month it became available,
    - at what Lavoo actually receives (the amount minus Stripe's fee),
      in the currency it landed in.
  Money still incoming is reported separately so nothing is hidden.
  How payments are RECORDED (the subscriptions table) does not change; this
  only changes how the Revenue page adds them up.

HOW (stripe_payment_status)
  1. Ask Stripe for its balance transactions (each payment's net amount,
     fee, status pending/available and the available_on date), with the
     charge attached so we know its payment intent.
  2. Ask Stripe which invoice each payment intent paid (InvoicePayment),
     because a first payment is stored in our table under the Stripe
     subscription id and a renewal under its payment intent or invoice id.
  3. Match each Stripe row in our table to its balance transaction by any
     of those ids.
  Results are cached for CACHE_SECONDS so the page doesn't call Stripe on
  every load.

  A row Stripe has no match for (e.g. created before this Stripe account,
  or a test) counts at its recorded amount once it is UNMATCHED_AFTER_DAYS
  old (longer than Stripe's normal hold), and is incoming before that.
"""
import logging
import os
import threading
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import stripe

logger = logging.getLogger(__name__)

CACHE_SECONDS = 300          # reuse Stripe's answer for 5 minutes
UNMATCHED_AFTER_DAYS = 7     # an unmatched Stripe row counts once it is this old
_PAYMENT_TYPES = ("charge", "payment")

_cache: dict = {"at": 0.0, "data": None}
_cache_lock = threading.Lock()


def _plain(obj) -> dict:
    """A Stripe object as a plain dict."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    return obj.to_dict() if hasattr(obj, "to_dict") else {}


def _id(value) -> str | None:
    """An id from a Stripe field that may be an id or an expanded object."""
    if isinstance(value, dict):
        return value.get("id")
    return value or None


def _load_from_stripe() -> dict:
    """{stripe_id: {"status", "available_on", "net", "fee", "currency"}} for every
    Stripe payment, keyed by each id our table may store it under."""
    key = os.getenv("STRIPE_SECRET_KEY")
    by_payment_intent: dict[str, dict] = {}
    by_id: dict[str, dict] = {}

    # 1. Every payment's balance transaction (net, fee, pending/available, date).
    txns = stripe.BalanceTransaction.list(limit=100, expand=["data.source"], api_key=key)
    for bt in txns.auto_paging_iter():
        bt = _plain(bt)
        if bt.get("type") not in _PAYMENT_TYPES:
            continue
        info = {
            "status": bt.get("status"),
            "available_on": datetime.fromtimestamp(bt["available_on"], UTC) if bt.get("available_on") else None,
            "net": Decimal(bt.get("net") or 0) / 100,
            "fee": Decimal(bt.get("fee") or 0) / 100,
            "currency": (bt.get("currency") or "").upper(),
        }
        source = bt.get("source") if isinstance(bt.get("source"), dict) else {"id": bt.get("source")}
        charge_id, pi = source.get("id"), _id(source.get("payment_intent"))
        for stripe_id in (charge_id, pi):
            if stripe_id:
                by_id[stripe_id] = info
        if pi:
            by_payment_intent[pi] = info

    # 2. Which invoice (and subscription) each payment intent paid.
    payments = stripe.InvoicePayment.list(limit=100, expand=["data.invoice"], api_key=key)
    for row in payments.auto_paging_iter():
        row = _plain(row)
        pi = _id((row.get("payment") or {}).get("payment_intent"))
        info = by_payment_intent.get(pi)
        invoice = row.get("invoice") if isinstance(row.get("invoice"), dict) else {"id": row.get("invoice")}
        if not info or not invoice.get("id"):
            continue
        by_id[invoice["id"]] = info
        # A first payment is stored under the subscription id (renewals are not:
        # the subscription id belongs to the first payment's row).
        if invoice.get("billing_reason") == "subscription_create":
            details = (invoice.get("parent") or {}).get("subscription_details") or {}
            sub_id = _id(details.get("subscription") or invoice.get("subscription"))
            if sub_id:
                by_id[sub_id] = info
    return by_id


def stripe_payment_status() -> dict | None:
    """The cached Stripe payment map (see _load_from_stripe), or None if Stripe
    couldn't be reached (the caller then falls back to the age rule)."""
    # 1. Fresh enough: reuse it.
    with _cache_lock:
        if _cache["data"] is not None and time.time() - _cache["at"] < CACHE_SECONDS:
            return _cache["data"]
    # 2. Ask Stripe (outside the lock: it takes a second or two).
    if not os.getenv("STRIPE_SECRET_KEY"):
        return None
    try:
        data = _load_from_stripe()
    except Exception as e:
        logger.warning(f"[stripe-revenue] couldn't read Stripe balance transactions: {e}")
        return None
    with _cache_lock:
        _cache.update(at=time.time(), data=data)
    return data


def when_counted(row, status_map: dict | None, now: datetime) -> dict:
    """When one Stripe payment row counts as revenue, and for how much.

    Returns {"counted": bool, "month_of": datetime | None, "amount": Decimal,
             "currency": str, "matched": bool}.
      - matched + available: counts in the month it became available, at net.
      - matched + pending:   not counted yet (incoming), at net.
      - unmatched:           counts at the recorded amount once older than
                             UNMATCHED_AFTER_DAYS, in the month of that date.
    """
    # 1. Stripe knows this payment.
    info = (status_map or {}).get(row.transaction_id)
    if info:
        available = info["status"] == "available" and (info["available_on"] is None or info["available_on"] <= now)
        return {"counted": available, "month_of": info["available_on"], "amount": info["net"],
                "currency": info["currency"] or row.currency, "matched": True}
    # 2. No match: use the age rule at the recorded (gross) amount.
    created = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=UTC)
    ready_on = created + timedelta(days=UNMATCHED_AFTER_DAYS)
    return {"counted": ready_on <= now, "month_of": ready_on, "amount": Decimal(str(row.amount)),
            "currency": row.currency, "matched": False}
