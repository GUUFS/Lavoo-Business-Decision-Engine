"""
Auto-assigns a staff member as the "referrer" for anyone who signs up with
no referral code at all, so every signup has someone attributed — fairly
rotated across whichever staff emails an admin has added to the pool (see
api/routes/admin/staff_referrals.py), and rated differently from a real
referral (see Referral.via_staff_pool / commission_service.py).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.pg_models import StaffReferralPool, User

logger = logging.getLogger(__name__)

# Its own lock number, separate from the payout locks in commission_service.py
# (7302) and stripe.py (7301) — picking a staff member and paying a
# commission are unrelated operations and must not block each other.
_ASSIGNMENT_LOCK_ID = 7304


def assign_next_staff_referrer(db: Session) -> Optional[User]:
    """
    Pick whoever has gone longest without a referral (a never-assigned
    member counts as longest of all), and record that they just received
    one — a plain turn-based rotation, not a race to equalise totals.

    This is deliberately gentle rather than aggressive: a staff member who
    joins the pool after others already have a head start is NOT given a
    burst of back-to-back referrals to catch their running total up to the
    group's. They're simply slotted into the rotation from here on and take
    their turn exactly like everyone else, so the historical gap narrows
    only gradually, over many turns, the same way it would have if they'd
    always been in the pool. Sorting by assigned_count instead would do the
    opposite — hand every new referral to the newest member alone until
    their count matches the others', which reads as favouritism toward
    whoever just joined.

    Returns the picked User, or None if the pool is empty. Never raises: a
    signup must succeed whether or not this finds anyone to assign.

    Caller is responsible for creating the actual Referral row — this only
    picks and reserves the slot, using its own single-purpose lock so two
    signups happening at the same moment can never be handed the same pick.
    """
    try:
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": _ASSIGNMENT_LOCK_ID})

        pick = (
            db.query(StaffReferralPool)
            .filter(StaffReferralPool.is_active.is_(True))
            .order_by(
                # Primary: whoever hasn't had a turn in the longest time.
                # Only ties among members who have NEVER been assigned
                # (last_assigned_at IS NULL — e.g. several added to the pool
                # before the first referral ever arrives) fall through to
                # assigned_count/id, since "longest ago" has no meaning yet
                # for any of them.
                StaffReferralPool.last_assigned_at.asc().nulls_first(),
                StaffReferralPool.assigned_count.asc(),
                StaffReferralPool.id.asc(),
            )
            .first()
        )
        if not pick:
            return None

        pick.assigned_count = (pick.assigned_count or 0) + 1
        pick.last_assigned_at = datetime.now(timezone.utc)
        db.flush()

        return db.query(User).filter(User.id == pick.user_id).first()
    except Exception as e:
        logger.error(f"[staff-referral] assignment failed: {e}", exc_info=True)
        return None
