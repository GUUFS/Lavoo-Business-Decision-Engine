"""
Admin refunds (subscriptions/admin_refunds.py), admin emails
(api/routes/admin/user_emails.py) and the partner welcome email.
Stripe is faked: no network, no real money.

A refund must: give the money back, cancel the Stripe subscription, end
access now, cancel an unpaid commission (or record a clawback for a paid
one), and record every step.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
import stripe

from database.pg_models import AdminRefund, AdminSentEmail, Commission, Subscriptions, User
from subscriptions import admin_refunds

NOW = datetime.now(UTC)


class FakeStripe:
    """Stands in for the Stripe calls a refund makes, and remembers them."""

    def __init__(self, charge: dict, invoice: dict | None, subscription: dict | None):
        self.charge, self.invoice, self.subscription = charge, invoice, subscription
        self.refunds, self.cancelled = [], []

    def install(self, monkeypatch):
        """Replace the real Stripe calls with this fake."""
        obj = lambda d: stripe.StripeObject.construct_from(d, "sk_test_fake")  # noqa: E731
        monkeypatch.setattr(stripe.Charge, "retrieve", lambda *a, **k: obj(self.charge))
        monkeypatch.setattr(stripe.InvoicePayment, "list",
                            lambda **k: obj({"data": [{"invoice": self.invoice}] if self.invoice else []}))
        monkeypatch.setattr(stripe.Subscription, "retrieve", lambda *a, **k: obj(self.subscription))
        monkeypatch.setattr(stripe.Subscription, "cancel", lambda sub_id, **k: self.cancelled.append(sub_id))

        def create_refund(**kwargs):
            self.refunds.append(kwargs)
            return obj({"id": "re_test_1"})
        monkeypatch.setattr(stripe.Refund, "create", create_refund)


def _paying_user(db, email="payer@test.local"):
    """A user on an active monthly plan, paid through Stripe subscription sub_test_1."""
    user = User(name="Payer", email=email, password="x", confirm_password="x", subscription_status="active",
                subscription_plan="monthly", stripe_customer_id="cus_test_1",
                subscription_expires_at=NOW + timedelta(days=25))
    db.add(user)
    db.flush()
    record = Subscriptions(user_id=user.id, subscription_plan="monthly", plan_tier="pro", transaction_id="sub_test_1",
                           tx_ref="ref-refund-1", amount=Decimal("7.00"), currency="GBP", status="completed",
                           subscription_status="active", payment_provider="stripe",
                           start_date=NOW - timedelta(days=5), end_date=NOW + timedelta(days=25))
    db.add(record)
    db.flush()
    return user, record


def _referrer_commission(db, user, record, status):
    """A referrer's commission on the payment, in the given status."""
    referrer = User(name="Referrer", email=f"ref-{status}@test.local", password="x", confirm_password="x")
    db.add(referrer)
    db.flush()
    commission = Commission(user_id=referrer.id, referred_user_id=user.id, subscription_id=record.id,
                            amount=Decimal("3.50"), currency="GBP", status=status)
    db.add(commission)
    db.flush()
    return commission


def _fake_stripe_for_seven_pounds():
    """A £7 renewal payment for sub_test_1."""
    return FakeStripe(
        charge={"id": "ch_test_1", "status": "succeeded", "amount": 700, "amount_refunded": 0, "currency": "gbp",
                "payment_intent": "pi_test_1", "customer": "cus_test_1"},
        invoice={"id": "in_test_1", "billing_reason": "subscription_cycle",
                 "parent": {"subscription_details": {"subscription": "sub_test_1"}}},
        subscription={"id": "sub_test_1", "status": "active", "metadata": {"source": "auto_renewal"}},
    )


def test_refund_gives_money_back_stops_charges_ends_access_and_cancels_unpaid_commission(db, monkeypatch):
    user, record = _paying_user(db)
    commission = _referrer_commission(db, user, record, "pending")
    fake = _fake_stripe_for_seven_pounds()
    fake.install(monkeypatch)

    result = admin_refunds.refund_payment(db, "ch_test_1", admin_id=None, note="customer asked")

    # 1. The money went back, once (with a key that stops double refunds).
    assert len(fake.refunds) == 1 and fake.refunds[0]["charge"] == "ch_test_1"
    assert fake.refunds[0]["idempotency_key"] == "admin-refund-ch_test_1"
    # 2. The Stripe subscription was cancelled, so it won't charge again.
    assert fake.cancelled == ["sub_test_1"]
    # 3. Our record is refunded and the user is no longer active.
    db.refresh(record)
    db.refresh(user)
    assert record.status == "refunded"
    assert user.subscription_status != "active"
    # 4. The unpaid commission was cancelled.
    db.refresh(commission)
    assert commission.status == "reversed"
    # 5. The refund is recorded with its steps.
    saved = db.query(AdminRefund).filter_by(stripe_charge_id="ch_test_1").one()
    assert saved.amount == Decimal("7.00") and saved.currency == "GBP" and saved.user_id == user.id
    assert any("Cancelled the referrer's unpaid commission" in step for step in result["steps"])


def test_a_paid_out_commission_is_clawed_back(db, monkeypatch):
    user, record = _paying_user(db, "payer2@test.local")
    commission = _referrer_commission(db, user, record, "paid")
    _fake_stripe_for_seven_pounds().install(monkeypatch)

    result = admin_refunds.refund_payment(db, "ch_test_1", admin_id=None)

    db.refresh(commission)
    assert commission.status == "clawed_back"
    assert any("clawback is recorded" in step for step in result["steps"])


def test_an_already_refunded_payment_is_refused(db, monkeypatch):
    fake = _fake_stripe_for_seven_pounds()
    fake.charge["amount_refunded"] = 700
    fake.install(monkeypatch)
    with pytest.raises(ValueError, match="already been refunded"):
        admin_refunds.refund_payment(db, "ch_test_1", admin_id=None)
    assert fake.refunds == []


def test_why_a_card_was_charged_in_plain_words():
    reasons = admin_refunds._why_charged(
        {"billing_reason": "subscription_cycle"}, {"metadata": {"source": "auto_renewal"}})
    assert reasons[0].startswith("Automatic renewal")
    assert "daily expiry job" in reasons[1]


def test_our_record_is_found_through_the_invoices_subscription(db, monkeypatch):
    _, record = _paying_user(db, "payer3@test.local")
    invoice = {"id": "in_other", "parent": {"subscription_details": {"subscription": "sub_test_1"}}}
    # 1. Not stored under the payment intent or invoice, but under the subscription id.
    assert admin_refunds.find_our_payment_record(db, "pi_unknown", invoice).id == record.id


# ------------------------------------------------------------- emails

def test_admin_message_is_escaped_and_keeps_line_breaks(monkeypatch):
    from emailing.email_service import email_service
    sent = {}
    monkeypatch.setattr(email_service, "_send_email",
                        lambda to, name, subject, html, text=None, reply_to=None:
                        sent.update(to=to, html=html, reply_to=reply_to) or {"status": "sent"})
    email_service.send_admin_message("u@test.local", "Ada", "Hello", "Line one\n<script>x</script>")
    assert "Line one<br>&lt;script&gt;" in sent["html"] and "<script>" not in sent["html"]
    assert sent["reply_to"] == email_service.support_email


def test_sending_an_email_to_a_user_records_it(db, monkeypatch):
    from api.routes.admin.user_emails import SendEmailRequest, send_email
    from emailing.email_service import email_service
    monkeypatch.setattr(email_service, "send_admin_message", lambda *a, **k: {"status": "sent"})
    user = User(name="Reader", email="reader@test.local", password="x", confirm_password="x")
    db.add(user)
    db.flush()
    send_email(SendEmailRequest(user_id=user.id, subject="Hi", message="Welcome"), admin=SimpleNamespace(id=None), db=db)
    saved = db.query(AdminSentEmail).filter_by(to_email="reader@test.local").one()
    assert saved.subject == "Hi" and saved.status == "sent"


def test_only_a_new_partner_is_marked_new(db, monkeypatch):
    from subscriptions import partner_service
    monkeypatch.setattr(partner_service, "pause_stripe_billing", lambda user: 0)
    user = User(name="Partner", email="partner-new@test.local", password="x", confirm_password="x")
    db.add(user)
    db.flush()
    # 1. Becoming a partner: new (the welcome email is sent).
    assert partner_service.grant_partner(db, user)["is_new"] is True
    # 2. Saved as partner again: not new (no second email).
    assert partner_service.grant_partner(db, user)["is_new"] is False
