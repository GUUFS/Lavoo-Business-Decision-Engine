"""
Charge a beta user who saved a Stripe card during the beta but was never
billed. Used by the admin "charge beta users" action
(api/routes/admin/admin.py) and the launch billing script
(cron/subscriptions/process_beta_billing.py), so both charge the same way:

  - the plan and currency the user picked when saving their card
    (User.preferred_plan_tier / preferred_currency / subscription_plan);
  - founding or standard price by the founding rules (subscriptions/founding.py);
  - the payment recorded with the amount Stripe actually charged.
"""
import logging
import os

import stripe

from database.pg_connections import SessionLocal
from database.pg_models import User

logger = logging.getLogger(__name__)

# Same mapping the website uses to pick a currency from the visitor's country.
_COUNTRY_CURRENCY = {"NG": "NGN", "GB": "GBP"}


def beta_currency(user: User) -> str:
    """The currency to charge a beta user in: what they picked when saving
    their card, or for older beta users who saved a card before that was
    recorded, the country their card was issued in (Nigeria: NGN, UK: GBP,
    anywhere else: USD)."""
    if getattr(user, "preferred_currency", None):
        return user.preferred_currency.upper()
    try:
        pm = stripe.PaymentMethod.retrieve(user.stripe_payment_method_id, api_key=os.getenv("STRIPE_SECRET_KEY"))
        country = (getattr(getattr(pm, "card", None), "country", None) or "").upper()
        return _COUNTRY_CURRENCY.get(country, "USD")
    except Exception as e:
        logger.warning(f"[beta-charge] couldn't read card country for user {user.id}: {e}; using USD")
        return "USD"


def charge_beta_user(user_id: int) -> bool:
    """Create and charge a Stripe subscription for one beta user, off-session,
    with the card they saved. Returns True if the subscription is active and
    recorded. Never raises."""
    from subscriptions import founding
    from subscriptions.stripe import _create_active_subscription_record, get_amount_from_stripe_price, get_stripe_price_id

    api_key = os.getenv("STRIPE_SECRET_KEY")
    # Some shared Stripe helpers use the global key (the cron script doesn't
    # load the modules that set it at import).
    stripe.api_key = api_key
    with SessionLocal() as db:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            # Premium-forever accounts are never charged (subscriptions/lifetime_premium.py).
            from subscriptions.lifetime_premium import lifetime_premium_active
            if lifetime_premium_active(user):
                logger.info("[beta-charge] user %s is Premium forever; not charged", user_id)
                return False
            if not user.stripe_customer_id or not user.stripe_payment_method_id:
                logger.warning("[beta-charge] user %s has no saved Stripe card; skipped", user_id)
                return False

            plan_type = user.subscription_plan or "monthly"
            plan_tier = getattr(user, "preferred_plan_tier", None) or "pro"
            currency = beta_currency(user)
            price_type = founding.price_type_for(db, user, plan_type)
            price_id = get_stripe_price_id(plan_type, currency, plan_tier, price_type)
            if not price_id:
                logger.error(
                    "[beta-charge] no %s price ID for %s/%s/%s (user %s); skipped",
                    price_type, plan_tier, plan_type, currency, user_id,
                )
                return False

            # Attach payment method to customer (idempotent if already attached)
            try:
                stripe.PaymentMethod.attach(user.stripe_payment_method_id, customer=user.stripe_customer_id, api_key=api_key)
            except stripe.error.InvalidRequestError:
                pass  # already attached

            sub = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{"price": price_id}],
                default_payment_method=user.stripe_payment_method_id,
                expand=["latest_invoice.payment_intent"],
                metadata={
                    "user_id": str(user_id), "plan_type": plan_type, "plan_tier": plan_tier,
                    "price_type": price_type, "currency": currency, "source": "beta_charge",
                },
                api_key=api_key,
            )

            status = sub.get("status")
            if status not in ("active", "trialing"):
                # e.g. 'incomplete': the bank wants the cardholder to approve
                # the payment, which can't happen off-session. They'll need to
                # pay from the upgrade page.
                logger.warning("[beta-charge] Stripe sub status=%s for user %s; not activated", status, user_id)
                return False

            amount = get_amount_from_stripe_price(price_id)
            _create_active_subscription_record(db, user, sub, plan_type, amount, tx_ref_prefix="BETA-CHARGE")
            db.commit()
            logger.info(
                "[beta-charge] ✅ charged user %s: %s %s %s (%s)",
                user_id, plan_tier, plan_type, currency, price_type,
            )

            try:
                from emailing.email_service import email_service
                end = user.subscription_expires_at
                email_service.send_payment_success_email(
                    user.email, user.name, float(amount), plan_type,
                    end.strftime("%B %d, %Y") if end else "",
                )
            except Exception as e:
                logger.warning("[beta-charge] payment email failed for user %s: %s", user_id, e)
            return True
        except Exception as exc:
            logger.error("[beta-charge] failed for user %s: %s", user_id, exc, exc_info=True)
            db.rollback()
            return False
