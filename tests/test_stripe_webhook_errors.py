"""
Stripe webhook error handling (subscriptions/stripe.py stripe_webhook).

A payment event that fails to record must answer an error so Stripe retries
it; answering 200 told Stripe it was handled and the payment was lost.
A retry after the failure must record the payment exactly once.
"""
import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import stripe
from fastapi import HTTPException
from starlette.requests import Request

from database.pg_models import Subscriptions, User
from subscriptions.commission_service import CommissionService
from subscriptions.stripe import stripe_webhook


def _invoice_event(user_id, pi):
    """An invoice.payment_succeeded event for one $9 monthly renewal."""
    start = int(datetime.now(UTC).timestamp())
    end = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
    return {"id": f"evt_{pi}", "object": "event", "type": "invoice.payment_succeeded", "data": {"object": {
        "id": f"in_{pi}", "object": "invoice", "subscription": "sub_webhook_test", "payment_intent": pi,
        "billing_reason": "subscription_cycle", "amount_paid": 900, "currency": "usd",
        "customer": "cus_webhook_test", "metadata": {"user_id": str(user_id)},
        "lines": {"data": [{"period": {"start": start, "end": end}}]}}}}


def _deliver(db, event):
    """Deliver one unsigned (test-mode) webhook to the real handler."""
    body = json.dumps(event).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    request = Request({"type": "http", "method": "POST", "path": "/api/stripe/webhook", "headers": []}, receive)
    return asyncio.run(stripe_webhook(request, None, db))


@pytest.fixture
def subscriber(db, monkeypatch):
    """A user with a Stripe subscription; Stripe's API is faked."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    user = User(name="Webhook", email="webhook@test.local", password="x", confirm_password="x")
    db.add(user)
    db.commit()
    sub = stripe.StripeObject.construct_from(
        {"id": "sub_webhook_test", "status": "active", "metadata": {"user_id": str(user.id), "plan_type": "monthly"},
         "items": {"data": []}}, None)
    with patch.object(stripe.Subscription, "retrieve", return_value=sub), \
         patch("subscriptions.founding.after_stripe_payment"), \
         patch("subscriptions.stripe.NotificationService.create_notification"):
        yield user


def test_failed_payment_event_asks_stripe_to_retry(db, subscriber):
    with patch.object(CommissionService, "calculate_commission", side_effect=RuntimeError("database hiccup")), \
         pytest.raises(HTTPException) as failed:
        _deliver(db, _invoice_event(subscriber.id, "pi_retry_1"))
    assert failed.value.status_code == 500
    assert db.query(Subscriptions).filter_by(transaction_id="pi_retry_1").count() == 0   # nothing half-saved

    # Stripe's retry succeeds, and records the payment once.
    with patch.object(CommissionService, "calculate_commission"):
        assert _deliver(db, _invoice_event(subscriber.id, "pi_retry_1")) == {"status": "success"}
        _deliver(db, _invoice_event(subscriber.id, "pi_retry_1"))
    assert db.query(Subscriptions).filter_by(transaction_id="pi_retry_1").count() == 1


def test_two_invoices_in_the_same_second_are_both_recorded(db, subscriber):
    with patch.object(CommissionService, "calculate_commission"):
        _deliver(db, _invoice_event(subscriber.id, "pi_same_second_a"))
        _deliver(db, _invoice_event(subscriber.id, "pi_same_second_b"))
    rows = db.query(Subscriptions).filter(Subscriptions.user_id == subscriber.id).all()
    assert sorted(r.transaction_id for r in rows) == ["pi_same_second_a", "pi_same_second_b"]
    assert len({r.tx_ref for r in rows}) == 2
