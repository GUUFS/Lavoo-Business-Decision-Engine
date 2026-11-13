"""
Payments and refunds for the admin Refunds page.

WHAT THE PAGE DOES
  1. Lists recent Stripe payments (recent_payments).
  2. Shows everything about one payment (payment_details): who paid, the
     card, the Stripe fee, when the money becomes available, which plan it
     was for, and WHY the card was charged (first payment, automatic
     renewal, beta charge...).
  3. Refunds a payment (refund_payment). The admin chose this policy:
       a) the money goes back to the card in full (Stripe refund);
       b) the Stripe subscription is cancelled, so it never charges again;
       c) access ends now: our payment record is marked refunded and the
          user's plan is worked out again (Free unless another payment
          still covers them, or they are a partner / Premium forever);
       d) the referrer's commission is cancelled if not yet paid out; if it
          was paid out, a clawback is recorded and the admin is alerted
          (CommissionService.reverse_commission_for_subscription);
       e) the refund is recorded in admin_refunds with every step taken.
     Stripe then sends a charge.refunded webhook; that runs step (c)-(d)
     again, which changes nothing the second time.

FINDING OUR RECORD FOR A STRIPE PAYMENT (find_our_payment_record)
  Our subscriptions table stores a payment under one of three Stripe ids:
  the payment intent (renewals), the invoice, or the Stripe subscription
  (first payments). In this Stripe API version a payment no longer says
  which invoice it paid, so the invoice is looked up with InvoicePayment.
"""
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal

import stripe
from sqlalchemy.orm import Session

from database.pg_models import AdminRefund, Commission, Subscriptions, User

logger = logging.getLogger(__name__)

# The reasons Stripe accepts for a refund.
STRIPE_REFUND_REASONS = ("requested_by_customer", "duplicate", "fraudulent")

# Why a card was charged, from the invoice's billing_reason (Stripe's words -> ours).
_BILLING_REASONS = {
    "subscription_create": "First payment, when they subscribed.",
    "subscription_cycle": "Automatic renewal: Stripe charged the saved card at the start of a new billing period.",
    "subscription_update": "Plan change: charged the difference when the plan changed.",
    "subscription_threshold": "Usage threshold reached.",
    "manual": "An invoice created by hand in Stripe.",
}

# Why a Stripe subscription was created, from the "source" our code puts in its metadata.
_SUBSCRIPTION_SOURCES = {
    "auto_renewal": ("Lavoo's daily expiry job: their plan had ended, so it started a new subscription and "
                     "charged the card they saved before (api/main.py, _attempt_stripe_renewal)."),
    "beta_charge": ("The beta billing: an admin pressed 'Charge beta users', which charged the card they "
                    "saved during the beta (subscriptions/beta_billing.py)."),
    "save_card_launch": "Charged at launch with the card they saved during the beta (subscriptions/stripe.py).",
}


def _key() -> str | None:
    """The Stripe secret key."""
    return os.getenv("STRIPE_SECRET_KEY")


def _plain(obj) -> dict:
    """A Stripe object as a plain dict (Stripe objects here have no .get())."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    return obj.to_dict() if hasattr(obj, "to_dict") else {}


def _money(amount_in_cents: int | None, currency: str | None) -> dict:
    """{"amount": 7.0, "currency": "GBP"} from Stripe's smallest unit (pence/cents)."""
    return {"amount": round((amount_in_cents or 0) / 100, 2), "currency": (currency or "").upper()}


def _when(timestamp: int | None) -> str | None:
    """A Stripe timestamp as an ISO date-time (UTC)."""
    return datetime.fromtimestamp(timestamp, UTC).isoformat() if timestamp else None


# =========================================================================
# Finding the invoice, the Stripe subscription and our record
# =========================================================================

def invoice_for_payment_intent(payment_intent_id: str | None) -> dict:
    """The invoice a payment paid (empty dict if it wasn't an invoice payment)."""
    # 1. No payment intent: nothing to look up.
    if not payment_intent_id:
        return {}
    # 2. Ask Stripe which invoice this payment paid.
    try:
        found = stripe.InvoicePayment.list(payment={"type": "payment_intent", "payment_intent": payment_intent_id},
                                           limit=1, expand=["data.invoice"], api_key=_key())
        rows = _plain(found).get("data") or []
        invoice = rows[0].get("invoice") if rows else None
        return invoice if isinstance(invoice, dict) else {}
    except Exception as e:
        logger.warning(f"[refunds] couldn't find the invoice for {payment_intent_id}: {e}")
        return {}


def subscription_id_of_invoice(invoice: dict) -> str | None:
    """The Stripe subscription an invoice belongs to (new and old API shapes)."""
    # 1. New API: invoice.parent.subscription_details.subscription
    details = ((invoice.get("parent") or {}).get("subscription_details") or {})
    sub = details.get("subscription") or invoice.get("subscription")
    # 2. It may be an id or an expanded object.
    return sub.get("id") if isinstance(sub, dict) else sub


def find_our_payment_record(db: Session, payment_intent_id: str | None, invoice: dict | None = None,
                            charge_id: str | None = None) -> Subscriptions | None:
    """Our subscriptions row for a Stripe payment, trying each id it may be stored under."""
    invoice = invoice if invoice is not None else invoice_for_payment_intent(payment_intent_id)
    # 1. The ids, most specific first: payment intent, charge, invoice, then subscription.
    for stripe_id in (payment_intent_id, charge_id, invoice.get("id"), subscription_id_of_invoice(invoice)):
        if stripe_id:
            found = db.query(Subscriptions).filter(Subscriptions.transaction_id == stripe_id).first()
            if found:
                return found
    return None


def _why_charged(invoice: dict, stripe_subscription: dict) -> list[str]:
    """Plain sentences on why the card was charged."""
    reasons = []
    # 1. The invoice's reason (first payment, renewal, ...).
    billing_reason = invoice.get("billing_reason")
    if billing_reason:
        reasons.append(_BILLING_REASONS.get(billing_reason, f"Stripe billing reason: {billing_reason}."))
    elif not invoice:
        reasons.append("A one-off payment, not a subscription invoice.")
    # 2. Which part of Lavoo started that subscription.
    source = (stripe_subscription.get("metadata") or {}).get("source")
    if source:
        reasons.append(_SUBSCRIPTION_SOURCES.get(source, f"Subscription started by: {source}."))
    # 3. Saved card: the payment happened without the customer on the page.
    if stripe_subscription and billing_reason == "subscription_cycle":
        reasons.append("The card was saved when they first subscribed; Stripe keeps it to charge each renewal.")
    return reasons


# =========================================================================
# Listing and showing payments
# =========================================================================

def recent_payments(db: Session, limit: int = 25) -> list[dict]:
    """The latest Stripe payments, newest first, with our user where we know them."""
    # 1. Charges from Stripe, with their fee and payout dates.
    charges = _plain(stripe.Charge.list(limit=limit, expand=["data.balance_transaction"], api_key=_key())).get("data") or []
    # 2. Our users, matched by Stripe customer id (one query for all).
    customer_ids = {c.get("customer") for c in charges if isinstance(c.get("customer"), str)}
    users = {u.stripe_customer_id: u for u in db.query(User).filter(User.stripe_customer_id.in_(customer_ids)).all()} \
        if customer_ids else {}
    out = []
    for c in charges:
        user = users.get(c.get("customer"))
        card = ((c.get("payment_method_details") or {}).get("card") or {})
        balance = c.get("balance_transaction") if isinstance(c.get("balance_transaction"), dict) else {}
        # 3. One row per payment.
        out.append({
            "charge_id": c.get("id"),
            "created_at": _when(c.get("created")),
            **_money(c.get("amount"), c.get("currency")),
            "refunded_amount": _money(c.get("amount_refunded"), c.get("currency"))["amount"],
            "status": c.get("status"),
            "refunded": bool(c.get("refunded")),
            "description": c.get("description"),
            "card": f"{(card.get('brand') or '').title()} •••• {card.get('last4')}" if card.get("last4") else None,
            "payer_email": (c.get("billing_details") or {}).get("email") or c.get("receipt_email"),
            "available_on": _when(balance.get("available_on")),
            "user": {"id": user.id, "name": user.name, "email": user.email} if user else None,
        })
    return out


def payment_details(db: Session, charge_id: str) -> dict:
    """Everything about one payment: Stripe's side, why it was charged, and our records."""
    # 1. The payment, with its fee and payout date.
    charge = _plain(stripe.Charge.retrieve(charge_id, expand=["balance_transaction"], api_key=_key()))
    payment_intent_id = charge.get("payment_intent") if isinstance(charge.get("payment_intent"), str) else None
    balance = charge.get("balance_transaction") if isinstance(charge.get("balance_transaction"), dict) else {}
    card = ((charge.get("payment_method_details") or {}).get("card") or {})

    # 2. The invoice and Stripe subscription it paid for (if any).
    invoice = invoice_for_payment_intent(payment_intent_id)
    sub_id = subscription_id_of_invoice(invoice)
    stripe_sub = {}
    if sub_id:
        try:
            stripe_sub = _plain(stripe.Subscription.retrieve(sub_id, api_key=_key()))
        except Exception as e:
            logger.warning(f"[refunds] couldn't load subscription {sub_id}: {e}")

    # 3. Our side: the user, our payment record, commissions, earlier refunds.
    user = db.query(User).filter(User.stripe_customer_id == charge.get("customer")).first() \
        if charge.get("customer") else None
    record = find_our_payment_record(db, payment_intent_id, invoice, charge_id)
    if not user and record:
        user = db.get(User, record.user_id)
    commissions = db.query(Commission).filter(Commission.subscription_id == record.id).all() if record else []
    refunds = db.query(AdminRefund).filter(AdminRefund.stripe_charge_id == charge_id) \
        .order_by(AdminRefund.created_at.desc()).all()

    # 4. Put it together.
    return {
        "charge_id": charge.get("id"),
        "created_at": _when(charge.get("created")),
        **_money(charge.get("amount"), charge.get("currency")),
        "refunded_amount": _money(charge.get("amount_refunded"), charge.get("currency"))["amount"],
        "status": charge.get("status"),
        "refunded": bool(charge.get("refunded")),
        "description": charge.get("description"),
        "receipt_url": charge.get("receipt_url"),
        "payer": {"name": (charge.get("billing_details") or {}).get("name"),
                  "email": (charge.get("billing_details") or {}).get("email") or charge.get("receipt_email"),
                  "country": ((charge.get("billing_details") or {}).get("address") or {}).get("country")},
        "card": {"brand": card.get("brand"), "last4": card.get("last4"), "exp": f"{card.get('exp_month')}/{card.get('exp_year')}"
                 if card.get("exp_month") else None, "country": card.get("country"), "funding": card.get("funding")},
        "money": {
            "stripe_fee": _money(balance.get("fee"), balance.get("currency"))["amount"] if balance else None,
            "you_receive": _money(balance.get("net"), balance.get("currency"))["amount"] if balance else None,
            "available_on": _when(balance.get("available_on")),
        },
        "why_charged": _why_charged(invoice, stripe_sub),
        "invoice": {"id": invoice.get("id"), "number": invoice.get("number"), "billing_reason": invoice.get("billing_reason"),
                    "url": invoice.get("hosted_invoice_url")} if invoice else None,
        "stripe_subscription": {"id": stripe_sub.get("id"), "status": stripe_sub.get("status"),
                                "metadata": stripe_sub.get("metadata") or {},
                                "cancel_at_period_end": stripe_sub.get("cancel_at_period_end")} if stripe_sub else None,
        "user": {"id": user.id, "name": user.name, "email": user.email, "plan": user.subscription_plan,
                 "status": user.subscription_status,
                 "expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
                 "card_saved": bool(user.stripe_payment_method_id)} if user else None,
        "our_record": {"id": record.id, "plan": record.subscription_plan, "plan_tier": record.plan_tier,
                       "status": record.status, "subscription_status": record.subscription_status,
                       "start_date": record.start_date.isoformat() if record.start_date else None,
                       "end_date": record.end_date.isoformat() if record.end_date else None} if record else None,
        "commissions": [{"id": c.id, "referrer_id": c.user_id, "amount": float(c.amount), "currency": c.currency,
                         "status": c.status} for c in commissions],
        "refunds": [_refund_view(r) for r in refunds],
    }


def _refund_view(r: AdminRefund) -> dict:
    """One recorded refund for the page."""
    return {"id": r.id, "charge_id": r.stripe_charge_id, "amount": float(r.amount), "currency": r.currency,
            "reason": r.reason, "note": r.note, "steps": r.steps or [], "user_id": r.user_id,
            "refunded_by": r.refunded_by, "created_at": r.created_at.isoformat() if r.created_at else None}


def refund_history(db: Session, limit: int = 50) -> list[dict]:
    """Refunds admins made, newest first."""
    return [_refund_view(r) for r in db.query(AdminRefund).order_by(AdminRefund.created_at.desc()).limit(limit).all()]


# =========================================================================
# Refunding a payment
# =========================================================================

def refund_payment(db: Session, charge_id: str, admin_id: int | None, reason: str = "requested_by_customer",
                   note: str | None = None) -> dict:
    """Refund a payment in full, stop future charges, end access now, cancel
    or claw back the commission, and record it all. Returns the steps taken."""
    from subscriptions.commission_service import CommissionService

    if reason not in STRIPE_REFUND_REASONS:
        raise ValueError(f"reason must be one of {', '.join(STRIPE_REFUND_REASONS)}")
    steps = []

    # 1. The payment. Refuse one that is already fully refunded or didn't succeed.
    charge = _plain(stripe.Charge.retrieve(charge_id, api_key=_key()))
    if charge.get("status") != "succeeded":
        raise ValueError("Only a successful payment can be refunded.")
    to_refund = (charge.get("amount") or 0) - (charge.get("amount_refunded") or 0)
    if to_refund <= 0:
        raise ValueError("This payment has already been refunded in full.")
    payment_intent_id = charge.get("payment_intent") if isinstance(charge.get("payment_intent"), str) else None

    # 2. Give the money back (the idempotency key stops a double refund on a double click).
    refund = _plain(stripe.Refund.create(
        charge=charge_id, reason=reason, api_key=_key(),
        metadata={"refunded_by_admin": str(admin_id or ""), "note": (note or "")[:400]},
        idempotency_key=f"admin-refund-{charge_id}",
    ))
    money = _money(to_refund, charge.get("currency"))
    steps.append(f"Refunded {money['currency']} {money['amount']:.2f} to the card (Stripe refund {refund.get('id')}).")

    # 3. Stop future charges: cancel the Stripe subscription this payment was for.
    invoice = invoice_for_payment_intent(payment_intent_id)
    sub_id = subscription_id_of_invoice(invoice)
    cancelled = None
    if sub_id:
        try:
            current = _plain(stripe.Subscription.retrieve(sub_id, api_key=_key()))
            if current.get("status") not in ("canceled", "incomplete_expired"):
                stripe.Subscription.cancel(sub_id, api_key=_key())
                steps.append(f"Cancelled the Stripe subscription {sub_id}, so it won't charge again.")
            else:
                steps.append(f"The Stripe subscription {sub_id} was already cancelled.")
            cancelled = sub_id
        except Exception as e:
            steps.append(f"Couldn't cancel the Stripe subscription {sub_id}: {e}. Cancel it in Stripe by hand.")
    else:
        steps.append("This payment wasn't for a Stripe subscription, so there was nothing to cancel.")

    # 4. Our records: payment marked refunded, access recalculated, commission handled.
    record = find_our_payment_record(db, payment_intent_id, invoice, charge_id)
    user = db.get(User, record.user_id) if record else (
        db.query(User).filter(User.stripe_customer_id == charge.get("customer")).first() if charge.get("customer") else None)
    if record:
        commission = db.query(Commission).filter(Commission.subscription_id == record.id).first()
        status_before = commission.status if commission else None
        CommissionService.reverse_commission_for_subscription(record, "refund", db)
        steps.append(f"Marked our payment record #{record.id} as refunded.")
        if user:
            db.refresh(user)
            steps.append(f"{user.name}'s plan is now: {user.subscription_status}"
                         + (" (another payment, partner deal or Premium forever still covers them)."
                            if user.subscription_status == "active" else "."))
        if not commission:
            steps.append("No referral commission was earned on this payment.")
        elif status_before in ("pending", "approved"):
            steps.append(f"Cancelled the referrer's unpaid commission #{commission.id}.")
        elif status_before in ("paid", "auto_settled"):
            steps.append(f"The referrer's commission #{commission.id} was already paid out: a clawback is recorded "
                         "against their next earnings, and admins were alerted to recover it.")
        else:
            steps.append(f"The referrer's commission #{commission.id} was already {status_before}; left as it is.")
    else:
        steps.append("No matching payment record was found in our database, so nobody's plan was changed. "
                     "Check the user on the Users page.")

    # 5. Record the refund and save everything.
    db.add(AdminRefund(
        stripe_charge_id=charge_id, stripe_payment_intent_id=payment_intent_id, stripe_refund_id=refund.get("id"),
        amount=Decimal(str(money["amount"])), currency=money["currency"], user_id=user.id if user else None,
        subscription_record_id=record.id if record else None, stripe_subscription_cancelled=cancelled,
        reason=reason, note=(note or "").strip() or None, steps=steps, refunded_by=admin_id,
    ))
    db.commit()
    logger.info(f"[refunds] admin {admin_id} refunded {charge_id}: {steps}")
    return {"charge_id": charge_id, "refund_id": refund.get("id"), **money, "steps": steps}
