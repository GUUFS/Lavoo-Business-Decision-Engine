"""
Payout Tracker (subscriptions/payout_tracker.py): every try to pay a
commission is recorded with its real reason, and the Revenue page's health
check shows that reason instead of "never attempted".

Flutterwave and Stripe are faked: no network, no real money.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from database.pg_models import (
    Commission,
    CommissionPayoutAttempt,
    PayoutAccount,
    Subscriptions,
    User,
)
from subscriptions import payout_tracker
from subscriptions.commission_service import CommissionService
from subscriptions.payout_service import PayoutService

NOW = datetime.now(UTC)


@pytest.fixture
def fake_flutterwave(monkeypatch):
    """£1 = ₦1,950 and a Flutterwave NGN wallet of ₦1,695.63 (as on the Revenue page).
    Returns the settings so a test can change the wallet balance."""
    import subscriptions.flutterwave_split as flutterwave_split
    wallet = {"available": Decimal("1695.63"), "sent": []}
    monkeypatch.setattr(flutterwave_split, "get_flutterwave_fx_rate", lambda a, b: Decimal("1950"))
    monkeypatch.setattr(PayoutService, "get_platform_flutterwave_available",
                        staticmethod(lambda currency="NGN": {"available": wallet["available"], "ledger": wallet["available"]}))

    def hand_to_flutterwave(payout, db, manage_transaction=True):
        """Stands in for the real transfer: Flutterwave accepted it."""
        payout.status = "processing"
        wallet["sent"].append(payout.amount)
        return {"success": True}
    monkeypatch.setattr(PayoutService, "process_flutterwave_payout", staticmethod(hand_to_flutterwave))
    return wallet


def _referrer(db, email, *, bank=True, stripe_verified=None):
    """A referrer with a Flutterwave bank account (bank=True), or a Stripe account."""
    user = User(name="Referrer", email=email, password="x", confirm_password="x")
    db.add(user)
    db.flush()
    account = PayoutAccount(user_id=user.id, payment_method="flutterwave" if bank else "stripe")
    if bank:
        account.bank_name, account.account_number, account.bank_code, account.account_name = "GTBank", "0123456789", "058", "Referrer"
    if stripe_verified is not None:
        account.stripe_account_id, account.is_verified = "acct_test", stripe_verified
    db.add(account)
    db.flush()
    return user


def _gbp_commission(db, referrer, payer_email, amount="1.75", hours_old=2):
    """A £7 Stripe payment by a referred user and the referrer's pending commission on it."""
    payer = User(name="Payer", email=payer_email, password="x", confirm_password="x")
    db.add(payer)
    db.flush()
    payment = Subscriptions(user_id=payer.id, subscription_plan="monthly", plan_tier="pro",
                            transaction_id=f"pi_{payer_email}", tx_ref=f"ref_{payer_email}", amount=Decimal("7.00"),
                            currency="GBP", status="completed", payment_provider="stripe",
                            start_date=NOW, end_date=NOW + timedelta(days=30))
    db.add(payment)
    db.flush()
    commission = Commission(user_id=referrer.id, referred_user_id=payer.id, subscription_id=payment.id,
                            amount=Decimal(amount), currency="GBP", status="pending",
                            created_at=NOW - timedelta(hours=hours_old))
    db.add(commission)
    db.commit()  # the payout code rolls back to here when nothing is sent
    return commission, payment


def test_a_low_wallet_is_recorded_as_waiting_for_money_with_the_numbers(db, fake_flutterwave):
    referrer = _referrer(db, "ref-wait@test.local")
    commission, _ = _gbp_commission(db, referrer, "payer-wait@test.local")

    # 1. £1.75 → ₦3,412.50 is more than the ₦1,695.63 wallet: nothing is sent.
    assert CommissionService.settle_pending_commission(commission, db, notify_admin=False) is None
    assert fake_flutterwave["sent"] == []

    # 2. The real reason is recorded: cross-border through Flutterwave, with the numbers.
    attempt = db.query(CommissionPayoutAttempt).filter_by(commission_id=commission.id).one()
    assert attempt.outcome == "waiting_for_money"
    assert attempt.route == "flutterwave" and attempt.cross_border is True
    assert (attempt.from_currency, attempt.to_currency) == ("GBP", "NGN")
    assert attempt.converted_amount == Decimal("3412.50")
    assert "₦3,412.50" in attempt.reason and "₦1,695.63" in attempt.reason

    # 3. The next retry counts on the same row instead of adding one.
    CommissionService.settle_pending_commission(commission, db, notify_admin=False)
    assert db.query(CommissionPayoutAttempt).filter_by(commission_id=commission.id).count() == 1
    db.refresh(attempt)
    assert attempt.tries == 2


def test_once_the_wallet_has_enough_it_is_sent_and_the_history_shows_both(db, fake_flutterwave):
    referrer = _referrer(db, "ref-sent@test.local")
    commission, _ = _gbp_commission(db, referrer, "payer-sent@test.local")
    CommissionService.settle_pending_commission(commission, db, notify_admin=False)

    # 1. Wallet topped up: the next try sends it.
    fake_flutterwave["available"] = Decimal("10000")
    assert CommissionService.settle_pending_commission(commission, db, notify_admin=False)
    assert fake_flutterwave["sent"] == [Decimal("3412.50")]

    # 2. History reads: waiting for money, then sent.
    history = payout_tracker.commission_history(db, commission.id)
    assert [h["outcome"] for h in history] == ["waiting_for_money", "sent"]
    assert history[1]["route_text"] == "Flutterwave, cross-border (GBP → NGN)"


def test_health_check_says_waiting_for_money_not_broken(db, fake_flutterwave):
    referrer = _referrer(db, "ref-health@test.local")
    commission, _ = _gbp_commission(db, referrer, "payer-health@test.local")
    CommissionService.settle_pending_commission(commission, db, notify_admin=False)

    checks = {name: (status, detail) for name, status, detail, _ in payout_tracker.unpaid_commission_checks(db, datetime.now(UTC))}
    # 1. Waiting for money is a warning, with the real reason and the route.
    status, detail = checks["Commissions waiting for money"]
    assert status == "warning"
    assert f"#{commission.id}" in detail and "cross-border (GBP → NGN)" in detail and "₦1,695.63" in detail
    # 2. Nothing is wrongly called "never tried" or "needs action".
    assert checks["Commissions never tried"][0] == "ok"
    assert checks["Commissions that need action"][0] == "ok"


def test_health_check_flags_a_usable_account_that_was_never_tried(db):
    referrer = _referrer(db, "ref-never@test.local")
    commission, _ = _gbp_commission(db, referrer, "payer-never@test.local")
    checks = {name: (status, detail) for name, status, detail, _ in payout_tracker.unpaid_commission_checks(db, datetime.now(UTC))}
    status, detail = checks["Commissions never tried"]
    assert status == "critical" and f"#{commission.id}" in detail


def test_health_check_flags_an_unverified_stripe_account_as_needing_action(db):
    referrer = _referrer(db, "ref-unverified@test.local", bank=False, stripe_verified=False)
    commission, _ = _gbp_commission(db, referrer, "payer-unverified@test.local")
    checks = {name: (status, detail) for name, status, detail, _ in payout_tracker.unpaid_commission_checks(db, datetime.now(UTC))}
    status, detail = checks["Commissions that need action"]
    assert status == "critical" and "isn't verified" in detail
    assert checks["Commissions never tried"][0] == "ok"


def test_tracker_shows_every_payment_with_its_payout_story(db, fake_flutterwave):
    referrer = _referrer(db, "ref-rows@test.local")
    commission, payment = _gbp_commission(db, referrer, "payer-rows@test.local")
    CommissionService.settle_pending_commission(commission, db, notify_admin=False)
    # 1. A second payment with no referrer at all.
    loner = User(name="Loner", email="loner@test.local", password="x", confirm_password="x")
    db.add(loner)
    db.flush()
    db.add(Subscriptions(user_id=loner.id, subscription_plan="monthly", plan_tier="pro", transaction_id="pi_loner",
                         tx_ref="ref_loner", amount=Decimal("7.00"), currency="GBP", status="completed",
                         payment_provider="stripe", start_date=NOW, end_date=NOW + timedelta(days=30)))
    db.flush()

    rows = {r["payment_id"]: r for r in payout_tracker.tracker_rows(db, limit=200)}
    # 2. The referred payment shows the commission's real state.
    story = rows[payment.id]["commissions"][0]
    assert story["state"] == "waiting_for_money" and story["cross_border"] is True
    assert story["route_text"] == "Flutterwave, cross-border (GBP → NGN)"
    # 3. The other payment says why nothing is paid out.
    loner_row = next(r for r in rows.values() if r["payer"] and r["payer"]["email"] == "loner@test.local")
    assert loner_row["no_commission"].startswith("No referrer")
    # 4. 'unpaid' keeps only payments with a commission still owed.
    unpaid_ids = {r["payment_id"] for r in payout_tracker.tracker_rows(db, limit=200, show="unpaid")}
    assert payment.id in unpaid_ids and loner_row["payment_id"] not in unpaid_ids
