"""
Cards and automatic renewal only with the customer's say-so
(subscriptions/card_consent.py, api/main.py renewals), and cross-border
payouts only once the payment's money is available
(CommissionService._payment_money_ready).

Stripe and Flutterwave are never called: every outside call is replaced.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from database.pg_models import Commission, Subscriptions, User
from subscriptions import card_consent
from subscriptions.commission_service import CommissionService


def _user(db, email, **fields):
    """A saved user."""
    user = User(name="Card Test", email=email, password="x", confirm_password="x", **fields)
    db.add(user)
    db.flush()
    return user


_CARD = SimpleNamespace(card=SimpleNamespace(last4="4242", brand="visa", exp_month=12, exp_year=2030))


# ── The customer's choice ───────────────────────────────────────────────────

def test_ticking_save_card_keeps_it_and_turns_renewal_on(db):
    user = _user(db, "tick@card.test")
    card_consent.remember_card_choice(user, True, stripe_payment_method=_CARD, stripe_payment_method_id="pm_1")
    assert user.auto_renew and user.stripe_payment_method_id == "pm_1" and user.card_last4 == "4242"


def test_not_ticking_forgets_any_old_card_and_turns_renewal_off(db):
    user = _user(db, "untick@card.test", auto_renew=True, stripe_payment_method_id="pm_old",
                 flutterwave_card_token="flw-old", card_last4="1111")
    card_consent.remember_card_choice(user, False, stripe_payment_method=_CARD, stripe_payment_method_id="pm_new")
    assert not user.auto_renew
    assert user.stripe_payment_method_id is None and user.flutterwave_card_token is None and user.card_last4 is None


def test_a_flutterwave_card_is_kept_only_when_ticked(db):
    user = _user(db, "flw@card.test")
    card_consent.remember_card_choice(user, True, flutterwave_card={"token": "flw-tok", "last_4digits": "5678", "type": "MASTERCARD"})
    assert user.auto_renew and user.flutterwave_card_token == "flw-tok" and user.card_brand == "Mastercard"


# ── Renewals ────────────────────────────────────────────────────────────────

def test_no_renewal_charge_without_consent(db, monkeypatch):
    """Both renewal paths refuse a user who didn't agree, before any charge."""
    from api import main
    from database import pg_connections
    user = _user(db, "noconsent@card.test", stripe_customer_id="cus_1", stripe_payment_method_id="pm_1",
                 flutterwave_card_token="flw-1", auto_renew=False)

    class Session:
        """The test's session, usable as `with SessionLocal() as db`."""
        def __enter__(self):
            return db

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(pg_connections, "SessionLocal", Session)
    monkeypatch.setenv("NEXT_PUBLIC_FLUTTERWAVE_SECRET_KEY", "x")
    with patch("stripe.Subscription.create") as stripe_charge, patch("requests.post") as flw_charge:
        assert main._attempt_stripe_renewal(user.id, "monthly", "pro", "USD") is False
        assert main._attempt_flutterwave_renewal(user.id, "monthly", 1.0, "USD", "pro") is False
    stripe_charge.assert_not_called()
    flw_charge.assert_not_called()


def test_no_flutterwave_charge_at_an_old_price(db, monkeypatch):
    """Consent given, but today's price can't be found: nothing is charged
    (before, it charged the last amount paid, e.g. an old $1 price)."""
    from api import main
    from database import pg_connections
    user = _user(db, "oldprice@card.test", flutterwave_card_token="flw-1", auto_renew=True)

    class Session:
        """The test's session, usable as `with SessionLocal() as db`."""
        def __enter__(self):
            return db

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(pg_connections, "SessionLocal", Session)
    monkeypatch.setenv("NEXT_PUBLIC_FLUTTERWAVE_SECRET_KEY", "x")
    with patch("subscriptions.plan_prices.get_plan_price", return_value=None), patch("requests.post") as flw_charge:
        assert main._attempt_flutterwave_renewal(user.id, "monthly", 1.0, "USD", "pro") is False
    flw_charge.assert_not_called()


def test_the_sweep_stops_stripe_renewals_and_forgets_unconsented_cards(db, monkeypatch):
    stopped = []
    monkeypatch.setattr(card_consent, "stop_stripe_renewals", lambda u: stopped.append(u.id) or 1)
    old = _user(db, "legacy@card.test", stripe_customer_id="cus_old", stripe_payment_method_id="pm_old")
    agreed = _user(db, "agreed@card.test", stripe_customer_id="cus_ok", stripe_payment_method_id="pm_ok", auto_renew=True)
    result = card_consent.sweep_unconsented(db)
    assert old.id in stopped and agreed.id not in stopped
    assert old.stripe_payment_method_id is None and old.renewals_stopped_at is not None
    assert agreed.stripe_payment_method_id == "pm_ok"
    assert result["stripe_subscriptions"] >= 1
    # Checked once: the next sweep leaves them alone.
    stopped.clear()
    card_consent.sweep_unconsented(db)
    assert old.id not in stopped


def test_the_sweep_tries_again_when_stripe_does_not_answer(db, monkeypatch):
    monkeypatch.setattr(card_consent, "stop_stripe_renewals", lambda u: None)
    user = _user(db, "retry@card.test", stripe_customer_id="cus_r")
    card_consent.sweep_unconsented(db)
    assert user.renewals_stopped_at is None


# ── Cross-border payouts wait for the payment's money ───────────────────────

def _commission(db, provider, created_at):
    """A referrer's commission on one payment from `provider`."""
    referrer = _user(db, f"ref-{provider}-{created_at.timestamp()}@card.test")
    payment = Subscriptions(user_id=referrer.id, transaction_id=f"tx-{provider}-{created_at.timestamp()}",
                            tx_ref=f"ref-{provider}-{created_at.timestamp()}", amount=Decimal("9.00"), currency="USD",
                            status="completed", payment_provider=provider, start_date=created_at,
                            end_date=created_at + timedelta(days=30), created_at=created_at)
    db.add(payment)
    db.flush()
    commission = Commission(user_id=referrer.id, subscription_id=payment.id, amount=Decimal("2.25"),
                            currency="USD", status="pending")
    db.add(commission)
    db.flush()
    return commission


def test_a_stripe_payment_still_incoming_holds_a_naira_payout(db):
    commission = _commission(db, "Stripe", datetime.now(UTC))
    tx = db.get(Subscriptions, commission.subscription_id).transaction_id
    with patch("subscriptions.stripe_revenue.stripe_payment_status",
               return_value={tx: {"status": "pending", "available_on": datetime.now(UTC) + timedelta(days=3),
                         "currency": "USD", "net": Decimal("8.40"), "fee": Decimal("0.60")}}):
        held = CommissionService._payment_money_ready(commission, db, "flutterwave")
    assert held and "still incoming" in held


def test_an_available_stripe_payment_is_paid_and_same_provider_is_not_held(db):
    commission = _commission(db, "Stripe", datetime.now(UTC) - timedelta(days=5))
    tx = db.get(Subscriptions, commission.subscription_id).transaction_id
    with patch("subscriptions.stripe_revenue.stripe_payment_status",
               return_value={tx: {"status": "available", "available_on": datetime.now(UTC) - timedelta(days=1),
                                  "currency": "USD", "net": Decimal("8.40"), "fee": Decimal("0.60")}}):
        assert CommissionService._payment_money_ready(commission, db, "flutterwave") is None
    # Paid out on Stripe too: not cross-border, no extra hold.
    assert CommissionService._payment_money_ready(commission, db, "stripe") is None


def test_a_flutterwave_payment_settles_before_a_stripe_payout(db, monkeypatch):
    monkeypatch.setenv("FLUTTERWAVE_SETTLEMENT_DAYS", "2")
    fresh = _commission(db, "Flutterwave", datetime.now(UTC) - timedelta(hours=5))
    settled = _commission(db, "Flutterwave", datetime.now(UTC) - timedelta(days=3))
    assert "settles about" in CommissionService._payment_money_ready(fresh, db, "stripe")
    assert CommissionService._payment_money_ready(settled, db, "stripe") is None
