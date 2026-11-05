"""
The admin dashboard's Total Revenue card must show the same numbers as the
Revenue page's "Subscription Revenue" (api/routes/admin/dashboard.py and
api/routes/admin/revenue.py).

Reproduces the case that showed a negative NGN total: a USD builder bonus
paid out in NGN through Flutterwave was being subtracted from NGN revenue.
"""
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from api.routes.admin.dashboard import get_dashboard_stats
from api.routes.admin.revenue import compute_revenue_stats
from database.pg_models import Commission, Payout, Subscriptions, User


def _user(db, n):
    """A plain user to attach payments to."""
    user = User(name=f"Rev {n}", email=f"rev{n}@test.local", password="x", confirm_password="x")
    db.add(user)
    db.flush()
    return user


def _payment(db, user, amount, currency, ref):
    """One successful subscription payment."""
    now = datetime.now(UTC)
    sub = Subscriptions(
        user_id=user.id, subscription_plan="monthly", plan_tier="pro", transaction_id=f"rev-{ref}",
        tx_ref=f"rev-{ref}", amount=Decimal(amount), currency=currency, status="completed",
        subscription_status="active", payment_provider="stripe" if currency != "NGN" else "flutterwave",
        start_date=now, end_date=now + timedelta(days=30),
    )
    db.add(sub)
    db.flush()
    return sub


def _dashboard_totals(db):
    """What the dashboard's Total Revenue card shows, per currency."""
    return asyncio.run(get_dashboard_stats(current_user=None, db=db))["total_revenue_by_currency"]


def test_dashboard_total_revenue_matches_revenue_page(db):
    before = _dashboard_totals(db)
    referrer, payer_usd, payer_ngn = _user(db, 1), _user(db, 2), _user(db, 3)

    # A $100 payment earns the referrer a $25 bonus, paid out as NGN 37,500.
    usd_sub = _payment(db, payer_usd, "100.00", "USD", "usd1")
    payout = Payout(user_id=referrer.id, amount=Decimal("37500.00"), currency="NGN", status="completed",
                    provider="flutterwave", payment_method="flutterwave",
                    original_currency="USD", original_amount=Decimal("25.00"))
    db.add(payout)
    db.flush()
    db.add(Commission(user_id=referrer.id, referred_user_id=payer_usd.id, subscription_id=usd_sub.id,
                      amount=Decimal("25.00"), original_amount=Decimal("100.00"), currency="USD",
                      commission_rate=Decimal("25"), status="auto_settled", payout_id=payout.id))
    # An unrelated NGN 1,000 payment with no referrer.
    _payment(db, payer_ngn, "1000.00", "NGN", "ngn1")
    db.flush()

    dashboard = _dashboard_totals(db)
    revenue_page = compute_revenue_stats(db)["by_currency"]

    # Same numbers on both pages, for every currency.
    assert dashboard == {ccy: v["total_subscription_revenue"] for ccy, v in revenue_page.items()}
    # NGN is +1,000 (the NGN payment), not -36,500 (1,000 minus the NGN payout).
    assert dashboard["NGN"] - before.get("NGN", 0.0) == 1000.0
    # USD is $100 paid minus the $25 bonus owed on it.
    assert dashboard["USD"] - before.get("USD", 0.0) == 75.0
