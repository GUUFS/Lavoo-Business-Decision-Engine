from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta, timezone

from database.pg_connections import get_db
from database.pg_models import User, Subscriptions, BusinessAnalysis
from api.routes.dependencies import admin_required

router = APIRouter(prefix="/control/users", tags=["admin-users"])

import logging

logger = logging.getLogger(__name__)


def get_user_avatar(name: str = None) -> str:
    """Safely extract up to 2 uppercase initials without crashing on spaces or empty names."""
    if not name or not isinstance(name, str):
        return "U"
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "U"
    return "".join(p[0] for p in parts[:2]).upper()



def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')"""
    if not dt:
        return "Never"

    # Normalize to naive for arithmetic
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    diff = datetime.utcnow() - dt
    seconds = int(diff.total_seconds())

    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds} sec{'s' if seconds != 1 else ''} ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} min{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hr{'s' if hours != 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"


def to_naive_utc(dt: datetime) -> datetime:
    """Strip timezone info so all comparisons use naive UTC — matching DB column type."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def is_user_inactive(user: User) -> bool:
    """Check if user is inactive (no login for 30 days)"""
    if not user.last_login and not user.updated_at:
        return True

    last_activity = to_naive_utc(user.last_login or user.updated_at)
    cutoff = datetime.utcnow() - timedelta(days=30)
    return last_activity < cutoff


# ── /stats must be declared before /{user_id} to avoid route shadowing ───────
@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get user statistics"""
    try:
        total_users = db.query(func.count(User.id)).scalar()

        pro_users = db.query(func.count(User.id)).filter(
            User.subscription_status == "active"
        ).scalar()

        free_users = db.query(func.count(User.id)).filter(
            or_(
                User.subscription_status != "active",
                User.subscription_status.is_(None),
            )
        ).scalar()

        deactivated_users = db.query(func.count(User.id)).filter(
            User.is_active == False
        ).scalar()

        # ✅ naive UTC — matches the DB column type (no timezone.utc)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        inactive_users = db.query(func.count(User.id)).filter(
            User.is_active == True,
            or_(
                User.last_login < cutoff_date,
                User.last_login.is_(None),
            ),
        ).scalar()

        return {
            "total": total_users,
            "pro": pro_users,
            "free": free_users,
            "deactivated": deactivated_users,
            "inactive": inactive_users,
        }

    except Exception as e:
        print(f"Error in user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ── List route (empty string = /control/users) ────────────────────────────────
@router.get("")
async def get_users(
    limit: int = 10,
    page: int = 1,
    search: str = None,
    status: str = None,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get users with server-side pagination and filtering"""
    try:
        offset = (page - 1) * limit

        query = db.query(User)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (User.name.ilike(search_term)) | (User.email.ilike(search_term))
            )

        # ✅ naive UTC — matches DB column type, avoids offset-naive/aware crash
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        if status and status != "all":
            if status == "active":
                query = query.filter(
                    User.is_active == True,
                    or_(
                        User.last_login >= cutoff_date,
                        User.last_login.is_(None),
                    ),
                )
            elif status == "inactive":
                query = query.filter(
                    User.is_active == True,
                    or_(
                        User.last_login < cutoff_date,
                        User.last_login.is_(None),
                    ),
                )
            elif status in ("suspended", "deactivated"):
                query = query.filter(User.is_active == False)
            elif status == "free":
                query = query.filter(
                    or_(
                        User.subscription_status != "active",
                        User.subscription_status.is_(None),
                    )
                )
            elif status == "pro":
                query = query.filter(User.subscription_status == "active")

        total = query.count()

        # ✅ Single joined query — eliminates the N+1 per-user DB hit
        analysis_counts = (
            db.query(
                BusinessAnalysis.user_id,
                func.count(BusinessAnalysis.id).label("count"),
            )
            .group_by(BusinessAnalysis.user_id)
            .subquery()
        )

        rows = (
            query.outerjoin(analysis_counts, User.id == analysis_counts.c.user_id)
            .add_columns(func.coalesce(analysis_counts.c.count, 0).label("analysis_count"))
            .order_by(desc(User.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

        result = []
        for row in rows:
            user = row[0]
            analysis_count = row[1]

            if not user.is_active:
                user_status = "suspended"
            elif is_user_inactive(user):
                user_status = "inactive"
            else:
                user_status = "active"

            last_active_dt = user.last_login or user.updated_at
            last_active = format_relative_time(last_active_dt)

            result.append(
                {
                    "id": user.id,
                    "name": user.name or "",
                    "email": user.email,
                    "role": "admin" if user.is_admin else "user",
                    "plan": user.subscription_plan or "Free",
                    "subscription_status": user.subscription_status or "none",
                    "status": user_status,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "joinDate": user.created_at.strftime("%Y-%m-%d") if user.created_at else None,
                    "lastActive": last_active,
                    "last_active": last_active,
                    "analyses": analysis_count,
                    "avatar": get_user_avatar(user.name),
                }
            )

        return {
            "users": result,
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": (total + limit - 1) // limit if limit else 1,
        }
    except Exception as e:
        logger.error(f"Error in get_users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


# ── Dynamic route AFTER static routes (/stats must not be shadowed) ───────────
@router.get("/{user_id}")
async def get_user_details(
    user_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Get full user details for modal"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from api.utils.sub_utils import sync_user_subscription
    user = sync_user_subscription(db, user)

    days_remaining = 0
    if user.subscription_status == "active" and user.subscriptions:
        first_sub = (
            db.query(Subscriptions)
            .filter(Subscriptions.user_id == user.id)
            .order_by(Subscriptions.created_at.asc(), Subscriptions.id.asc())
            .first()
        )
        if first_sub and first_sub.end_date:
            # ✅ Normalize both sides to naive UTC before comparing
            end_date = to_naive_utc(first_sub.end_date)
            delta = end_date - datetime.utcnow()
            days_remaining = max(0, delta.days)

    from database.pg_models import Referral
    referrals = db.query(Referral).filter(Referral.referrer_id == user.id).all()
    referral_names = [ref.referred_user.name for ref in referrals if ref.referred_user]

    # Who referred THIS user — the reverse direction from referral_names
    # above (who this user referred). Previously not surfaced at all, so
    # the admin had no way to see a user's own referrer from this modal.
    inbound_referral = (
        db.query(Referral)
        .filter(Referral.referred_user_id == user.id)
        .order_by(Referral.created_at.desc())
        .first()
    )
    # referrer_id points at the actual staff member's User row even for a
    # staff-pool auto-assignment (signup.py sets referrer_id=referrer.id in
    # both cases) — so the real name/email is always available here. Only
    # the via_staff_pool flag itself distinguishes "signed up with a real
    # referral code" from "no code, auto-assigned to a staff member."
    referred_by = None
    if inbound_referral and inbound_referral.referrer:
        referred_by = {
            "name": inbound_referral.referrer.name,
            "email": inbound_referral.referrer.email,
            "id": inbound_referral.referrer.id,
            "via_staff_pool": inbound_referral.via_staff_pool,
        }

    if not user.is_active:
        status = "suspended"
    elif is_user_inactive(user):
        status = "inactive"
    else:
        status = "active"

    last_active_dt = user.last_login or user.updated_at
    last_active = format_relative_time(last_active_dt)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar": get_user_avatar(user.name),
        "joinDate": user.created_at.isoformat() if user.created_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "lastActive": last_active,
        "last_active": last_active,
        "status": status,
        "is_active": user.is_active,
        "subscription_status": user.subscription_status,
        "subscription_plan": user.subscription_plan or "Free",
        "total_chops": user.total_chops or 0,
        "referral_chops": user.referral_chops or 0,
        "alert_read_chops": user.alert_reading_chops or 0,
        "alert_share_chops": user.alert_sharing_chops or 0,
        "insight_read_chops": user.insight_reading_chops or 0,
        "insight_share_chops": user.insight_sharing_chops or 0,
        "referral_code": user.referral_code,
        "total_referrals": user.referral_count or 0,
        "referred_users": referral_names,
        "referred_by": referred_by,
        "days_remaining": days_remaining,
    }


@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Toggle user active status (Deactivate/Activate)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_id_from_token = (
        current_user.get("id") or current_user.get("user", {}).get("id")
        if isinstance(current_user, dict)
        else current_user.id
    )

    if user.id == user_id_from_token:
        raise HTTPException(
            status_code=400, detail="Cannot deactivate your own admin account"
        )

    user.is_active = not user.is_active
    db.commit()

    action = "activated" if user.is_active else "deactivated"
    new_status = "active" if user.is_active else "suspended"

    return {
        "status": "success",
        "message": f"User {user.email} has been {action}",
        "new_status": new_status,
    }


@router.post("/generate-referral-codes")
async def generate_missing_referral_codes(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Generate referral codes for all users who don't have one"""
    import random
    import string

    def generate_referral_code(length=8):
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    users_without_codes = db.query(User).filter(
        or_(User.referral_code.is_(None), User.referral_code == "")
    ).all()

    updated_count = 0
    for user in users_without_codes:
        new_code = generate_referral_code()
        while db.query(User).filter(User.referral_code == new_code).first():
            new_code = generate_referral_code()
        user.referral_code = new_code
        updated_count += 1

    db.commit()

    return {
        "status": "success",
        "message": f"Generated referral codes for {updated_count} users",
        "updated_count": updated_count,
    }


@router.post("/sync-subscriptions")
async def sync_subscription_statuses(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Sync subscription statuses for all users"""
    users = db.query(User).all()
    updated_count = 0

    for user in users:
        original_status = user.subscription_status
        original_plan = user.subscription_plan

        active_sub = None
        if user.subscriptions:
            for sub in user.subscriptions:
                if sub.status == "active" and sub.end_date:
                    # ✅ Normalize to naive UTC before comparing
                    end_date = to_naive_utc(sub.end_date)
                    if end_date > datetime.utcnow():
                        active_sub = sub
                        break
                    else:
                        sub.status = "expired"

        if active_sub:
            user.subscription_status = "active"
            user.subscription_plan = active_sub.plan_type or "Pro"
        else:
            user.subscription_status = "Free"
            user.subscription_plan = "Free"

        if (
            user.subscription_status != original_status
            or user.subscription_plan != original_plan
        ):
            updated_count += 1

    db.commit()

    return {
        "status": "success",
        "message": f"Synced subscription statuses for {updated_count} users",
        "updated_count": updated_count,
    }


def _delete_user_completely(db: Session, user_id: int) -> dict:
    """
    Fully removes a user and everything tied to them. Most tables this
    touches have no DB-level cascade (confirmed against the model
    definitions — only the community/content tables do), so a plain
    db.delete(user) would just fail on a foreign-key violation the moment
    the account had ANY real activity. Walks every table with a hard
    reference to users.id instead, in dependency order, then the user row.

    Referrals are the one case that needs more than a delete: if this user
    was credited chops for referring someone, deleting that Referral row
    must also claw back the chops/referral_count it granted — otherwise a
    real referrer's stats stay permanently inflated by a removed account,
    silently wrong forever.

    Returns a summary dict for the caller to report back.
    """
    from database.pg_models import (
        BusinessAnalysis, UserNotification, Ticket, TicketMessage, UserAlert,
        Referral, StaffReferralPool, Commission, Payout, PayoutAccount,
        CommissionSummary, UserInsight, UserPinnedInsight, UserPinnedAlert,
        Trend, PushSubscription, CommunityChannel, ChannelMember,
        CommunityDiscussion, DiscussionPollVote, DiscussionReply,
        DiscussionLike, DiscussionBookmark, EventRegistration,
        CommunityActivity, SavedItem,
    )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "not_found", "user_id": user_id}

    summary = {"user_id": user_id, "email": user.email, "deleted": {}, "chops_corrections": []}

    def _delete_all(model, *filters):
        count = db.query(model).filter(*filters).delete(synchronize_session=False)
        if count:
            summary["deleted"][model.__name__] = summary["deleted"].get(model.__name__, 0) + count

    # Commissions earned by someone ELSE because of this user's activity
    # (they were the referred_user on the subscription that created it) —
    # delete the row, but it isn't this user's own money, so no chops
    # correction is owed for these the way it is for Referral below.
    _delete_all(Commission, or_(Commission.user_id == user_id, Commission.referred_user_id == user_id))

    # Referrals — reverse the chops a REAL referrer was credited for
    # referring this user, before removing the row.
    incoming_refs = db.query(Referral).filter(Referral.referred_user_id == user_id).all()
    for r in incoming_refs:
        referrer = db.query(User).filter(User.id == r.referrer_id).first()
        if referrer and referrer.id != user_id:
            before = (referrer.total_chops, referrer.referral_chops, referrer.referral_count)
            referrer.total_chops = max(0, (referrer.total_chops or 0) - (r.chops_awarded or 0))
            referrer.referral_chops = max(0, (referrer.referral_chops or 0) - (r.chops_awarded or 0))
            referrer.referral_count = max(0, (referrer.referral_count or 0) - 1)
            summary["chops_corrections"].append({
                "referrer_email": referrer.email,
                "total_chops": f"{before[0]}->{referrer.total_chops}",
                "referral_chops": f"{before[1]}->{referrer.referral_chops}",
                "referral_count": f"{before[2]}->{referrer.referral_count}",
            })
    _delete_all(Referral, or_(Referral.referrer_id == user_id, Referral.referred_user_id == user_id))

    _delete_all(Subscriptions, Subscriptions.user_id == user_id)
    _delete_all(Payout, Payout.user_id == user_id)
    _delete_all(PayoutAccount, PayoutAccount.user_id == user_id)
    _delete_all(CommissionSummary, CommissionSummary.user_id == user_id)
    _delete_all(StaffReferralPool, StaffReferralPool.user_id == user_id)
    _delete_all(BusinessAnalysis, BusinessAnalysis.user_id == user_id)
    _delete_all(UserNotification, UserNotification.user_id == user_id)
    _delete_all(UserAlert, UserAlert.user_id == user_id)
    _delete_all(UserInsight, UserInsight.user_id == user_id)
    _delete_all(UserPinnedInsight, UserPinnedInsight.user_id == user_id)
    _delete_all(UserPinnedAlert, UserPinnedAlert.user_id == user_id)
    _delete_all(PushSubscription, PushSubscription.user_id == user_id)

    ticket_ids = [t.id for t in db.query(Ticket.id).filter(Ticket.user_id == user_id).all()]
    _delete_all(TicketMessage, TicketMessage.sender_id == user_id)
    if ticket_ids:
        _delete_all(TicketMessage, TicketMessage.ticket_id.in_(ticket_ids))
    _delete_all(Ticket, Ticket.user_id == user_id)

    db.query(Trend).filter(Trend.created_by == user_id).update({"created_by": None}, synchronize_session=False)

    # Community content — the DB models declare ondelete="CASCADE" for
    # these, but defensive CREATE TABLE fallbacks elsewhere in this app
    # (api/main.py, used when Alembic drifts) don't reliably apply the
    # same constraint, so delete explicitly rather than trust it's live.
    _delete_all(ChannelMember, ChannelMember.user_id == user_id)
    _delete_all(DiscussionPollVote, DiscussionPollVote.user_id == user_id)
    _delete_all(DiscussionLike, DiscussionLike.user_id == user_id)
    _delete_all(DiscussionBookmark, DiscussionBookmark.user_id == user_id)
    _delete_all(EventRegistration, EventRegistration.user_id == user_id)
    _delete_all(CommunityActivity, CommunityActivity.user_id == user_id)
    _delete_all(SavedItem, SavedItem.user_id == user_id)
    reply_ids = [r.id for r in db.query(DiscussionReply.id).filter(DiscussionReply.user_id == user_id).all()]
    _delete_all(DiscussionReply, DiscussionReply.user_id == user_id)
    disc_ids = [d.id for d in db.query(CommunityDiscussion.id).filter(CommunityDiscussion.user_id == user_id).all()]
    if disc_ids:
        _delete_all(DiscussionReply, DiscussionReply.discussion_id.in_(disc_ids))
        _delete_all(DiscussionLike, DiscussionLike.discussion_id.in_(disc_ids))
        _delete_all(DiscussionBookmark, DiscussionBookmark.discussion_id.in_(disc_ids))
        _delete_all(DiscussionPollVote, DiscussionPollVote.discussion_id.in_(disc_ids))
    _delete_all(CommunityDiscussion, CommunityDiscussion.user_id == user_id)

    db.delete(user)
    summary["deleted"]["User"] = 1
    return summary


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Permanently delete one user and everything tied to their account."""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    try:
        summary = _delete_user_completely(db, user_id)
        if summary.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="User not found")
        db.commit()
        logger.warning(f"[admin] User {user_id} ({summary.get('email')}) permanently deleted by admin {current_user.email}: {summary}")
        return {"status": "success", "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[admin] Failed to delete user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete-bulk")
async def delete_users_bulk(
    payload: dict,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Permanently delete several users at once. Body: {"user_ids": [1, 2, 3]}."""
    user_ids = payload.get("user_ids") or []
    if not isinstance(user_ids, list) or not user_ids:
        raise HTTPException(status_code=400, detail="user_ids must be a non-empty list")
    if current_user.id in user_ids:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    results = []
    for uid in user_ids:
        try:
            summary = _delete_user_completely(db, int(uid))
            db.commit()
            results.append(summary)
            logger.warning(f"[admin] User {uid} permanently deleted (bulk) by admin {current_user.email}: {summary}")
        except Exception as e:
            db.rollback()
            logger.error(f"[admin] Bulk delete failed for user {uid}: {e}", exc_info=True)
            results.append({"user_id": uid, "status": "error", "error": str(e)})

    deleted_count = len([r for r in results if r.get("status") != "error" and r.get("status") != "not_found"])
    return {"status": "success", "deleted_count": deleted_count, "results": results}