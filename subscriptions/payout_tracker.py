"""
Payout Tracker: what the payout system did with every payment.

WHY THIS EXISTS
  A commission that couldn't be paid used to leave no trace: the payout
  code stopped quietly (for example "not enough money in the Flutterwave
  wallet") and the Revenue page could only say "never attempted". Now
  every try is recorded in plain words, and the admin can see for each
  payment:
    - was a commission due, and to whom
    - which route pays it: Flutterwave (bank account in Nigeria) or Stripe
    - is it CROSS-BORDER: earned in one currency, paid in another
      (e.g. a £ payment, paid to the referrer in ₦ through Flutterwave)
    - what happened: sent, waiting for money, account not ready, ...
    - why, with the numbers (amount needed, wallet balance, exchange rate)

HOW IT IS RECORDED (two steps)
  1. note():  the payout code (commission_service.py) calls this at the
              moment it knows the outcome. It is only kept in memory,
              because the caller may roll the database back right after
              (settle_pending_commission rolls back when nothing was sent).
  2. save():  the caller calls this AFTER its commit or rollback, so the
              record survives either way.
  The same outcome again (e.g. "waiting for money" on every 10-minute
  retry) adds 1 to `tries` on the same row instead of adding a new row.

WHERE IT IS SHOWN
  - Admin Payout Tracker page (api/routes/admin/payout_tracker.py)
  - Revenue page health check: unpaid_commission_checks() below gives the
    real reason instead of "never attempted".
"""
import contextlib
import logging
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from database.pg_models import (
    Commission,
    CommissionPayoutAttempt,
    Payout,
    PayoutAccount,
    Referral,
    Subscriptions,
    User,
)

logger = logging.getLogger(__name__)

# Plain-words labels for each outcome (also used by the admin page).
OUTCOME_LABELS = {
    "sent": "Sent",
    "waiting_for_money": "Waiting for money",
    "no_payout_account": "Referrer has nowhere to receive it",
    "account_not_ready": "Referrer's account not ready",
    "rate_unavailable": "Exchange rate unavailable",
    "too_small": "Too small to send",
    "needs_review": "Needs a person to decide",
    "could_not_check": "Couldn't check the provider",
    "failed": "Transfer failed",
}

# Outcomes that fix themselves: the 10-minute jobs keep retrying them.
SELF_FIXING = {"waiting_for_money", "rate_unavailable", "could_not_check", "failed"}

_SYMBOLS = {"GBP": "£", "USD": "$", "NGN": "₦", "EUR": "€"}

# Outcomes noted but not saved yet, by commission id (see step 1 above).
_notes: dict[int, dict] = {}
_notes_lock = threading.Lock()


def money(amount, currency: str | None) -> str:
    """'£3.50', '₦6,825.00' or '12.00 CAD'."""
    if amount is None:
        return "?"
    code = (currency or "").upper()
    value = f"{Decimal(str(amount)):,.2f}"
    return f"{_SYMBOLS[code]}{value}" if code in _SYMBOLS else f"{value} {code}".strip()


def route_text(route: str | None, cross_border: bool, from_currency: str | None, to_currency: str | None) -> str:
    """'Flutterwave, cross-border (GBP → NGN)' or 'Stripe (GBP)'."""
    if not route:
        return "No route"
    name = "Flutterwave" if route == "flutterwave" else "Stripe"
    if cross_border:
        return f"{name}, cross-border ({from_currency} → {to_currency})"
    return f"{name} ({to_currency or from_currency})"


# ------------------------------------------------------------ recording

def note(commission: Commission, outcome: str, reason: str, *, route: str | None = None,
         to_currency: str | None = None, converted_amount=None, fx_rate=None,
         balance_available=None, payout_id: int | None = None) -> None:
    """Step 1: remember what just happened to this commission (in memory only).
    Never raises: tracking must never break a real payout."""
    try:
        from_currency = (commission.currency or "USD").upper()
        to_ccy = (to_currency or "").upper() or None
        with _notes_lock:
            _notes[int(commission.id)] = {
                "outcome": outcome, "reason": reason, "route": route,
                "cross_border": bool(to_ccy and to_ccy != from_currency),
                "from_currency": from_currency, "to_currency": to_ccy,
                "amount": Decimal(str(commission.amount)) if commission.amount is not None else None,
                "converted_amount": converted_amount, "fx_rate": fx_rate,
                "balance_available": balance_available, "payout_id": payout_id,
            }
    except Exception as e:
        logger.warning(f"[payout-tracker] could not note commission outcome: {e}")


def save(db: Session, commission_id: int, commit: bool = True) -> None:
    """Step 2: write the noted outcome to the database. Call it after the
    caller's own commit or rollback. Never raises.

    commit=False: only add it to the caller's open transaction (used when a
    commission is being created, so it is saved together with it)."""
    # 1. Take the note; nothing noted means nothing to save.
    with _notes_lock:
        data = _notes.pop(int(commission_id), None)
    if not data:
        return
    try:
        # 2. Inside a savepoint, so a failure here can't undo the caller's work.
        with db.begin_nested():
            now = datetime.now(UTC)
            latest = (db.query(CommissionPayoutAttempt)
                      .filter(CommissionPayoutAttempt.commission_id == commission_id)
                      .order_by(CommissionPayoutAttempt.id.desc()).first())
            # 3. Same outcome on the same route as last time: count it on that row.
            if latest and latest.outcome == data["outcome"] and latest.route == data["route"]:
                latest.tries = (latest.tries or 1) + 1
                latest.last_tried_at = now
                for key in ("reason", "to_currency", "cross_border", "converted_amount", "fx_rate",
                            "balance_available", "payout_id"):
                    if data[key] is not None:
                        setattr(latest, key, data[key])
            # 4. Something new happened: add a row.
            else:
                db.add(CommissionPayoutAttempt(commission_id=commission_id, first_tried_at=now,
                                               last_tried_at=now, tries=1, **data))
        # 5. Commit now, or leave it to the caller's own commit.
        if commit:
            db.commit()
    except Exception as e:
        # The savepoint already undid this write; the caller's work is untouched.
        logger.warning(f"[payout-tracker] could not save outcome for commission {commission_id}: {e}")
        # A failed commit leaves the session unusable until it is rolled back.
        if commit:
            with contextlib.suppress(Exception):
                db.rollback()


# ------------------------------------------------------------ reading

def why_account_cannot_be_paid(account: PayoutAccount | None) -> str | None:
    """Why no automatic route can pay this referrer, or None if one can."""
    if account is None:
        return "The referrer hasn't added a payout account."
    has_bank = bool(account.payment_method == "flutterwave" and account.bank_name
                    and account.account_number and account.bank_code)
    if has_bank:
        return None
    if account.stripe_account_id and account.is_verified:
        return None
    if account.stripe_account_id:
        return "The referrer's Stripe account isn't verified yet, and there is no Flutterwave bank account."
    return "The referrer's payout account has no complete bank details and no Stripe account."


def _attempt_view(a: CommissionPayoutAttempt) -> dict:
    """One attempt row for the admin page."""
    return {
        "id": a.id, "outcome": a.outcome, "label": OUTCOME_LABELS.get(a.outcome, a.outcome),
        "reason": a.reason, "route": a.route, "cross_border": bool(a.cross_border),
        "route_text": route_text(a.route, bool(a.cross_border), a.from_currency, a.to_currency),
        "from_currency": a.from_currency, "to_currency": a.to_currency,
        "amount": float(a.amount) if a.amount is not None else None,
        "converted_amount": float(a.converted_amount) if a.converted_amount is not None else None,
        "fx_rate": float(a.fx_rate) if a.fx_rate is not None else None,
        "balance_available": float(a.balance_available) if a.balance_available is not None else None,
        "payout_id": a.payout_id, "tries": a.tries,
        "first_tried_at": a.first_tried_at.isoformat() if a.first_tried_at else None,
        "last_tried_at": a.last_tried_at.isoformat() if a.last_tried_at else None,
        "self_fixing": a.outcome in SELF_FIXING,
    }


def _latest_by_commission(db: Session, commission_ids: list[int]) -> dict[int, CommissionPayoutAttempt]:
    """The most recent attempt for each commission id."""
    if not commission_ids:
        return {}
    rows = (db.query(CommissionPayoutAttempt)
            .filter(CommissionPayoutAttempt.commission_id.in_(commission_ids))
            .order_by(CommissionPayoutAttempt.commission_id, CommissionPayoutAttempt.id).all())
    latest = {}
    for row in rows:
        latest[row.commission_id] = row  # later rows overwrite earlier ones
    return latest


def _commission_story(c: Commission, latest: CommissionPayoutAttempt | None,
                      payout: Payout | None, account: PayoutAccount | None) -> dict:
    """What happened to one commission, in plain words."""
    # 1. Paid at the moment of payment by a Flutterwave split (no transfer needed).
    if c.status == "auto_settled" and not c.payout_id and not latest:
        state, reason = "sent", "Paid at the moment of payment: Flutterwave split the money straight to the referrer."
    # 2. A payout exists: report its real status.
    elif payout is not None:
        state = {"completed": "sent", "processing": "sent", "pending": "sent", "failed": "failed"}.get(payout.status, payout.status)
        reason = {
            "completed": "Sent and confirmed by the provider.",
            "processing": "Handed to the provider; waiting for its confirmation.",
            "pending": "Being sent now.",
            "failed": f"The transfer failed: {payout.failure_reason or 'no reason given'}. It is retried automatically.",
        }.get(payout.status, f"Payout status: {payout.status}")
        if latest and latest.outcome != "sent" and payout.status == "failed":
            reason = latest.reason
    # 3. Reversed, clawed back or otherwise closed.
    elif c.status in ("reversed", "clawed_back", "cancelled"):
        state, reason = c.status, {"reversed": "Cancelled because the payment was refunded or disputed.",
                                   "clawed_back": "Already paid, then the payment was refunded: the referrer owes it back.",
                                   }.get(c.status, f"Commission {c.status}.")
    # 4. Not paid, and the system recorded why.
    elif latest:
        state, reason = latest.outcome, latest.reason
    # 5. Not paid, nothing recorded yet: work out why from the account.
    else:
        problem = why_account_cannot_be_paid(account)
        state = "no_payout_account" if problem else "not_tried_yet"
        reason = problem or "Not tried yet. The payout jobs run every 10 minutes and will try it."
    return {
        "id": c.id, "amount": float(c.amount), "currency": c.currency, "status": c.status,
        "rate": float(c.commission_rate) if c.commission_rate is not None else None,
        "referrer_id": c.user_id, "state": state, "state_label": OUTCOME_LABELS.get(state, state.replace("_", " ")),
        "reason": reason,
        "route_text": route_text(latest.route, bool(latest.cross_border), latest.from_currency, latest.to_currency)
        if latest else (route_text(payout.provider, bool(payout.original_currency), payout.original_currency, payout.currency)
                        if payout else None),
        "cross_border": bool(latest.cross_border) if latest else bool(payout and payout.original_currency),
        "tries": latest.tries if latest else 0,
        "last_tried_at": latest.last_tried_at.isoformat() if latest and latest.last_tried_at else None,
        "payout": {"id": payout.id, "status": payout.status, "amount": float(payout.amount), "currency": payout.currency,
                   "provider": payout.provider, "reference": payout.provider_payout_id,
                   "failure_reason": payout.failure_reason} if payout else None,
    }


def tracker_rows(db: Session, limit: int = 50, show: str = "all") -> list[dict]:
    """Every recent payment and what the payout system did with it.

    show: 'all' | 'with_commission' | 'unpaid' (commission due but not sent)."""
    # 1. Recent completed payments, newest first.
    query = db.query(Subscriptions).filter(Subscriptions.status.in_(["completed", "successful", "refunded"]))
    if show in ("with_commission", "unpaid"):
        query = query.filter(Subscriptions.id.in_(db.query(Commission.subscription_id)))
    payments = query.order_by(Subscriptions.created_at.desc()).limit(max(1, min(limit, 200)) * (3 if show == "unpaid" else 1)).all()

    # 2. Load everything for those payments in a few queries (not one per row).
    sub_ids = [p.id for p in payments]
    commissions = db.query(Commission).filter(Commission.subscription_id.in_(sub_ids)).all() if sub_ids else []
    by_sub: dict[int, list[Commission]] = {}
    for c in commissions:
        by_sub.setdefault(c.subscription_id, []).append(c)
    latest = _latest_by_commission(db, [c.id for c in commissions])
    payout_ids = [c.payout_id for c in commissions if c.payout_id]
    payouts = {p.id: p for p in db.query(Payout).filter(Payout.id.in_(payout_ids)).all()} if payout_ids else {}
    user_ids = {p.user_id for p in payments} | {c.user_id for c in commissions}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    accounts = {a.user_id: a for a in db.query(PayoutAccount).filter(
        PayoutAccount.user_id.in_({c.user_id for c in commissions})).all()} if commissions else {}
    referred = {r.referred_user_id for r in db.query(Referral.referred_user_id).filter(
        Referral.referred_user_id.in_({p.user_id for p in payments})).all()} if payments else set()

    # 3. One row per payment.
    rows = []
    for p in payments:
        payer = users.get(p.user_id)
        stories = []
        for c in by_sub.get(p.id, []):
            story = _commission_story(c, latest.get(c.id), payouts.get(c.payout_id), accounts.get(c.user_id))
            referrer = users.get(c.user_id)
            story["referrer"] = {"id": referrer.id, "name": referrer.name, "email": referrer.email} if referrer else None
            stories.append(story)
        # 4. No commission: say why in plain words.
        if not stories:
            no_commission = ("The payer has a referrer, but no commission was due on this payment (outside the "
                             "6-month window, the one-time rule, or the referrer isn't subscribed)."
                             if p.user_id in referred else "No referrer, so there is nothing to pay out.")
        else:
            no_commission = None
        row = {
            "payment_id": p.id, "created_at": p.created_at.isoformat() if p.created_at else None,
            "amount": float(p.amount), "currency": p.currency, "provider": p.payment_provider, "status": p.status,
            "plan": p.subscription_plan, "plan_tier": p.plan_tier,
            "payer": {"id": payer.id, "name": payer.name, "email": payer.email} if payer else None,
            "commissions": stories, "no_commission": no_commission,
        }
        # 5. 'unpaid' keeps only payments with a commission still owed.
        if show == "unpaid" and not any(s["status"] == "pending" and s["state"] != "sent" for s in stories):
            continue
        rows.append(row)
    return rows[:limit]


def commission_history(db: Session, commission_id: int) -> list[dict]:
    """Every recorded attempt for one commission, oldest first."""
    rows = (db.query(CommissionPayoutAttempt)
            .filter(CommissionPayoutAttempt.commission_id == commission_id)
            .order_by(CommissionPayoutAttempt.id).all())
    return [_attempt_view(a) for a in rows]


# ------------------------------------------------------------ health check

def unpaid_commission_checks(db: Session, now: datetime, lookback_days: int = 30) -> list[tuple]:
    """The Revenue page's checks for commissions that should have been paid
    by now, each with its REAL reason. Returns (name, status, detail, count)
    tuples for PayoutService.check_payout_system_integrity.

    Looks at pending commissions with no payout, between 1 hour and
    `lookback_days` old (the retry jobs' own window), and sorts them into:
      - waiting for money: the jobs retry every 10 minutes, it sends itself
        once the wallet has enough  -> warning (not "broken")
      - needs action: nothing will happen until a person does something  -> critical
      - never tried: no attempt recorded and the account looks usable, so the
        payout jobs may not be running  -> critical
    """
    # 1. The commissions to explain.
    commissions = (db.query(Commission)
                   .filter(Commission.status == "pending", Commission.payout_id.is_(None),
                           Commission.created_at < now - timedelta(hours=1),
                           Commission.created_at >= now - timedelta(days=lookback_days))
                   .order_by(Commission.created_at).all())
    latest = _latest_by_commission(db, [c.id for c in commissions])
    accounts = {a.user_id: a for a in db.query(PayoutAccount).filter(
        PayoutAccount.user_id.in_({c.user_id for c in commissions})).all()} if commissions else {}

    # 2. Sort each one by what is stopping it.
    waiting, needs_action, never_tried = [], [], []
    for c in commissions:
        attempt = latest.get(c.id)
        label = f"#{c.id} ({money(c.amount, c.currency)})"
        if attempt and attempt.outcome in SELF_FIXING:
            route = route_text(attempt.route, bool(attempt.cross_border), attempt.from_currency, attempt.to_currency)
            waiting.append(f"{label} via {route}: {attempt.reason} (tried {attempt.tries}×)")
        elif attempt:
            needs_action.append(f"{label}: {attempt.reason}")
        else:
            problem = why_account_cannot_be_paid(accounts.get(c.user_id))
            if problem is None:
                never_tried.append(f"{label}: the referrer's account can be paid, but no attempt is recorded")
            elif accounts.get(c.user_id) is not None:
                # No payout account at all is the referrer's choice, not a system problem: not listed.
                needs_action.append(f"{label}: {problem}")

    def detail(items: list[str]) -> str:
        """The first 3 reasons, then '+N more'."""
        return " · ".join(items[:3]) + (f" · +{len(items) - 3} more" if len(items) > 3 else "")

    # 3. One line each on the Revenue page.
    return [
        ("Commissions waiting for money", "warning" if waiting else "ok",
         (f"{len(waiting)} commission(s) can't be sent yet — " + detail(waiting)
          + ". Retried every 10 minutes; sent automatically once there is enough.") if waiting
         else "No commission is waiting for money", len(waiting)),
        ("Commissions that need action", "critical" if needs_action else "ok",
         (f"{len(needs_action)} commission(s) won't be paid until someone acts — " + detail(needs_action))
         if needs_action else "No commission is blocked", len(needs_action)),
        ("Commissions never tried", "critical" if never_tried else "ok",
         (f"{len(never_tried)} commission(s) — " + detail(never_tried) + ". The payout jobs may not be running.")
         if never_tried else "Every commission with a usable account has been tried", len(never_tried)),
    ]
