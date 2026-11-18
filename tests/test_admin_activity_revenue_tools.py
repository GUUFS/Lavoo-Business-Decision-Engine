"""
Admin activity stamps (api/services/admin_activity.py), the admin's own
password change (api/routes/admin/account.py), Stripe revenue counted when
the money is available (subscriptions/stripe_revenue.py + admin revenue),
the Stripe invoice reconciliation, and discovered tool links written into
analyses (decision_engine/tool_discovery.link_into_analyses).
Stripe is faked: no network.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
import stripe
from fastapi import HTTPException

from api.services import admin_activity
from database.pg_models import (
    AdminActivity,
    AITool,
    BusinessAnalysis,
    Commission,
    Subscriptions,
    ToolDiscovery,
    User,
)

NOW = datetime.now(UTC)


def _user(db, email, **extra):
    """A user (admin or not)."""
    from api.routes.auth.login import pwd_context
    user = User(name=email.split("@")[0].title(), email=email, password=pwd_context.hash("old-password-1"),
                confirm_password="x", **extra)
    db.add(user)
    db.flush()
    return user


# ------------------------------------------------------------ activity stamps

def test_only_changes_from_the_admin_end_are_stamped():
    # 1. Reads are never stamped.
    assert not admin_activity.should_record("GET", "/api/control/users", None)
    # 2. Admin-only addresses are, and so is anything called from the admin website.
    assert admin_activity.should_record("POST", "/api/control/refunds/payments/ch_1/refund", None)
    assert admin_activity.should_record("POST", "/api/business/clarify/exam/run", "https://control.lavooai.com/admin/micromodel")
    # 3. The same address from the main app is a user's action, not an admin's.
    assert not admin_activity.should_record("POST", "/api/business/analyze", "https://lavooai.com/l/decision-engine")


def test_actions_are_described_in_plain_words():
    assert admin_activity.describe("POST", "/api/control/refunds/payments/ch_9/refund") == "Refunded Stripe payment ch_9"
    assert admin_activity.describe("PATCH", "/api/control/permissions/12/partner") == "Changed partner status of user #12"
    assert admin_activity.describe("DELETE", "/api/admin/content/alerts/3") == "Deleted alerts item #3"
    # An address without a rule still reads sensibly.
    assert admin_activity.describe("POST", "/api/control/something/new") == "Did: something → new"


def test_an_admins_change_is_stamped_with_who_and_when(db, monkeypatch):
    admin = _user(db, "stamp-admin@test.local", is_admin=True)
    # 1. Use the test session, and pretend the token belongs to this admin.
    import api.routes.auth.login as login
    import database.pg_connections as connections
    monkeypatch.setattr(connections, "SessionLocal", lambda: SimpleNamespace(
        add=db.add, commit=db.flush, rollback=lambda: None, close=lambda: None))
    monkeypatch.setattr(login, "get_current_user", lambda a, c, s: admin)

    admin_activity.record("Bearer x", None, "POST", "/api/control/refunds/payments/ch_5/refund", "", 200, "1.2.3.4")

    stamp = db.query(AdminActivity).filter_by(admin_id=admin.id).one()
    assert stamp.action == "Refunded Stripe payment ch_5" and stamp.succeeded is True
    assert stamp.admin_name == admin.name and stamp.created_at is not None


def test_a_non_admin_is_not_stamped(db, monkeypatch):
    user = _user(db, "plain-user@test.local", is_admin=False)
    import api.routes.auth.login as login
    import database.pg_connections as connections
    monkeypatch.setattr(connections, "SessionLocal", lambda: SimpleNamespace(
        add=db.add, commit=db.flush, rollback=lambda: None, close=lambda: None))
    monkeypatch.setattr(login, "get_current_user", lambda a, c, s: user)
    admin_activity.record("Bearer x", None, "POST", "/api/control/users/1/status", "", 200, None)
    assert db.query(AdminActivity).filter_by(admin_id=user.id).count() == 0


# ------------------------------------------------------------ change password

def test_admin_changes_own_password(db):
    from api.routes.admin.account import ChangeOwnPassword, change_own_password
    from api.routes.auth.login import pwd_context
    admin = _user(db, "pw-admin@test.local", is_admin=True)

    # 1. Wrong current password: refused with a clear reason.
    with pytest.raises(HTTPException, match="current password is wrong"):
        change_own_password(ChangeOwnPassword(current_password="nope", new_password="new-password-2",
                                              confirm_password="new-password-2"), admin=admin, db=db)
    # 2. Mismatched new passwords: refused.
    with pytest.raises(HTTPException, match="don't match"):
        change_own_password(ChangeOwnPassword(current_password="old-password-1", new_password="new-password-2",
                                              confirm_password="new-password-3"), admin=admin, db=db)
    # 3. Right: both hashes now match the new password.
    change_own_password(ChangeOwnPassword(current_password="old-password-1", new_password="new-password-2",
                                          confirm_password="new-password-2"), admin=admin, db=db)
    assert pwd_context.verify("new-password-2", admin.password)
    assert pwd_context.verify("new-password-2", admin.confirm_password)


# ------------------------------------------------------------ Stripe revenue

def _stripe_payment(db, user, tx_id, amount, days_ago):
    """A recorded £ Stripe payment."""
    row = Subscriptions(user_id=user.id, subscription_plan="monthly", plan_tier="pro", transaction_id=tx_id,
                        tx_ref=f"ref-{tx_id}", amount=Decimal(amount), currency="GBP", status="completed",
                        payment_provider="stripe", start_date=NOW, end_date=NOW + timedelta(days=30),
                        created_at=NOW - timedelta(days=days_ago))
    db.add(row)
    db.flush()
    return row


def test_stripe_payments_count_only_once_available(db, monkeypatch):
    from api.routes.admin import revenue
    payer = _user(db, "rev-payer@test.local")
    referrer = _user(db, "rev-ref@test.local")
    available = _stripe_payment(db, payer, "pi_available", "7.00", 6)
    pending = _stripe_payment(db, payer, "pi_pending", "7.00", 1)
    # 1. A £1.75 bonus on each payment.
    for row in (available, pending):
        db.add(Commission(user_id=referrer.id, referred_user_id=payer.id, subscription_id=row.id,
                          amount=Decimal("1.75"), currency="GBP", status="pending"))
    db.flush()
    # 2. Stripe: the first is available (net £6.69), the second still incoming.
    status_map = {
        "pi_available": {"status": "available", "available_on": NOW - timedelta(hours=1), "net": Decimal("6.69"),
                         "fee": Decimal("0.31"), "currency": "GBP"},
        "pi_pending": {"status": "pending", "available_on": NOW + timedelta(days=4), "net": Decimal("6.69"),
                       "fee": Decimal("0.31"), "currency": "GBP"},
    }
    monkeypatch.setattr(revenue, "stripe_payment_status", lambda: status_map)
    before = revenue.compute_revenue_stats(db)["by_currency"]["GBP"]

    # 3. Only the available one counts, at net, minus only its own bonus.
    stats = revenue.compute_revenue_stats(db)
    gbp = stats["by_currency"]["GBP"]
    assert gbp["stripe_incoming"] >= 6.69
    assert stats["stripe_counting"] == {"basis": "available", "stripe_reachable": True}
    # 4. Once the second becomes available it adds £6.69 - £1.75.
    status_map["pi_pending"].update(status="available", available_on=NOW - timedelta(minutes=1))
    after = revenue.compute_revenue_stats(db)["by_currency"]["GBP"]
    assert round(after["monthly_revenue"] - before["monthly_revenue"], 2) == round(6.69 - 1.75, 2)
    assert round(before["stripe_incoming"] - after["stripe_incoming"], 2) == 6.69


def test_unmatched_stripe_rows_use_the_age_rule():
    from subscriptions.stripe_revenue import when_counted
    old = SimpleNamespace(transaction_id="sub_x", amount=Decimal("7"), currency="GBP", created_at=NOW - timedelta(days=9))
    new = SimpleNamespace(transaction_id="sub_y", amount=Decimal("7"), currency="GBP", created_at=NOW - timedelta(days=2))
    assert when_counted(old, {}, NOW)["counted"] is True
    assert when_counted(new, None, NOW)["counted"] is False


# ------------------------------------------------------------ invoice reconciliation

def test_a_renewal_invoice_is_found_through_its_payment_intent(db, monkeypatch):
    from subscriptions.payout_service import PayoutService
    payer = _user(db, "recon@test.local")
    _stripe_payment(db, payer, "pi_renewal_1", "7.00", 0)
    obj = lambda d: stripe.StripeObject.construct_from(d, "sk_test")  # noqa: E731
    monkeypatch.setattr(stripe.InvoicePayment, "list", lambda **k: obj(
        {"data": [{"payment": {"type": "payment_intent", "payment_intent": "pi_renewal_1"}}]}))
    invoice = obj({"id": "in_new_api", "billing_reason": "subscription_cycle",
                   "parent": {"subscription_details": {"subscription": "sub_1"}}})
    # 1. Found, although the invoice has no payment_intent field (new Stripe API).
    assert PayoutService.stripe_invoice_is_recorded(db, invoice) is True
    # 2. A renewal is NOT matched by its subscription id alone.
    monkeypatch.setattr(stripe.InvoicePayment, "list", lambda **k: obj({"data": []}))
    _stripe_payment(db, payer, "sub_1", "7.00", 30)
    assert PayoutService.stripe_invoice_is_recorded(db, invoice) is False


# ------------------------------------------------------------ tool links in analyses

def test_a_discovered_tools_link_is_written_into_the_analysis(db):
    from decision_engine.tool_discovery import link_into_analyses
    owner = _user(db, "analysis-owner@test.local")
    analysis = BusinessAnalysis(
        user_id=owner.id, business_goal="More customers",
        recommended_tool_stacks=[{"stack_name": "Growth", "tools": ["Zapier"],
                                  "setup_order": [{"tool_name": "Brevo Pro", "url": None, "website": None}]}],
        single_tool_recommendation={"tool_name": "Other Tool", "website": None},
    )
    db.add(analysis)
    tool = AITool(name="Brevo Pro", url="https://www.brevo.com", description="Email marketing", source="discovered")
    db.add(tool)
    db.flush()
    row = ToolDiscovery(name="Brevo Pro", name_key="brevo pro", status="added", website="https://www.brevo.com",
                        tool_id=tool.id, reason="Added as Brevo Pro.", attempts=1, times_suggested=1)
    db.add(row)
    db.commit()

    # 1. The link goes into the analysis that named the tool.
    assert link_into_analyses(db, row) == [analysis.id]
    db.refresh(analysis)
    entry = analysis.recommended_tool_stacks[0]["setup_order"][0]
    assert entry["website"] == entry["url"] == "https://www.brevo.com"
    # 2. Other tools are left alone; the report records the analysis.
    assert analysis.single_tool_recommendation["website"] is None
    assert row.linked_analyses == [analysis.id] and f"#{analysis.id}" in row.reason
    # 3. Running it again changes nothing.
    assert link_into_analyses(db, row) == []


# ------------------------------------------------------------ negative balance fixes

def test_a_dollar_payment_landing_in_pounds_takes_its_bonus_off_pounds(db, monkeypatch):
    """A $ payment lands in the £ Stripe balance. Its $ bonus must come off
    the £ column too (converted), not off $, which made $ go negative."""
    from api.routes.admin import revenue
    payer = _user(db, "fx-payer@test.local")
    referrer = _user(db, "fx-ref@test.local")
    # 1. $8.50 charged; it landed as £6.70 before Stripe's £0.30 fee (£6.40 net).
    row = Subscriptions(user_id=payer.id, subscription_plan="monthly", plan_tier="pro", transaction_id="pi_fx_usd",
                        tx_ref="ref-fx", amount=Decimal("8.50"), currency="USD", status="completed",
                        payment_provider="stripe", start_date=NOW, end_date=NOW + timedelta(days=30),
                        created_at=NOW - timedelta(days=5))
    db.add(row)
    db.flush()
    db.add(Commission(user_id=referrer.id, referred_user_id=payer.id, subscription_id=row.id,
                      amount=Decimal("1.70"), currency="USD", status="pending"))
    db.flush()
    status_map = {"pi_fx_usd": {"status": "pending", "available_on": NOW + timedelta(days=2),
                                "net": Decimal("6.40"), "fee": Decimal("0.30"), "currency": "GBP"}}
    monkeypatch.setattr(revenue, "stripe_payment_status", lambda: status_map)
    before = revenue.compute_revenue_stats(db)["by_currency"]
    # 2. The money becomes available.
    status_map["pi_fx_usd"].update(status="available", available_on=NOW - timedelta(minutes=1))
    after = revenue.compute_revenue_stats(db)["by_currency"]
    usd_before = before.get("USD", {}).get("total_subscription_revenue", 0.0)
    usd_after = after.get("USD", {}).get("total_subscription_revenue", 0.0)
    # 3. $ is untouched; £ gets £6.40 minus the bonus at the payment's rate ($1.70 x 6.70/8.50 = £1.34).
    assert round(usd_after - usd_before, 2) == 0
    gbp_change = after["GBP"]["total_subscription_revenue"] - before["GBP"]["total_subscription_revenue"]
    assert round(gbp_change, 2) == round(6.40 - 1.34, 2)


def test_a_cancelled_bonus_on_a_refunded_payment_is_not_taken_off(db, monkeypatch):
    """Refunded payment: it leaves revenue and its unpaid bonus is 'reversed'.
    The reversed bonus must not keep lowering revenue."""
    from api.routes.admin import revenue
    monkeypatch.setattr(revenue, "stripe_payment_status", lambda: {})
    payer = _user(db, "refund-payer@test.local")
    referrer = _user(db, "refund-ref@test.local")
    before = revenue.compute_revenue_stats(db)["by_currency"].get("USD", {}).get("total_subscription_revenue", 0.0)
    # 1. A refunded Flutterwave $ payment whose bonus was cancelled.
    row = Subscriptions(user_id=payer.id, subscription_plan="monthly", plan_tier="pro", transaction_id="flw-refunded",
                        tx_ref="ref-flw-refunded", amount=Decimal("8.50"), currency="USD", status="refunded",
                        payment_provider="flutterwave", start_date=NOW, end_date=NOW + timedelta(days=30))
    db.add(row)
    db.flush()
    db.add(Commission(user_id=referrer.id, referred_user_id=payer.id, subscription_id=row.id,
                      amount=Decimal("1.70"), currency="USD", status="reversed"))
    db.flush()
    after = revenue.compute_revenue_stats(db)["by_currency"].get("USD", {}).get("total_subscription_revenue", 0.0)
    # 2. Nothing changes: no payment counted, no bonus taken off.
    assert round(after - before, 2) == 0
