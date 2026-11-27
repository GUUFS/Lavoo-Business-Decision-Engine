"""
Emails and revenue fixes from 2026-11-19.

- Every email says "Lavoo. The Business Doctor" (never the old "Lavoo Business
  Intelligence Engine"), as sender name too, uses the app's black-and-orange look instead of the
  old purple, and the app's words: Premium, check-up, Builder Bonus.
- flutterwave.py's failed-payment email has a method behind it (it used to
  crash with AttributeError).
- Cancelling a Stripe subscription ends the plan but keeps the payment in
  revenue: the dollars a customer paid don't vanish when they cancel.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from database.pg_models import Subscriptions, User
from emailing.email_service import email_service
from tests.test_stripe_webhook_errors import _deliver, subscriber  # noqa: F401  (subscriber is a fixture)

EMAIL_FILE = Path(__file__).resolve().parents[1] / "emailing" / "email_service.py"


def _capture(monkeypatch) -> dict:
    """Catch the next email instead of sending it; returns what was sent."""
    sent = {}
    monkeypatch.setattr(email_service, "_send_email",
                        lambda to, name, subject, html, text=None, reply_to=None:
                        sent.update(subject=subject, html=html, text=text) or {"status": "sent"})
    return sent


def test_no_email_uses_the_old_name_or_purple():
    # 1. The source holds every template: none may keep the old name or colours.
    source = EMAIL_FILE.read_text(encoding="utf-8")
    assert "Intelligence" not in source
    for purple in ("#8b5cf6", "#7c3aed", "#6366f1", "#667eea", "#764ba2"):
        assert purple not in source


def test_sender_name_is_quoted_in_the_from_line(monkeypatch):
    # The name has a full stop, so the From line must put it in quotes, or
    # some mail servers reject the email. Resend is caught, not called.
    sent = {}

    class Answer:
        status_code = 200
        text = ""

        def json(self):
            return {"id": "x"}

    monkeypatch.delenv("FROM_NAME", raising=False)
    monkeypatch.setattr(email_service, "from_name", "Lavoo. The Business Doctor")
    monkeypatch.setattr(email_service, "resend_api_key", "test-key")
    monkeypatch.setattr("emailing.email_service.requests.post",
                        lambda url, headers=None, json=None, timeout=None: sent.update(json) or Answer())
    email_service._send_email("u@test.local", "Ada", "Hi", "<p>Hi</p>")
    assert sent["from"] == f'"Lavoo. The Business Doctor" <{email_service.from_email}>'


def test_welcome_email_speaks_like_the_app(monkeypatch):
    sent = _capture(monkeypatch)
    email_service.send_welcome_email("new@test.local", "Ada")
    assert sent["subject"] == "Welcome to Lavoo. The Business Doctor"
    assert "check-up" in sent["html"] and "Builder Bonus" in sent["html"] and "Missions" in sent["html"]
    assert "/l/decision-engine" in sent["html"] and "Lavoo. The Business Doctor" in sent["html"]


def test_admin_message_has_the_brand_header(monkeypatch):
    # The "Welcome" message an admin sends uses the plain layout (was purple).
    sent = _capture(monkeypatch)
    email_service.send_admin_message("u@test.local", "Ada", "Welcome", "Hello")
    assert "#18181b" in sent["html"] and "#e87a02" in sent["html"]
    assert "Lavoo. The Business Doctor" in sent["html"]


def test_plan_names_match_the_app(monkeypatch):
    assert email_service._plan_name("monthly") == "Premium (Monthly)"
    assert email_service._plan_name("") == "Premium"
    sent = _capture(monkeypatch)
    email_service.send_payment_success_email("p@test.local", "Ada", 5000, "monthly", "December 19, 2026", "NGN ")
    assert "Premium (Monthly)" in sent["subject"] and "NGN 5000.00" in sent["html"]


def test_builder_bonus_not_commission(monkeypatch):
    sent = _capture(monkeypatch)
    email_service.send_commission_notification("r@test.local", "Ada", 4.5, "$", "Bola", "Nov 19, 2026")
    assert "Builder Bonus" in sent["subject"] and "ommission" not in sent["html"]


def test_flutterwave_failed_payment_email_exists(monkeypatch):
    # flutterwave.py calls send_payment_failed_email(email, name, amount, reason).
    sent = _capture(monkeypatch)
    email_service.send_payment_failed_email("f@test.local", "Ada", 0.0, "Card declined")
    assert sent["subject"] == "Payment Failed - Action Required"
    assert "Card declined" in sent["html"] and "Retry Date" not in sent["html"]


def test_cancelling_keeps_the_payment_in_revenue(db, subscriber):  # noqa: F811
    from api.routes.admin.revenue import compute_revenue_stats
    now = datetime.now(UTC)
    # 1. A $9 Stripe payment for this subscription.
    db.add(Subscriptions(user_id=subscriber.id, subscription_plan="monthly", transaction_id="sub_webhook_test",
                         tx_ref="ref-cancel-1", amount=Decimal("9.00"), currency="USD", status="completed",
                         subscription_status="active", payment_provider="stripe",
                         start_date=now, end_date=now + timedelta(days=30)))
    db.commit()
    before = compute_revenue_stats(db)["by_currency"]["USD"]["charged_revenue"]
    # 2. Stripe says the subscription was cancelled.
    _deliver(db, {"id": "evt_cancel_1", "object": "event", "type": "customer.subscription.deleted",
                  "data": {"object": {"id": "sub_webhook_test", "object": "subscription",
                                      "customer": "cus_webhook_test"}}})
    # 3. The plan ended, the payment still counts.
    row = db.query(Subscriptions).filter_by(tx_ref="ref-cancel-1").one()
    assert row.subscription_status == "cancelled" and row.status == "completed"
    assert db.get(User, subscriber.id).subscription_status == "cancelled"
    assert compute_revenue_stats(db)["by_currency"]["USD"]["charged_revenue"] == before


def test_amounts_show_the_currency_paid_in():
    # "$" for dollars, "£" for pounds, the code for anything else.
    assert email_service.currency_prefix("usd") == "$"
    assert email_service.currency_prefix("GBP") == "£"
    assert email_service.currency_prefix("NGN") == "NGN "
    assert email_service.currency_prefix(None) == "$"
