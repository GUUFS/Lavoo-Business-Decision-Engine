"""
Tests for the Builder Bonus referral rules in subscriptions/commission_service.py
(CommissionService._eligibility_for_payment), run against real Postgres.

Rules checked:
  - Pro referrer earns 25%, Premium 40%, on the referral's payments until
    the referral has paid for 6 months of subscription (6 monthly / 2
    quarterly). Months the referral wasn't subscribed don't count.
  - A yearly referral pays its referrer once; nothing after it pays.
  - A free referrer earns 10% of the referral's first payment only.
  - A referrer who isn't actively subscribed (status not active/canceling,
    or paid period over) is treated as free; one who cancelled at period end
    but is still paid up keeps their rate.
"""
import itertools
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from database.pg_models import Subscriptions, User
from calendar import monthrange

from subscriptions.commission_service import CommissionService

def _add_months(dt, months):
    """Same day `months` later, clamped to the month's last day."""
    years, month_index = divmod(dt.month - 1 + months, 12)
    year, month = dt.year + years, month_index + 1
    return dt.replace(year=year, month=month, day=min(dt.day, monthrange(year, month)[1]))


NOW = datetime(2026, 11, 5, tzinfo=UTC)
_ids = itertools.count(1)


def make_referrer(db, status="active", tier="pro", expires=NOW + timedelta(days=400)):
    """Create a referrer. Active/canceling ones also get their own paid
    subscription row, which is where their Pro/Premium tier is read from."""
    n = next(_ids)
    user = User(name=f"Referrer {n}", email=f"referrer{n}@test.local", password="x", confirm_password="x",
                subscription_status=status, subscription_expires_at=expires)
    db.add(user)
    db.flush()
    if status in ("active", "canceling"):
        add_payment(db, user.id, NOW - timedelta(days=5), "monthly", tier=tier, sub_status=status)
    return user


def make_referral(db):
    """Create the referred user and return their id."""
    n = next(_ids)
    user = User(name=f"Referral {n}", email=f"referral{n}@test.local", password="x", confirm_password="x")
    db.add(user)
    db.flush()
    return user.id


def add_payment(db, user_id, when, period, tier="pro", sub_status="active"):
    """Record one successful subscription payment for `user_id` at `when`."""
    n = next(_ids)
    sub = Subscriptions(
        user_id=user_id, subscription_plan=period, plan_tier=tier, transaction_id=f"tx{n}", tx_ref=f"ref{n}",
        amount=Decimal("9.00"), currency="USD", status="completed", subscription_status=sub_status,
        payment_provider="stripe", created_at=when, start_date=when, end_date=when + timedelta(days=30),
    )
    db.add(sub)
    db.flush()
    return sub


def pay(db, referrer, referral_id, when, period):
    """Record the referral's payment and return (eligible, rate) for it,
    exactly as calculate_commission would see it."""
    sub = add_payment(db, referral_id, when, period)
    return CommissionService._eligibility_for_payment(
        referrer.id, False, referral_id, period, when, db, exclude_subscription_id=sub.id
    )


def monthly_dates(start, count):
    """`count` monthly billing dates starting at `start` (calendar months)."""
    return [_add_months(start, i) for i in range(count)]


def test_pro_monthly_earns_25_percent_for_six_payments_only(db):
    referrer, referral = make_referrer(db), make_referral(db)
    results = [pay(db, referrer, referral, t, "monthly")
               for t in monthly_dates(datetime(2027, 1, 31, 10, tzinfo=UTC), 8)]
    assert [eligible for eligible, _ in results] == [True] * 6 + [False] * 2
    assert results[0][1] == Decimal("0.25")


def test_seventh_monthly_payment_charged_early_does_not_earn(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 3, 15, tzinfo=UTC)
    for t in monthly_dates(start, 6):
        pay(db, referrer, referral, t, "monthly")
    eligible, _ = pay(db, referrer, referral, _add_months(start, 6) - timedelta(days=2), "monthly")
    assert eligible is False


def test_pro_quarterly_earns_two_payments_only(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 31, tzinfo=UTC)
    dates = [start, _add_months(start, 3), _add_months(start, 6)]
    assert [pay(db, referrer, referral, t, "quarterly")[0] for t in dates] == [True, True, False]


def test_yearly_referral_earns_once(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 2, 10, tzinfo=UTC)
    assert pay(db, referrer, referral, start, "yearly")[0] is True
    assert pay(db, referrer, referral, _add_months(start, 12), "yearly")[0] is False


def test_switch_to_yearly_inside_window_earns_once(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 1, tzinfo=UTC)
    pay(db, referrer, referral, start, "monthly")
    pay(db, referrer, referral, _add_months(start, 1), "monthly")
    assert pay(db, referrer, referral, _add_months(start, 2), "yearly")[0] is True
    assert pay(db, referrer, referral, _add_months(start, 4), "yearly")[0] is False


def test_switch_to_yearly_after_window_does_not_earn(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 1, tzinfo=UTC)
    for t in monthly_dates(start, 7):
        pay(db, referrer, referral, t, "monthly")
    assert pay(db, referrer, referral, _add_months(start, 7), "yearly")[0] is False


def test_premium_referrer_earns_40_percent(db):
    referrer, referral = make_referrer(db, tier="premium"), make_referral(db)
    assert pay(db, referrer, referral, NOW, "monthly") == (True, Decimal("0.40"))


@pytest.mark.parametrize("period", ["monthly", "yearly"])
def test_free_referrer_earns_10_percent_of_first_payment_only(db, period):
    referrer, referral = make_referrer(db, status="Free"), make_referral(db)
    assert pay(db, referrer, referral, NOW, period) == (True, Decimal("0.10"))
    assert pay(db, referrer, referral, _add_months(NOW, 1), "monthly")[0] is False


def test_referrer_whose_paid_period_ended_is_treated_as_free(db):
    referrer, referral = make_referrer(db, expires=NOW - timedelta(days=10)), make_referral(db)
    assert pay(db, referrer, referral, NOW, "monthly") == (True, Decimal("0.10"))
    assert pay(db, referrer, referral, NOW + timedelta(days=31), "monthly")[0] is False


def test_canceling_but_still_paid_referrer_keeps_pro_rate(db):
    referrer = make_referrer(db, status="canceling", expires=NOW + timedelta(days=20))
    assert pay(db, referrer, make_referral(db), NOW, "monthly") == (True, Decimal("0.25"))


def test_referrer_who_lapses_stops_earning(db):
    referrer, referral = make_referrer(db), make_referral(db)
    assert pay(db, referrer, referral, NOW, "monthly") == (True, Decimal("0.25"))
    referrer.subscription_status = "Free"
    db.flush()
    assert pay(db, referrer, referral, _add_months(NOW, 1), "monthly")[0] is False


def test_staff_pool_signup_earns_flat_30_percent(db):
    staff, referral = make_referrer(db, status="Free"), make_referral(db)
    sub = add_payment(db, referral, NOW, "monthly")
    assert CommissionService._eligibility_for_payment(
        staff.id, True, referral, "monthly", NOW, db, exclude_subscription_id=sub.id
    ) == (True, Decimal("0.30"))


def test_months_not_subscribed_do_not_count(db):
    """3 monthly payments, a 4-month break, then they come back: the first
    3 payments after the break still earn (3 + 3 = 6), the next doesn't."""
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    before_break = [pay(db, referrer, referral, t, "monthly")[0] for t in monthly_dates(start, 3)]
    after_break = [pay(db, referrer, referral, t, "monthly")[0]
                   for t in monthly_dates(_add_months(start, 7), 4)]
    assert before_break == [True, True, True]
    assert after_break == [True, True, True, False]


def test_long_break_still_earns_remaining_months(db):
    """2 monthly payments, then a quarterly one more than a year later: it
    earns, because only 2 months had been paid before it."""
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    for t in monthly_dates(start, 2):
        pay(db, referrer, referral, t, "monthly")
    assert pay(db, referrer, referral, _add_months(start, 14), "quarterly")[0] is True
    assert pay(db, referrer, referral, _add_months(start, 17), "quarterly")[0] is False


def test_yearly_after_six_paid_months_does_not_earn(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    for t in monthly_dates(start, 6):
        pay(db, referrer, referral, t, "monthly")
    assert pay(db, referrer, referral, _add_months(start, 6), "yearly")[0] is False
