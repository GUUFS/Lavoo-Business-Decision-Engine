from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime

from database.pg_connections import get_db
from database.pg_models import User, UserRole
from api.routes.dependencies import admin_required
from api.routes.admin.users import get_user_avatar

router = APIRouter(prefix="/control/permissions", tags=["admin-permissions"])

ASSIGNABLE_ROLES = {UserRole.NORMAL.value, UserRole.MODERATOR.value}


class SetRoleRequest(BaseModel):
    role: str


class SetStaffRequest(BaseModel):
    is_staff: bool


class SetPartnerRequest(BaseModel):
    is_partner: bool


@router.get("")
async def get_users_for_permissions(
    limit: int = 10,
    page: int = 1,
    search: str = "",
    role: str = "",          # filter: "moderator" | "staff" | "normal_user" | "" = all
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Return paginated users for the permissions management page. Includes
    both role (moderator/normal_user — single-select) and is_staff
    (independent boolean — a user can be moderator AND staff at once) so
    the admin can see and change either.

    The "staff" filter value queries is_staff rather than the role column
    — it isn't one of role's own values (see ASSIGNABLE_ROLES / User.role's
    comment on pg_models.py for why staff lives on its own column).
    """
    offset = (page - 1) * limit
    query = db.query(User)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(User.name.ilike(term), User.email.ilike(term))
        )

    if role == "staff":
        query = query.filter(User.is_staff.is_(True))
    elif role == "partner":
        query = query.filter(User.is_partner.is_(True))
    elif role in ASSIGNABLE_ROLES:
        query = query.filter(User.role == role)

    total = query.count()

    users = (
        query.order_by(desc(User.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_staff": bool(user.is_staff),
            "is_partner": bool(user.is_partner),
            "partner_since": user.partner_since.isoformat() if user.partner_since else None,
            "partner_premium_until": user.partner_premium_until.isoformat() if user.partner_premium_until else None,
            "is_active": user.is_active,
            "role": user.role or UserRole.NORMAL.value,
            "subscription_status": user.subscription_status or "none",
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "avatar": get_user_avatar(user.name),
        })

    return {
        "users": result,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit,
    }


@router.patch("/{user_id}/role")
async def set_user_role(
    user_id: int,
    request: SetRoleRequest,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Assign a user's community role directly (normal_user / moderator)
    rather than only toggling moderator on and off. Staff is a separate,
    independent flag — see set_user_staff below — not a value of this
    role, so assigning moderator here never removes a user's staff status
    or vice versa. Cannot change your own role or another admin's role.
    """
    if request.role not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{request.role}'. Must be one of: {', '.join(sorted(ASSIGNABLE_ROLES))}",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Resolve the calling admin's id regardless of dict vs ORM object
    caller_id = (
        current_user.get("id") or current_user.get("user", {}).get("id")
        if isinstance(current_user, dict)
        else current_user.id
    )

    if user.id == caller_id:
        raise HTTPException(
            status_code=400, detail="Cannot change your own role"
        )

    if user.is_admin:
        raise HTTPException(
            status_code=400, detail="Cannot change the role of a platform admin"
        )

    user.role = request.role
    db.commit()

    role_label = request.role.replace('_', ' ')
    return {
        "status": "success",
        "message": f"{user.name} is now a {role_label}",
        "new_role": request.role,
        "user_id": user.id,
    }


@router.patch("/{user_id}/staff")
async def set_user_staff(
    user_id: int,
    request: SetStaffRequest,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Grant or revoke Staff independently of the community role above — a
    user can be moderator AND staff, or staff alone, etc. Staff isn't just
    a badge: it actually raises the referral commission rate to 50% (same
    as is_partner — see CommissionService._get_rate_for_referrer), and
    that real rate is what shows on the user's own Earnings tab, not a
    hardcoded placeholder. Cannot change your own staff status or another
    admin's.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    caller_id = (
        current_user.get("id") or current_user.get("user", {}).get("id")
        if isinstance(current_user, dict)
        else current_user.id
    )

    if user.id == caller_id:
        raise HTTPException(
            status_code=400, detail="Cannot change your own staff status"
        )

    if user.is_admin:
        raise HTTPException(
            status_code=400, detail="Cannot change the staff status of a platform admin"
        )

    user.is_staff = request.is_staff
    db.commit()

    return {
        "status": "success",
        "message": f"{user.name} is {'now' if request.is_staff else 'no longer'} Staff",
        "is_staff": user.is_staff,
        "user_id": user.id,
    }

@router.patch("/{user_id}/partner")
async def set_user_partner(
    user_id: int,
    request: SetPartnerRequest,
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Make a user a partner, or remove it, the same way as Staff. A partner
    earns a 50% Builder Bonus rate on their referrals and gets Premium free
    for 6 calendar months from the day they become a partner (see
    subscriptions/partner_service.py); any Stripe subscription they pay for
    is paused for those 6 months. Removing it ends both straight away and
    resumes that Stripe billing.
    Cannot change your own partner status or another admin's.
    """
    from subscriptions.partner_service import grant_partner, revoke_partner

    # 0. Find the user and refuse changes to yourself or another admin.
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    caller_id = (
        current_user.get("id") or current_user.get("user", {}).get("id")
        if isinstance(current_user, dict)
        else current_user.id
    )

    if user.id == caller_id:
        raise HTTPException(
            status_code=400, detail="Cannot change your own partner status"
        )

    if user.is_admin:
        raise HTTPException(
            status_code=400, detail="Cannot change the partner status of a platform admin"
        )

    # 1. Grant: partner status, 6 months of free Premium, Stripe billing paused.
    if request.is_partner:
        result = grant_partner(db, user)
        until = user.partner_premium_until.strftime("%d %B %Y") if user.partner_premium_until else None
        message = f"{user.name} is now a Partner: 50% builder bonus, Premium free until {until}"
        if result["stripe_paused"]:
            message += f". Stripe billing paused until then ({result['stripe_paused']} subscription(s))"
    # 2. Revoke: both end now, and paused Stripe billing resumes.
    else:
        result = revoke_partner(db, user)
        message = f"{user.name} is no longer a Partner"
        if result["stripe_resumed"]:
            message += f". Stripe billing resumed ({result['stripe_resumed']} subscription(s))"

    # 3. Tell the admin page what changed.

    return {
        "status": "success",
        "message": message,
        "is_partner": bool(user.is_partner),
        "partner_since": user.partner_since.isoformat() if user.partner_since else None,
        "partner_premium_until": user.partner_premium_until.isoformat() if user.partner_premium_until else None,
        "user_id": user.id,
    }
