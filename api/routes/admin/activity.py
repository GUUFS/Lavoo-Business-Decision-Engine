"""
Admin Activity page: who did what from the admin end, and when
(records written by api/services/admin_activity.py).

  GET /api/control/activity?search=&admin_id=&failed_only=&limit=&offset=
      newest first, plus the admin team for the person filter (each stamp
      carries the person's role at the time, e.g. "Finance")
"""
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.routes.dependencies import admin_required
from database.pg_connections import get_db
from database.pg_models import AdminActivity, User

router = APIRouter(prefix="/control/activity", tags=["admin-activity"])


def _view(a: AdminActivity) -> dict:
    """One stamp for the page."""
    return {"id": a.id, "admin_id": a.admin_id, "admin_name": a.admin_name, "admin_email": a.admin_email,
            "admin_role": a.admin_role, "action": a.action, "method": a.method, "path": a.path, "status_code": a.status_code,
            "succeeded": a.succeeded, "ip_address": a.ip_address,
            "created_at": a.created_at.isoformat() if a.created_at else None}


@router.get("")
def list_activity(search: str = "", admin_id: int | None = None, failed_only: bool = False,
                  limit: int = 50, offset: int = 0, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Admin actions, newest first, with optional filters."""
    # 1. Filters: text (action, path, admin name/email), one admin, failures only.
    query = db.query(AdminActivity)
    if search.strip():
        like = f"%{search.strip()}%"
        query = query.filter(or_(AdminActivity.action.ilike(like), AdminActivity.path.ilike(like),
                                 AdminActivity.admin_name.ilike(like), AdminActivity.admin_email.ilike(like)))
    if admin_id:
        query = query.filter(AdminActivity.admin_id == admin_id)
    if failed_only:
        query = query.filter(AdminActivity.succeeded.is_(False))
    # 2. One page, newest first.
    total = query.count()
    rows = query.order_by(AdminActivity.created_at.desc(), AdminActivity.id.desc()) \
        .offset(max(0, offset)).limit(max(1, min(limit, 200))).all()
    # 3. For the person filter: the whole admin team, plus anyone in the log who has since left it.
    people = {u.id: {"id": u.id, "name": u.name, "email": u.email}
              for u in db.query(User).filter(User.is_admin.is_(True)).all()}
    for a in (db.query(AdminActivity.admin_id, AdminActivity.admin_name, AdminActivity.admin_email)
              .filter(AdminActivity.admin_id.isnot(None)).distinct().all()):
        people.setdefault(a.admin_id, {"id": a.admin_id, "name": a.admin_name, "email": a.admin_email})
    admins = sorted(people.values(), key=lambda p: (p["name"] or "").lower())
    return {"success": True, "data": [_view(a) for a in rows], "total": total, "admins": admins}
