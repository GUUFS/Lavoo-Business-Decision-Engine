"""
Partners (subscriptions/partner_service.py, set on the admin Permissions page):
  - 50% Builder Bonus rate on their referrals;
  - Premium free for 6 calendar months from the day they become a partner,
    kept active by the status sync and the checkup limits while it lasts;
  - removing partner status ends both; when the 6 months end they go back
    to what they pay for (or Free) but stay a partner;
  - a partner's Stripe subscription is paused (invoices voided) until the
    free Premium ends, and resumed if partner status is removed early.
Also: new users get 3 free days (BetaService.get_grace_period_days).
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import stripe

from api.utils.sub_utils import sync_user_subscription
from database.pg_models import Subscriptions, User
from decision_engine.checkup_limits import user_plan_tier
from subscriptions.beta_service import BetaService
from subscriptions.commission_service import CommissionService
from subscriptions.partner_service import (
    end_expired_partner_premium,
    grant_partner,
    partner_premium_active,
    partner_premium_user_ids,
    revoke_partner,
)

JOINED = datetime(2026, 11, 9, 10, tzinfo=UTC)


def _partner(db, name="Partner", now=None):
    """A free user with no payments, made a partner (at `now`)."""
    user = _user(db, name)
    grant_partner(db, user, now=now)
    return user


def _user(db, name="Partner"):
    """A free user with no payments."""
    user = User(name=name, email=f"{name.lower().replace(' ', '')}@test.local", password="x",
                confirm_password="x", subscription_status="Free")
    db.add(user)
    db.flush()
    return user


def test_new_partner_gets_six_months_of_premium_from_the_day_they_join(db):
    user = _partner(db, now=JOINED)
    assert user.is_partner is True
    assert user.partner_since == JOINED
    assert user.partner_premium_until == datetime(2027, 5, 9, 10, tzinfo=UTC)
    assert user.subscription_status == "active"
    assert partner_premium_active(user, JOINED + timedelta(days=150))
    assert not partner_premium_active(user, datetime(2027, 5, 9, 10, tzinfo=UTC))


def test_partner_with_no_payments_stays_active_through_the_status_sync(db):
    user = _partner(db)
    sync_user_subscription(db, user)       # would reset a non-payer to Free
    assert user.subscription_status == "active"


def test_partner_gets_premium_checkups(db):
    user = _partner(db)
    assert user_plan_tier(db, user) == "premium"


def test_making_an_existing_partner_a_partner_again_does_not_restart_the_six_months(db):
    user = _partner(db, now=JOINED)
    grant_partner(db, user, now=JOINED + timedelta(days=60))
    assert user.partner_since == JOINED
    assert user.partner_premium_until == datetime(2027, 5, 9, 10, tzinfo=UTC)


def test_removing_partner_ends_premium_and_the_rate(db):
    user = _partner(db)
    revoke_partner(db, user)
    assert user.is_partner is False and user.partner_premium_until is None
    assert user.subscription_status == "Free"
    assert user_plan_tier(db, user) == "pro"


def test_when_the_six_months_end_they_go_back_to_free_but_stay_a_partner(db):
    user = _partner(db, now=JOINED)
    assert user.id in partner_premium_user_ids(db, JOINED + timedelta(days=30))
    after = datetime(2027, 5, 10, tzinfo=UTC)
    assert end_expired_partner_premium(db, now=after) >= 1
    assert user.subscription_status == "Free"
    assert user.is_partner is True
    assert user.id not in partner_premium_user_ids(db, after)


def test_partner_who_pays_stays_active_after_the_six_months(db):
    user = _partner(db, now=JOINED)
    now = datetime.now(UTC)
    db.add(Subscriptions(user_id=user.id, subscription_plan="monthly", plan_tier="pro", transaction_id="tx-partner",
                         tx_ref="ref-partner", amount=Decimal("9"), currency="USD", status="completed",
                         subscription_status="active", payment_provider="stripe", start_date=now,
                         end_date=now + timedelta(days=30)))
    db.flush()
    end_expired_partner_premium(db, now=datetime(2027, 5, 10, tzinfo=UTC))
    assert user.subscription_status == "active"


def test_partner_earns_the_50_percent_rate(db):
    partner = _partner(db)
    assert CommissionService._get_rate_for_referrer(partner.id, db) == Decimal("0.50")


def test_new_users_get_three_free_days(monkeypatch):
    monkeypatch.delenv("GRACE_PERIOD_DAYS", raising=False)
    monkeypatch.setattr(BetaService, "_get_dynamic_env", staticmethod(lambda: {}))
    assert BetaService.get_grace_period_days() == 3


class FakeStripe:
    """Records the Stripe calls made for one customer's subscriptions."""

    def __init__(self, subs):
        self.subs = subs          # what Subscription.list returns
        self.modified = []        # (subscription id, changes) per modify call

    def list(self, **kwargs):
        return {"data": self.subs}

    def modify(self, sub_id, **kwargs):
        self.modified.append((sub_id, kwargs))
        return {"id": sub_id}


def _stripe_customer(db, monkeypatch, subs):
    """A free user with a Stripe customer, and a fake Stripe holding `subs`."""
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_fake")
    user = _user(db, "Stripe Partner")
    user.stripe_customer_id = "cus_partner"
    db.flush()
    return user, FakeStripe(subs)


def test_new_partner_stripe_billing_is_paused_until_free_premium_ends(db, monkeypatch):
    user, fake = _stripe_customer(db, monkeypatch, [
        {"id": "sub_paying", "status": "active", "metadata": {}},
        {"id": "sub_old", "status": "canceled", "metadata": {}},
    ])
    with patch.object(stripe.Subscription, "list", side_effect=fake.list), \
         patch.object(stripe.Subscription, "modify", side_effect=fake.modify):
        assert grant_partner(db, user, now=JOINED) == {"stripe_paused": 1}
    sub_id, changes = fake.modified[0]
    assert sub_id == "sub_paying" and len(fake.modified) == 1          # cancelled ones are left alone
    assert changes["pause_collection"] == {
        "behavior": "void", "resumes_at": int(datetime(2027, 5, 9, 10, tzinfo=UTC).timestamp())}


def test_regranting_an_existing_partner_does_not_pause_again(db, monkeypatch):
    user, fake = _stripe_customer(db, monkeypatch, [{"id": "sub_paying", "status": "active", "metadata": {}}])
    with patch.object(stripe.Subscription, "list", side_effect=fake.list), \
         patch.object(stripe.Subscription, "modify", side_effect=fake.modify):
        grant_partner(db, user, now=JOINED)
        assert grant_partner(db, user, now=JOINED + timedelta(days=10)) == {"stripe_paused": 0}
    assert len(fake.modified) == 1


def test_removing_partner_resumes_only_the_billing_we_paused(db, monkeypatch):
    user, fake = _stripe_customer(db, monkeypatch, [
        {"id": "sub_ours", "status": "active", "metadata": {"paused_for": "partner_premium"},
         "pause_collection": {"behavior": "void"}},
        {"id": "sub_other_pause", "status": "active", "metadata": {}, "pause_collection": {"behavior": "void"}},
    ])
    # A partner whose subscription we paused when they joined.
    user.is_partner, user.partner_since = True, JOINED
    user.partner_premium_until = datetime(2027, 5, 9, 10, tzinfo=UTC)
    db.flush()
    with patch.object(stripe.Subscription, "list", side_effect=fake.list), \
         patch.object(stripe.Subscription, "modify", side_effect=fake.modify):
        assert revoke_partner(db, user) == {"stripe_resumed": 1}
    assert fake.modified == [("sub_ours", {"pause_collection": "", "metadata": {"paused_for": ""},
                                           "api_key": "sk_test_fake"})]


def test_a_stripe_error_does_not_stop_someone_becoming_a_partner(db, monkeypatch):
    user, _ = _stripe_customer(db, monkeypatch, [])
    with patch.object(stripe.Subscription, "list", side_effect=stripe.error.APIConnectionError("down")):
        assert grant_partner(db, user, now=JOINED) == {"stripe_paused": 0}
    assert user.is_partner is True


def test_admin_permissions_list_shows_a_partner_as_premium(db):
    """The admin Subscription column reads plan_tier: a partner on free
    Premium is 'premium', not the 'Pro' every active user used to show."""
    import asyncio

    from api.routes.admin.permissions import get_users_for_permissions
    partner = _partner(db, name="Listed Partner")
    listing = asyncio.run(get_users_for_permissions(limit=10, page=1, search=partner.email, role="",
                                                    current_user=None, db=db))
    row = listing["users"][0]
    assert row["subscription_status"] == "active" and row["plan_tier"] == "premium"
