"""
End-to-end tests for referral payouts across payment providers, after the
new "6 paid months" commission rule (subscriptions/commission_service.py).

The real payment code runs against real Postgres. Only the outside world is
faked: Flutterwave's HTTP API, Stripe's API, live FX rates and platform
balances. Each test checks both WHETHER the referrer is paid (the
commission rule) and HOW (the right provider, currency and amount).

Flows covered:
  - Flutterwave charge with a subaccount split: the split percentage set up
    before the charge, and the "already settled" commission recorded after.
  - Stripe (USD) payment -> referrer paid in NGN through Flutterwave.
  - Flutterwave (NGN) payment -> referrer paid in GBP through Stripe Connect.
  - A payment outside the 6 paid months: no split, no commission, no transfer.
"""
import itertools
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from database.pg_models import Commission, Payout, PayoutAccount, Referral, Subscriptions, User
from subscriptions.commission_service import CommissionService
from subscriptions.flutterwave_split import get_split_config_for_referred_user

_ids = itertools.count(1)


# ── Test data helpers ───────────────────────────────────────────────────────

def make_user(db, status="Free", expires=None):
    """Create a user; `status`/`expires` describe their own subscription."""
    n = next(_ids)
    user = User(name=f"User {n}", email=f"xrail{n}@test.local", password="x", confirm_password="x",
                subscription_status=status, subscription_expires_at=expires)
    db.add(user)
    db.flush()
    return user


def add_payment(db, user_id, when, period="monthly", amount="100.00", currency="USD",
                provider="stripe", tier="pro", sub_status="active"):
    """Record one successful subscription payment."""
    n = next(_ids)
    sub = Subscriptions(
        user_id=user_id, subscription_plan=period, plan_tier=tier, transaction_id=f"xr-tx{n}",
        tx_ref=f"xr-ref{n}", amount=Decimal(amount), currency=currency, status="completed",
        subscription_status=sub_status, payment_provider=provider, created_at=when,
        start_date=when, end_date=when + timedelta(days=30),
    )
    db.add(sub)
    db.flush()
    return sub


def make_referrer(db, tier="pro"):
    """An actively subscribed Pro/Premium referrer (paid up for a year)."""
    now = datetime.now(UTC)
    referrer = make_user(db, status="active", expires=now + timedelta(days=365))
    add_payment(db, referrer.id, now - timedelta(days=3), tier=tier)
    return referrer


def link_referral(db, referrer):
    """Create a referred user linked to `referrer`; returns the referred user."""
    referred = make_user(db)
    db.add(Referral(referrer_id=referrer.id, referred_user_id=referred.id))
    db.flush()
    return referred


def give_flutterwave_bank(db, user, subaccount=True):
    """Referrer's verified Nigerian bank account (optionally with a split subaccount)."""
    db.add(PayoutAccount(
        user_id=user.id, payment_method="flutterwave", bank_name="Test Bank", bank_code="044",
        account_number="0123456789", account_name="Test Referrer", is_verified=True,
        flutterwave_subaccount_id="RS_TEST" if subaccount else None,
        subaccount_status="active" if subaccount else None,
    ))
    db.flush()


def give_stripe_connect(db, user):
    """Referrer's verified Stripe Connect account (UK, pays out in GBP)."""
    db.add(PayoutAccount(user_id=user.id, payment_method="stripe", stripe_account_id="acct_TEST",
                         stripe_account_status="active", is_verified=True))
    db.flush()


def six_paid_months(db, user_id, currency="USD", provider="stripe", amount="100.00"):
    """Six monthly payments ending a few days ago (the referrer's full 6 months)."""
    start = datetime.now(UTC) - timedelta(days=200)
    for i in range(6):
        add_payment(db, user_id, start + timedelta(days=30 * i), currency=currency,
                    provider=provider, amount=amount)


@pytest.fixture(autouse=True)
def quiet_side_effects():
    """Keep notifications, emails, admin alerts and plan chops out of the way;
    they aren't what these tests check and some call outside services."""
    with patch("subscriptions.commission_service.NotificationService.create_notification"), \
         patch.object(CommissionService, "_award_plan_signup_chops"), \
         patch.object(CommissionService, "_alert_admin", create=True):
        yield


def flutterwave_transfer_ok():
    """A fake requests.post response for an accepted Flutterwave transfer."""
    response = MagicMock(status_code=200, text='{"status":"success"}')
    response.json.return_value = {"status": "success", "data": {"id": 987654, "status": "NEW"}}
    return response


# ── Flutterwave subaccount split ────────────────────────────────────────────

@pytest.mark.parametrize("tier, lavoo_keeps", [("pro", 0.75), ("premium", 0.60)])
def test_flutterwave_split_gives_referrer_their_rate(db, tier, lavoo_keeps):
    referrer = make_referrer(db, tier=tier)
    give_flutterwave_bank(db, referrer)
    referred = link_referral(db, referrer)

    config = get_split_config_for_referred_user(referred.id, db, billing_period="monthly")
    assert config == {"subaccount_id": "RS_TEST", "main_account_charge_percentage": lavoo_keeps}


def test_flutterwave_split_stops_after_six_paid_months(db):
    referrer = make_referrer(db)
    give_flutterwave_bank(db, referrer)
    referred = link_referral(db, referrer)
    six_paid_months(db, referred.id, currency="NGN", provider="flutterwave")

    assert get_split_config_for_referred_user(referred.id, db, billing_period="monthly") is None


def test_flutterwave_split_charge_is_recorded_as_already_settled(db):
    """After a split charge the referrer already has their share, so the
    commission is history only: no transfer is attempted."""
    referrer = make_referrer(db)
    give_flutterwave_bank(db, referrer)
    referred = link_referral(db, referrer)
    sub = add_payment(db, referred.id, datetime.now(UTC), currency="NGN", provider="flutterwave",
                      amount="20000.00")

    with patch.object(CommissionService, "_attempt_immediate_payout") as payout:
        commission = CommissionService.calculate_commission(sub, db, already_settled=True)
    payout.assert_not_called()
    assert commission.status == "auto_settled"
    assert commission.amount == Decimal("5000.00") and commission.currency == "NGN"


# ── Stripe payment -> Flutterwave payout ────────────────────────────────────

def test_stripe_usd_payment_pays_nigerian_referrer_in_ngn(db):
    referrer = make_referrer(db)
    give_flutterwave_bank(db, referrer, subaccount=False)
    referred = link_referral(db, referrer)
    sub = add_payment(db, referred.id, datetime.now(UTC), currency="USD", amount="100.00")

    with patch("subscriptions.flutterwave_split.get_flutterwave_fx_rate", return_value=Decimal("1500")), \
         patch("subscriptions.payout_service.PayoutService.get_platform_flutterwave_available",
               return_value={"available": Decimal("10000000")}), \
         patch("subscriptions.payout_service.requests.post", return_value=flutterwave_transfer_ok()) as post:
        commission = CommissionService.calculate_commission(sub, db)

    assert commission.amount == Decimal("25.00") and commission.currency == "USD"
    assert commission.status == "auto_settled"
    payout = db.get(Payout, commission.payout_id)
    assert (payout.currency, payout.amount, payout.status) == ("NGN", Decimal("37500.00"), "processing")
    assert (payout.original_currency, payout.original_amount) == ("USD", Decimal("25.00"))
    assert post.call_args.kwargs["json"]["amount"] == 37500.0


# ── Flutterwave payment -> Stripe payout ────────────────────────────────────

def test_flutterwave_ngn_payment_pays_uk_referrer_in_gbp(db):
    referrer = make_referrer(db, tier="premium")
    give_stripe_connect(db, referrer)
    referred = link_referral(db, referrer)
    sub = add_payment(db, referred.id, datetime.now(UTC), currency="NGN", provider="flutterwave",
                      amount="20000.00")

    account = {"capabilities": {"transfers": "active"}, "default_currency": "gbp"}
    with patch("stripe.Account.retrieve", return_value=account), \
         patch("stripe.Transfer.list", return_value=MagicMock(data=[])), \
         patch("stripe.Transfer.create", return_value={"id": "tr_TEST"}) as transfer, \
         patch("subscriptions.flutterwave_split.get_flutterwave_fx_rate", return_value=Decimal("0.0005")), \
         patch("subscriptions.payout_service.PayoutService.get_platform_stripe_available", return_value=10_000_00):
        commission = CommissionService.calculate_commission(sub, db)

    assert commission.amount == Decimal("8000.00") and commission.currency == "NGN"  # 40%
    assert commission.status == "auto_settled"
    payout = db.get(Payout, commission.payout_id)
    assert (payout.currency, payout.amount, payout.status) == ("GBP", Decimal("4.00"), "completed")
    assert transfer.call_args.kwargs["amount"] == 400 and transfer.call_args.kwargs["currency"] == "gbp"


# ── Outside the 6 paid months: nothing is paid on any rail ─────────────────

def test_payment_after_six_paid_months_pays_nothing_on_any_rail(db):
    referrer = make_referrer(db)
    give_flutterwave_bank(db, referrer, subaccount=False)
    referred = link_referral(db, referrer)
    six_paid_months(db, referred.id)
    seventh = add_payment(db, referred.id, datetime.now(UTC))

    with patch("subscriptions.payout_service.requests.post") as post, \
         patch("stripe.Transfer.create") as transfer:
        assert CommissionService.calculate_commission(seventh, db) is None
    post.assert_not_called()
    transfer.assert_not_called()
    assert db.query(Commission).filter_by(subscription_id=seventh.id).count() == 0
