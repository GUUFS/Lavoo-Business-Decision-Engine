"""
Premium forever (subscriptions/lifetime_premium.py): the account stays
active Premium with no payment and no end date, is skipped by the expiry
job and the beta charge, and an email on LIFETIME_PREMIUM_EMAILS gets the
flag the first time the status sync sees it.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from api.utils.sub_utils import sync_user_subscription
from database.pg_models import Subscriptions, User
from decision_engine.checkup_limits import user_plan_tier
from subscriptions.lifetime_premium import (
    grant_lifetime_premium,
    lifetime_premium_active,
    lifetime_premium_user_ids,
)


def _user(db, email, status="Free"):
    """A user with no payments."""
    # 1. Minimal account.
    user = User(name="Member", email=email, password="x", confirm_password="x", subscription_status=status)
    db.add(user)
    db.flush()
    return user


def test_named_email_is_premium_forever_on_first_sync(db):
    # 1. The owner's account, free, no payments (any letter case).
    user = _user(db, "TeamHolyHustle@gmail.com")
    # 2. The status sync would normally leave a non-payer on Free.
    sync_user_subscription(db, user)
    # 3. It is now flagged, active, on the lifetime plan, with no end date.
    assert user.lifetime_premium is True
    assert user.subscription_status == "active"
    assert user.subscription_plan == "lifetime"
    assert user.subscription_expires_at is None
    assert user_plan_tier(db, user) == "premium"
    assert user.id in lifetime_premium_user_ids(db)


def test_granted_account_stays_active_when_an_old_payment_has_expired(db):
    # 1. An account whose last payment ended a year ago.
    user = _user(db, "lifetime-granted@test.local", status="active")
    past = datetime.now(UTC) - timedelta(days=400)
    db.add(Subscriptions(user_id=user.id, subscription_plan="monthly", plan_tier="pro", transaction_id="tx-life",
                         tx_ref="ref-life", amount=Decimal("9"), currency="USD", status="completed",
                         subscription_status="active", payment_provider="stripe", start_date=past,
                         end_date=past + timedelta(days=30)))
    db.flush()
    # 2. Made Premium forever.
    grant_lifetime_premium(db, user)
    # 3. The sync doesn't move it to Free, and checkups are Premium.
    sync_user_subscription(db, user)
    assert user.subscription_status == "active"
    assert user_plan_tier(db, user) == "premium"


def test_other_accounts_are_not_lifetime(db):
    # 1. An ordinary free account.
    user = _user(db, "someone-else@test.local")
    # 2. Not lifetime, not in the expiry job's skip list, stays Free.
    assert not lifetime_premium_active(user)
    assert user.id not in lifetime_premium_user_ids(db)
    sync_user_subscription(db, user)
    assert user.subscription_status == "Free"
