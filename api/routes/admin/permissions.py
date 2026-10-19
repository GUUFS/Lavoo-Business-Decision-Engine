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

ASSIGNABLE_ROLES = {UserRole.NORMAL.value, UserRole.MODERATOR.value, UserRole.STAFF.value}


class SetRoleRequest(BaseModel):
    role: str


@router.get("")
async def get_users_for_permissions(
    limit: int = 10,
    page: int = 1,
    search: str = "",
    role: str = "",          # filter: "moderator" | "staff" | "normal_user" | None = all
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """
    Return paginated users for the permissions management page.
    Includes role field so admin can see and toggle moderator status.
    """
    offset = (page - 1) * limit
    query = db.query(User)

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(User.name.ilike(term), User.email.ilike(term))
        )

    if role in ASSIGNABLE_ROLES:
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
    Assign a user's community role directly (normal_user / moderator /
    staff) rather than only toggling moderator on and off — STAFF marks
    someone with elevated trust/visibility (e.g. a Lavoo team member)
    without granting admin panel access, and is shown as a badge on that
    user's own profile (see User.role's own comment on pg_models.py).
    Cannot change your own role or another admin's role.
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