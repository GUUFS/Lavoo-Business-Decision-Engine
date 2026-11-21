"""
Days remaining in the admin user details (api/routes/admin/users.py access_left).

It used to read the user's OLDEST payment, whose end date is in the past
for anyone who renewed, so it showed 0 days. It now takes whichever access
ends last: the newest paid plan, Partner Premium or the free trial; and
Premium forever has no end.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from api.routes.admin.users import access_left
from database.pg_models import Subscriptions, User

NOW = datetime.now(UTC)


def _user(db, email, **fields):
    """A saved user with the given fields."""
    user = User(name="Days", email=email, password="x", confirm_password="x", **fields)
    db.add(user)
    db.flush()
    return user


def _payment(db, user, start_days_ago, end_in_days, ref):
    """One completed payment covering start_days_ago .. end_in_days from now."""
    db.add(Subscriptions(user_id=user.id, subscription_plan="monthly", transaction_id=ref, tx_ref=ref,
                         amount=Decimal("9.00"), currency="USD", status="completed",
                         subscription_status="active", payment_provider="stripe",
                         start_date=NOW - timedelta(days=start_days_ago),
                         end_date=NOW + timedelta(days=end_in_days)))
    db.flush()


def test_a_renewed_user_counts_from_the_newest_payment(db):
    user = _user(db, "renewed@test.local", subscription_status="active")
    _payment(db, user, 60, -30, "days-old")     # the first month, long over
    _payment(db, user, 5, 25, "days-new")       # the renewal
    access = access_left(db, user)
    assert access["days_remaining"] in (24, 25) and access["access_type"] == "Paid plan"
    assert access["access_ends_at"].endswith("Z")


def test_partner_and_trial_days_count(db):
    partner = _user(db, "partner-days@test.local", partner_premium_until=NOW + timedelta(days=90, hours=1))
    assert access_left(db, partner) | {"access_ends_at": None} == \
        {"days_remaining": 90, "access_type": "Partner", "access_ends_at": None}
    trial = _user(db, "trial-days@test.local", grace_period_ends_at=NOW + timedelta(days=3, hours=1))
    assert access_left(db, trial)["days_remaining"] == 3
    assert access_left(db, trial)["access_type"] == "Free trial"


def test_premium_forever_and_nothing_left(db):
    forever = _user(db, "forever-days@test.local", lifetime_premium=True)
    assert access_left(db, forever)["days_remaining"] is None
    assert access_left(db, forever)["access_type"] == "Premium forever"
    lapsed = _user(db, "lapsed-days@test.local", subscription_expires_at=NOW - timedelta(days=2))
    assert access_left(db, lapsed)["days_remaining"] == 0 and access_left(db, lapsed)["access_type"] is None
