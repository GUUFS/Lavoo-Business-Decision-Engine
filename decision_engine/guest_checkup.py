"""
Ad checkup: a visitor from a Facebook ad runs a checkup BEFORE signing up.

THE FLOW
  1. The ad opens lavoo.io/checkup. The visitor types their problem.
  2. start()   - checks the free limits, records a GuestCheckup with a secret
                 token. The normal analysis then runs and is saved with NO
                 owner (api/routes/public_checkup.py).
  3. teaser()  - the visitor sees only "What to fix first" and how much more
                 is waiting. The full plan never leaves the server yet.
  4. They sign up. The browser kept the token.
  5. claim()   - after login, the token makes them the owner of the analysis,
                 and they open the full result.
  6. delete_unclaimed() - a daily job deletes checkups nobody claimed within
                 KEEP_UNCLAIMED_DAYS.

LIMITS (each checkup is a real AI run, so ad clicks cost money)
  - GUEST_CHECKUPS_PER_VISITOR per browser per day (2)
  - GUEST_CHECKUPS_PER_IP per internet address per day (10: phones on the
    same mobile network can share one address, so this is looser)
  - GUEST_CHECKUPS_PER_DAY for everyone together (300)
  Each can be changed with an environment variable of the same name.
"""
import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database.pg_models import BusinessAnalysis, CheckupUsage, GuestCheckup, User

GUEST_CHECKUPS_PER_VISITOR = int(os.getenv("GUEST_CHECKUPS_PER_VISITOR", "2"))
GUEST_CHECKUPS_PER_IP = int(os.getenv("GUEST_CHECKUPS_PER_IP", "10"))
GUEST_CHECKUPS_PER_DAY = int(os.getenv("GUEST_CHECKUPS_PER_DAY", "300"))
KEEP_UNCLAIMED_DAYS = 7
MIN_GOAL_CHARS, MAX_GOAL_CHARS = 10, 2000
# Checkups that use up a free slot (a failed one is given back).
_COUNTED = ("started", "completed", "claimed")


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
        raise _refuse("guest_daily_limit", "Free checkups are full for today. Sign up to run yours now.")
    # 2. This browser.
    if visitor_id and today.filter(GuestCheckup.visitor_id == visitor_id).count() >= GUEST_CHECKUPS_PER_VISITOR:
        raise _refuse("guest_visitor_limit", "You've used today's free checkups. Sign up to see your full results.")
    # 3. This internet address.
    if ip_hash and today.filter(GuestCheckup.ip_hash == ip_hash).count() >= GUEST_CHECKUPS_PER_IP:
        raise _refuse("guest_ip_limit", "Too many free checkups from this network today. Sign up to continue.")


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


def teaser(analysis: BusinessAnalysis) -> dict:
    """What the visitor sees before signing up: the main problem in full,
    and only HOW MUCH more is waiting (not the content)."""
    bottleneck = analysis.primary_bottleneck or {}
    if isinstance(bottleneck, str):
        bottleneck = {"title": bottleneck}
    stacks = analysis.recommended_tool_stacks or []
    tools = {t if isinstance(t, str) else t.get("tool_name")
             for s in stacks if isinstance(s, dict) for t in (s.get("tools") or []) if t}
    return {
        "what_to_fix": {
            "title": bottleneck.get("title") or "",
            "description": bottleneck.get("description") or "",
            "consequence": bottleneck.get("consequence") or "",
        },
        "locked": {
            "other_problems": len(analysis.secondary_constraints or []),
            "action_steps": len(analysis.action_plans or []),
            "tools": len([t for t in tools if t]),
            "roadmap_days": analysis.estimated_days,
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
        raise HTTPException(status_code=404, detail="This checkup can't be found any more. Run a new one.")
    # 2. Already claimed: only by the same person.
    if row.status == "claimed":
        if row.claimed_by != user.id:
            raise HTTPException(status_code=404, detail="This checkup belongs to another account.")
        return row.analysis_id
    # 3. Hand the analysis over.
    analysis = db.get(BusinessAnalysis, row.analysis_id)
    if analysis is None or (analysis.user_id and analysis.user_id != user.id):
        raise HTTPException(status_code=404, detail="This checkup can't be found any more. Run a new one.")
    analysis.user_id = user.id
    row.status, row.claimed_by, row.claimed_at = "claimed", user.id, datetime.now(UTC)
    # 4. Record it in their checkup history as 'guest': visible, but it doesn't
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
