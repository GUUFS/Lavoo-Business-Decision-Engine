"""
Ad checkup: a visitor from a Facebook ad runs a checkup BEFORE signing up.

THE FLOW
  1. The ad opens lavoo.io/checkup. The visitor types their problem.
  2. start()   - checks the free limits, records a GuestCheckup with a secret
                 token. The normal analysis then runs and is saved with NO
                 owner (api/routes/public_checkup.py).
  3. teaser()  - the visitor sees the Primary Problem and Secondary Problems
                 in full, and only the TITLES of the Ranked Action Plan (the
                 page blurs the rest). What to stop doing and the Missions
                 stay on the server until signup.
  4. They sign up. The browser kept the token.
  5. claim()   - after login, the token makes them the owner of the analysis,
                 and they open the full result.
  6. delete_unclaimed() - a daily job deletes checkups nobody claimed within
                 KEEP_UNCLAIMED_DAYS.

FAILURES
  record_failure() logs every check-up that went wrong, from the server or
  from the browser, with the reason. More than FAILURE_ALERT_COUNT in an hour
  emails the admin (at most one email an hour).

LIMITS (each checkup is a real AI run, so ad clicks cost money)
  - GUEST_CHECKUPS_PER_VISITOR per browser per day (2)
  - GUEST_CHECKUPS_PER_IP per internet address per day (10: phones on the
    same mobile network can share one address, so this is looser)
  - GUEST_CHECKUPS_PER_DAY for everyone together (300)
  Each can be changed with an environment variable of the same name.
"""
import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.pg_models import BusinessAnalysis, CheckupFailure, CheckupUsage, GuestCheckup, User

logger = logging.getLogger(__name__)

GUEST_CHECKUPS_PER_VISITOR = int(os.getenv("GUEST_CHECKUPS_PER_VISITOR", "2"))
GUEST_CHECKUPS_PER_IP = int(os.getenv("GUEST_CHECKUPS_PER_IP", "10"))
GUEST_CHECKUPS_PER_DAY = int(os.getenv("GUEST_CHECKUPS_PER_DAY", "300"))
KEEP_UNCLAIMED_DAYS = 7
MIN_GOAL_CHARS, MAX_GOAL_CHARS = 10, 2000
# Checkups that use up a free slot (a failed one is given back).
_COUNTED = ("started", "completed", "claimed")
# More than this many failures in an hour emails the admin.
FAILURE_ALERT_COUNT = 3
# The reason saved when the visitor closes the page mid-run. It is logged, but
# it isn't our fault, so it doesn't count towards the admin alert.
VISITOR_LEFT = "The visitor left before it finished"


def hash_ip(ip: str | None) -> str | None:
    """The visitor's IP address, hashed (with the server's secret) so it is never stored as is."""
    if not ip:
        return None
    salt = os.getenv("SECRET_KEY", "")
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()


def _refuse(code: str, message: str) -> HTTPException:
    """A 429 the checkup page shows as a "sign up instead" message."""
    return HTTPException(status_code=429, detail={"code": code, "message": message})


def check_limits(db: Session, visitor_id: str | None, ip_hash: str | None, now: datetime | None = None) -> None:
    """Raise HTTP 429 if this visitor, this address, or everyone together
    has used today's free checkups (a day = the last 24 hours)."""
    now = now or datetime.now(UTC)
    since = now - timedelta(hours=24)
    today = db.query(GuestCheckup).filter(GuestCheckup.created_at >= since, GuestCheckup.status.in_(_COUNTED))
    # 1. Everyone together: protects the daily AI budget.
    if today.count() >= GUEST_CHECKUPS_PER_DAY:
        raise _refuse("guest_daily_limit", "Free check-ups are full for today. Sign up to run yours now.")
    # 2. This browser.
    if visitor_id and today.filter(GuestCheckup.visitor_id == visitor_id).count() >= GUEST_CHECKUPS_PER_VISITOR:
        raise _refuse("guest_visitor_limit", "You've used today's free check-ups. Sign up to see your full results.")
    # 3. This internet address.
    if ip_hash and today.filter(GuestCheckup.ip_hash == ip_hash).count() >= GUEST_CHECKUPS_PER_IP:
        raise _refuse("guest_ip_limit", "Too many free check-ups from this network today. Sign up to continue.")


def clean_goal(text: str | None) -> str:
    """The visitor's problem, trimmed; HTTP 400 if too short or too long."""
    goal = (text or "").strip()
    if len(goal) < MIN_GOAL_CHARS:
        raise HTTPException(status_code=400, detail="Tell us a bit more about your business problem.")
    if len(goal) > MAX_GOAL_CHARS:
        raise HTTPException(status_code=400, detail=f"Please keep it under {MAX_GOAL_CHARS} characters.")
    return goal


def start(db: Session, goal: str, visitor_id: str | None, ip_hash: str | None,
          utm_source: str | None = None, utm_campaign: str | None = None) -> GuestCheckup:
    """Check the limits and record a new guest checkup with its secret token."""
    check_limits(db, visitor_id, ip_hash)
    row = GuestCheckup(
        token=secrets.token_urlsafe(24), visitor_id=(visitor_id or "")[:64] or None, ip_hash=ip_hash,
        business_goal=goal, status="started",
        utm_source=(utm_source or "")[:100] or None, utm_campaign=(utm_campaign or "")[:150] or None,
    )
    db.add(row)
    db.commit()
    return row


def finish(db: Session, checkup_id: int, analysis_id: int | None = None, error: str | None = None) -> None:
    """Record how the analysis ended: completed (with its analysis) or failed.

    Takes the id, not the row object: while the answer streams, the request's
    session has already let go of the row, so changing the object (or even
    reading it) fails (same approach as checkup_limits._finish). Never raises."""
    fields = {
        "status": "completed" if analysis_id else "failed",
        "analysis_id": analysis_id,
        "error": (error or "")[:2000] or None,
    }
    try:
        # 1. A failed analysis can leave half-done work in the session: clear it.
        if not analysis_id:
            db.rollback()
        # 2. Save the outcome on the database row itself.
        db.query(GuestCheckup).filter(GuestCheckup.id == checkup_id).update(fields)
        db.commit()
    except Exception:
        db.rollback()
    # 3. A failure also goes in the failure log (which may alert the admin).
    if not analysis_id:
        record_failure(db, "server", error or "Unknown error", checkup_id=checkup_id)


def _send_failure_alert(count: int, latest: str) -> None:
    """Email the admin that ad check-ups are failing. Never raises."""
    try:
        from emailing.email_service import email_service
        admin_email = os.getenv("ADMIN_ALERT_EMAIL", os.getenv("SUPPORT_EMAIL", "support@lavoo.io"))
        body = (f"{count} ad check-ups failed in the last hour. Latest reason: {latest[:500]}. "
                "Every failure is in the checkup_failures table.")
        email_service._send_email(to_email=admin_email, to_name="Lavoo Admin",
                                  subject=f"⚠️ {count} ad check-ups failed in the last hour",
                                  html_content=f"<p>{body}</p>", text_content=body)
    except Exception as exc:
        logger.error(f"[guest-checkup] failure alert not sent: {exc}")


def record_failure(db: Session, source: str, reason: str, checkup_id: int | None = None,
                   visitor_id: str | None = None, now: datetime | None = None) -> bool:
    """Log one failed check-up ("server" or "browser") with its reason.
    Emails the admin when more than FAILURE_ALERT_COUNT happen in an hour,
    at most once an hour. Returns True if an alert was sent. Never raises."""
    now = now or datetime.now(UTC)
    try:
        # 1. Save the failure.
        row = CheckupFailure(source=source[:20], reason=(reason or "Unknown error")[:2000],
                             checkup_id=checkup_id, visitor_id=(visitor_id or "")[:64] or None)
        db.add(row)
        db.commit()
        logger.warning(f"[guest-checkup] {source} failure: {row.reason[:300]}")
        # 2. Count the last hour's failures (a visitor closing the page doesn't count).
        hour_ago = now - timedelta(hours=1)
        recent = db.query(CheckupFailure).filter(CheckupFailure.created_at >= hour_ago,
                                                  CheckupFailure.reason != VISITOR_LEFT)
        count = recent.count()
        if count <= FAILURE_ALERT_COUNT:
            return False
        # 3. Already alerted in the last hour: don't email again.
        if recent.filter(CheckupFailure.alerted.is_(True)).count():
            return False
        # 4. Mark this one as the alert, then email.
        row.alerted = True
        db.commit()
        _send_failure_alert(count, row.reason)
        return True
    except Exception as exc:
        db.rollback()
        logger.error(f"[guest-checkup] could not log a failure: {exc}")
        return False


def _secondary_problem(item, index: int) -> dict:
    """One Secondary Problem, in the shape the result page shows it."""
    # 1. Older analyses keep it as plain text.
    if isinstance(item, str):
        return {"number": f"0{index + 2}", "title": item, "description": item}
    # 2. Newer ones are a dict (same fields the result page reads).
    item = item if isinstance(item, dict) else {}
    title = item.get("title") or item.get("constraint") or item.get("name") or f"Problem {index + 1}"
    return {
        "number": str(item.get("number") or f"0{index + 2}"),
        "title": title,
        "description": item.get("description") or item.get("impact") or item.get("details") or title,
    }


def _mission_count(analysis: BusinessAnalysis) -> int:
    """How many daily Missions the plan has (the roadmap's tasks, repeats
    counted once, as on the result page), or the number of actions."""
    count = 0
    # 1. Count each roadmap phase's tasks, a repeated task only once.
    for phase in analysis.execution_roadmap or []:
        tasks = phase.get("tasks") if isinstance(phase, dict) else None
        seen = set()
        for task in tasks or []:
            key = " ".join(str(task).lower().split())[:60]
            if key not in seen:
                seen.add(key)
                count += 1
    # 2. No roadmap: one Mission per action.
    return count or len(analysis.action_plans or [])


def teaser(analysis: BusinessAnalysis) -> dict:
    """What the visitor sees before signing up.

    Shown in full: the Primary Problem and the Secondary Problems.
    Shown as titles only: the Ranked Action Plan (the page blurs the rest).
    Not sent at all: the action plans' content, what to stop doing and the
    Missions. Only that they exist, so nothing hidden can be read with the
    browser's developer tools."""
    # 1. The Primary Problem, in full.
    bottleneck = analysis.primary_bottleneck or {}
    if isinstance(bottleneck, str):
        bottleneck = {"title": bottleneck}
    # 2. The Ranked Action Plan: titles only.
    titles = []
    for index, plan in enumerate(analysis.action_plans or []):
        plan = plan if isinstance(plan, dict) else {}
        titles.append(plan.get("title") or plan.get("action_title") or f"Action {index + 1}")
    return {
        "primary_problem": {
            "title": bottleneck.get("title") or "",
            "description": bottleneck.get("description") or "",
            "consequence": bottleneck.get("consequence") or bottleneck.get("impact") or "",
        },
        # 3. The Secondary Problems, in full.
        "secondary_problems": [_secondary_problem(item, i)
                               for i, item in enumerate(analysis.secondary_constraints or [])],
        "action_plan_titles": titles,
        # 4. Behind the sign-up card: only how much is waiting.
        "locked": {
            "stop_doing": bool((analysis.what_to_stop or "").strip()),
            "missions": _mission_count(analysis),
        },
    }


def find(db: Session, token: str) -> GuestCheckup | None:
    """The guest checkup for a token, or None."""
    return db.query(GuestCheckup).filter(GuestCheckup.token == token).first() if token else None


def claim(db: Session, token: str, user: User) -> int:
    """Make the logged-in user the owner of their ad checkup. Returns the
    analysis id. Safe to call twice (the second time just returns the id)."""
    row = find(db, token)
    # 1. Unknown, not finished, or deleted.
    if not row or not row.analysis_id or row.status not in ("completed", "claimed"):
        raise HTTPException(status_code=404, detail="This check-up can't be found any more. Run a new one.")
    # 2. Already claimed: only by the same person.
    if row.status == "claimed":
        if row.claimed_by != user.id:
            raise HTTPException(status_code=404, detail="This check-up belongs to another account.")
        return row.analysis_id
    # 3. Hand the analysis over.
    analysis = db.get(BusinessAnalysis, row.analysis_id)
    if analysis is None or (analysis.user_id and analysis.user_id != user.id):
        raise HTTPException(status_code=404, detail="This check-up can't be found any more. Run a new one.")
    analysis.user_id = user.id
    row.status, row.claimed_by, row.claimed_at = "claimed", user.id, datetime.now(UTC)
    # 4. Remember which ad brought them (only if nothing is recorded yet).
    if not user.utm_source and not user.utm_campaign:
        user.utm_source, user.utm_campaign = row.utm_source, row.utm_campaign
    # 5. Record it in their checkup history as 'guest': visible, but it doesn't
    #    use up a weekly or monthly checkup (it was run before they joined).
    db.add(CheckupUsage(user_id=user.id, created_at=row.created_at or datetime.now(UTC),
                        status="guest", analysis_id=analysis.id))
    db.commit()
    return analysis.id


def delete_unclaimed(db: Session, now: datetime | None = None) -> int:
    """Delete guest checkups (and their ownerless analyses) nobody claimed
    within KEEP_UNCLAIMED_DAYS. Returns how many were deleted."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=KEEP_UNCLAIMED_DAYS)
    rows = db.query(GuestCheckup).filter(GuestCheckup.created_at < cutoff, GuestCheckup.status != "claimed").all()
    for row in rows:
        # 1. The analysis, only while it still has no owner.
        if row.analysis_id:
            analysis = db.get(BusinessAnalysis, row.analysis_id)
            if analysis is not None and analysis.user_id is None:
                db.delete(analysis)
        # 2. The guest record.
        db.delete(row)
    db.commit()
    return len(rows)
