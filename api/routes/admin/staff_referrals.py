"""
Admin management of the staff referral pool — see api/services/
staff_referral_service.py for the fair-rotation pick this pool feeds, and
Referral.via_staff_pool / commission_service.py for how a resulting
commission is rated (flat 30%) differently from a real referral.
"""
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database.pg_connections import get_db
from database.pg_models import Commission, Referral, StaffReferralPool, User
from api.routes.dependencies import admin_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/control/staff-referral-pool", tags=["admin-staff-referrals"])


class AddStaffEmail(BaseModel):
    email: EmailStr


def _serialize(entry: StaffReferralPool, db: Session) -> dict:
    user = db.query(User).filter(User.id == entry.user_id).first()
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "email": entry.email,
        "name": user.name if user else None,
        "is_active": entry.is_active,
        "assigned_count": entry.assigned_count or 0,
        "last_assigned_at": entry.last_assigned_at.isoformat() if entry.last_assigned_at else None,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.get("")
async def list_staff_referral_pool(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    entries = db.query(StaffReferralPool).order_by(StaffReferralPool.created_at.asc()).all()
    return {"pool": [_serialize(e, db) for e in entries]}


@router.get("/{entry_id}/referrals")
async def list_staff_referral_assignments(
    entry_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    The actual referred users assigned to one staff member — what the pool's
    'Assigned so far' count on the list view is a running total of. Each
    Commission is matched by both referrer AND referred user, not just the
    referrer, since a referrer can have commissions from other sources too.
    """
    entry = db.query(StaffReferralPool).filter(StaffReferralPool.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    referrals = (
        db.query(Referral)
        .filter(Referral.referrer_id == entry.user_id, Referral.via_staff_pool.is_(True))
        .order_by(Referral.created_at.desc())
        .all()
    )

    rows = []
    for referral in referrals:
        referred = db.query(User).filter(User.id == referral.referred_user_id).first()
        commissions = db.query(Commission).filter(
            Commission.user_id == entry.user_id,
            Commission.referred_user_id == referral.referred_user_id,
        ).all()
        rows.append({
            "referred_user_id": referral.referred_user_id,
            "name": referred.name if referred else None,
            "email": referred.email if referred else None,
            "assigned_at": referral.created_at.isoformat() if referral.created_at else None,
            "subscription_status": referred.subscription_status if referred else None,
            "commission_count": len(commissions),
            "commission_total": sum(float(c.amount) for c in commissions) if commissions else 0.0,
            "commission_currency": commissions[0].currency if commissions else None,
        })

    return {"staff_name": entry.email, "referrals": rows}


@router.post("")
async def add_staff_referral_email(
    body: AddStaffEmail,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Add a staff email to the pool. The person must already have a Lavoo
    account (commissions are paid to a User, so there's nothing to attribute
    them to otherwise) — sign them up first if they don't have one yet.
    """
    user = db.query(User).filter(User.email.ilike(body.email)).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No Lavoo account exists for {body.email} yet — they need an account before they can be added.",
        )

    existing = db.query(StaffReferralPool).filter(StaffReferralPool.user_id == user.id).first()
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail=f"{body.email} is already in the pool.")
        existing.is_active = True
        existing.email = user.email
        db.commit()
        db.refresh(existing)
        return {"status": "success", "entry": _serialize(existing, db)}

    entry = StaffReferralPool(user_id=user.id, email=user.email, is_active=True)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(f"[staff-referral-pool] added {user.email} (user_id={user.id}) by admin {current_user.email}")
    return {"status": "success", "entry": _serialize(entry, db)}


@router.delete("/{entry_id}")
async def remove_staff_referral_email(
    entry_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Deactivates rather than deletes — its assigned_count/last_assigned_at
    and every Referral it already produced stay on file. Re-adding the same
    email later resumes from its prior assigned_count, not zero, so it
    can't unfairly cut back in line ahead of staff who stayed in the pool.
    """
    entry = db.query(StaffReferralPool).filter(StaffReferralPool.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    entry.is_active = False
    db.commit()
    logger.info(f"[staff-referral-pool] removed {entry.email} (user_id={entry.user_id}) by admin {current_user.email}")
    return {"status": "success"}


@router.post("/backfill")
async def backfill_staff_referrals(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    One-time, admin-triggered: assign a staff member to every EXISTING user
    who has no referrer at all (no referral code was ever used, and they've
    never been auto-assigned before), using the same fair-rotation pick as
    new signups.

    Only creates the referral link itself, going forward — it does NOT
    retroactively generate commissions for subscription payments these
    users already made before today. Their existing Commission history is
    untouched; only their FUTURE payments will earn the assigned staff
    member a commission.
    """
    from api.services.staff_referral_service import assign_next_staff_referrer
    from database.pg_models import NotificationType
    from api.services.notification_service import NotificationService

    if not db.query(StaffReferralPool).filter(StaffReferralPool.is_active.is_(True)).first():
        raise HTTPException(status_code=400, detail="The staff referral pool is empty — add at least one staff email first.")

    already_referred_ids = {r[0] for r in db.query(Referral.referred_user_id).all()}
    already_in_pool_ids = {r[0] for r in db.query(StaffReferralPool.user_id).all()}

    candidates = (
        db.query(User)
        .filter(
            User.referrer_code.is_(None),
            User.is_admin.is_(False),
            User.is_bot.is_(False),
        )
        .order_by(User.created_at.asc())
        .all()
    )
    candidates = [u for u in candidates if u.id not in already_referred_ids and u.id not in already_in_pool_ids]

    assigned = 0
    for user in candidates:
        staff = assign_next_staff_referrer(db)
        if not staff:
            break  # pool became empty mid-run (shouldn't happen — checked above) — stop rather than skip silently
        staff.referral_count = (staff.referral_count or 0) + 1
        user.total_chops = (user.total_chops or 0) + 50
        staff.total_chops = (staff.total_chops or 0) + 50
        staff.referral_chops = (staff.referral_chops or 0) + 50
        user.referrer_code = staff.referral_code

        db.add(Referral(
            referrer_id=staff.id, referred_user_id=user.id,
            chops_awarded=50, created_at=datetime.now(timezone.utc),
            via_staff_pool=True,
        ))
        NotificationService.create_notification(
            db=db, user_id=user.id, type=NotificationType.REFERRAL_REGISTERED.value,
            title="Welcome Bonus!", message="You received 50 chops for joining Lavoo!",
            link="/dashboard/earnings",
        )
        NotificationService.create_notification(
            db=db, user_id=staff.id, type=NotificationType.REFERRAL_REGISTERED.value,
            title="New Referral! +50 Chops",
            message=f"{user.name} was assigned to you as a new referral. You earned 50 chops!",
            link="/dashboard/referrals",
        )
        assigned += 1

    db.commit()
    logger.info(f"[staff-referral-pool] backfill by admin {current_user.email}: assigned {assigned} of {len(candidates)} candidate(s)")
    return {"status": "success", "assigned": assigned, "candidates_found": len(candidates)}
