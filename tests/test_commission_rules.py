"""
Tests for the Builder Bonus referral rules in subscriptions/commission_service.py
(CommissionService._eligibility_for_payment), run against real Postgres.

Rules checked:
  - Pro referrer earns 25%, Premium 40%, on the referral's payments until
    the referral has paid for 6 months of subscription (6 monthly / 2
    quarterly).
  - A referrer on a YEARLY plan: months the referral wasn't subscribed don't
    count (paid month 1, missed month 2: 1 used, 5 left).
  - A referrer on a MONTHLY or QUARTERLY plan: a straight count of 6
    calendar months from the referral's first payment (paid month 1, missed
    month 2: 1 earned, 4 left).
  - A yearly referral pays its referrer once; nothing after it pays.
  - A free referrer earns 10% of the referral's first payment only.
  - A referrer who isn't actively subscribed (status not active/canceling,
    or paid period over) is treated as free; one who cancelled at period end
    but is still paid up keeps their rate.
"""
import itertools
from calendar import monthrange
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from database.pg_models import Subscriptions, User
from subscriptions.commission_service import CommissionService


def _add_months(dt, months):
    """Same day `months` later, clamped to the month's last day."""
    years, month_index = divmod(dt.month - 1 + months, 12)
    year, month = dt.year + years, month_index + 1
    return dt.replace(year=year, month=month, day=min(dt.day, monthrange(year, month)[1]))


NOW = datetime(2026, 11, 5, tzinfo=UTC)
_ids = itertools.count(1)


def make_referrer(db, status="active", tier="pro", expires=NOW + timedelta(days=400), period="monthly"):
    """Create a referrer. Active/canceling ones also get their own paid
    subscription row, which is where their Pro/Premium tier and their own
    billing period (`period`: monthly/quarterly/yearly) are read from."""
    n = next(_ids)
    user = User(name=f"Referrer {n}", email=f"referrer{n}@test.local", password="x", confirm_password="x",
                subscription_status=status, subscription_expires_at=expires)
    db.add(user)
    db.flush()
    if status in ("active", "canceling"):
        add_payment(db, user.id, NOW - timedelta(days=5), period, tier=tier, sub_status=status)
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


def test_yearly_referrer_months_not_subscribed_do_not_count(db):
    """Referrer on a yearly plan. 3 monthly payments, a 4-month break, then
    they come back: the first 3 payments after the break still earn
    (3 + 3 = 6), the next doesn't."""
    referrer, referral = make_referrer(db, period="yearly"), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    before_break = [pay(db, referrer, referral, t, "monthly")[0] for t in monthly_dates(start, 3)]
    after_break = [pay(db, referrer, referral, t, "monthly")[0]
                   for t in monthly_dates(_add_months(start, 7), 4)]
    assert before_break == [True, True, True]
    assert after_break == [True, True, True, False]


def test_yearly_referrer_long_break_still_earns_remaining_months(db):
    """Referrer on a yearly plan. 2 monthly payments, then quarterly ones
    after a break of more than a year. The 1st quarterly earns (2 months
    paid before it) and so does the 2nd (2 + 3 = 5, still under 6); the 3rd
    doesn't (5 + 3 = 8). The referrer stays subscribed throughout."""
    referrer = make_referrer(db, expires=datetime(2030, 1, 1, tzinfo=UTC), period="yearly")
    referral = make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    for t in monthly_dates(start, 2):
        pay(db, referrer, referral, t, "monthly")
    assert pay(db, referrer, referral, _add_months(start, 14), "quarterly")[0] is True
    assert pay(db, referrer, referral, _add_months(start, 17), "quarterly")[0] is True
    assert pay(db, referrer, referral, _add_months(start, 20), "quarterly")[0] is False


def test_yearly_after_six_paid_months_does_not_earn(db):
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    for t in monthly_dates(start, 6):
        pay(db, referrer, referral, t, "monthly")
    assert pay(db, referrer, referral, _add_months(start, 6), "yearly")[0] is False


# ── Straight count vs paid-month count (the referrer's own billing period) ──

def _paid_month_one_missed_month_two(db, referrer_period):
    """The example from the rule: the referral pays month 1, misses month 2,
    then pays every month from month 3 on. Returns which payments earn."""
    referrer, referral = make_referrer(db, period=referrer_period), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    first = pay(db, referrer, referral, start, "monthly")[0]
    later = [pay(db, referrer, referral, t, "monthly")[0]
             for t in [_add_months(start, m) for m in range(2, 9)]]   # months 3 to 9
    return first, later


@pytest.mark.parametrize("referrer_period", ["monthly", "quarterly"])
def test_monthly_or_quarterly_referrer_loses_the_missed_month(db, referrer_period):
    """Straight count: 1 earned, month 2 lost, 4 left (months 3-6), so 5 in all."""
    first, later = _paid_month_one_missed_month_two(db, referrer_period)
    assert first is True
    assert later == [True, True, True, True, False, False, False]


def test_yearly_referrer_keeps_the_missed_month(db):
    """Paid-month count: 1 used, 5 left, so 6 in all (months 1 and 3-7)."""
    first, later = _paid_month_one_missed_month_two(db, "yearly")
    assert first is True
    assert later == [True, True, True, True, True, False, False]


def test_monthly_referrer_window_closes_after_six_calendar_months(db):
    """A referral who pays twice, stops, and comes back after the window
    has closed earns nothing more for a monthly-plan referrer."""
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    assert [pay(db, referrer, referral, t, "monthly")[0] for t in monthly_dates(start, 2)] == [True, True]
    assert pay(db, referrer, referral, _add_months(start, 6), "monthly")[0] is False


def test_last_day_inside_the_window_still_earns(db):
    """The window is 6 calendar months from the first payment: the day
    before it ends still earns, the moment it ends doesn't."""
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 31, 12, tzinfo=UTC)
    pay(db, referrer, referral, start, "monthly")
    end = _add_months(start, 6)                              # 31 July 2027, 12:00
    assert pay(db, referrer, referral, end - timedelta(days=1), "monthly")[0] is True
    assert pay(db, referrer, referral, end, "monthly")[0] is False


def test_referrer_who_moves_to_yearly_gets_paid_month_counting(db):
    """The counting follows the referrer's plan on the day each payment
    clears: after moving to yearly, the referral's missed months stop
    being lost."""
    referrer, referral = make_referrer(db), make_referral(db)
    start = datetime(2027, 1, 10, tzinfo=UTC)
    pay(db, referrer, referral, start, "monthly")
    late = _add_months(start, 7)
    assert pay(db, referrer, referral, late, "monthly")[0] is False      # monthly plan: window closed
    add_payment(db, referrer.id, NOW, "yearly")                          # referrer switches to yearly
    assert pay(db, referrer, referral, _add_months(start, 8), "monthly")[0] is True


def test_partner_without_a_yearly_plan_gets_the_straight_count(db):
    partner, referral = make_referrer(db, status="Free"), make_referral(db)
    partner.is_partner = True
    db.flush()
    start = datetime(2027, 1, 10, tzinfo=UTC)
    assert pay(db, partner, referral, start, "monthly") == (True, Decimal("0.50"))
    assert pay(db, partner, referral, _add_months(start, 6), "monthly")[0] is False
