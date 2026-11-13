"""
Admin "Email a user" page: find a user, write a subject and message, send.
Every email sent is recorded (admin_sent_emails) and listed on the page.

  GET  /api/control/user-emails/users?search=...   find users by name or email
  POST /api/control/user-emails                     send an email to one user
  GET  /api/control/user-emails                     emails admins sent, newest first
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.routes.dependencies import admin_required
from database.pg_connections import get_db
from database.pg_models import AdminSentEmail, User

router = APIRouter(prefix="/control/user-emails", tags=["admin-user-emails"])


class SendEmailRequest(BaseModel):
    """The email an admin writes."""
    user_id: int
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=10000)


def _email_view(e: AdminSentEmail) -> dict:
    """One sent email for the page."""
    return {"id": e.id, "user_id": e.user_id, "to_email": e.to_email, "subject": e.subject, "message": e.message,
            "status": e.status, "sent_by": e.sent_by, "created_at": e.created_at.isoformat() if e.created_at else None}


@router.get("/users")
def find_users(search: str = "", admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Up to 10 users whose name or email contains the search text."""
    # 1. Need at least 2 characters.
    term = search.strip()
    if len(term) < 2:
        return {"success": True, "data": []}
    # 2. Match name or email, case-insensitive.
    like = f"%{term}%"
    users = (db.query(User).filter(or_(User.email.ilike(like), User.name.ilike(like)))
             .order_by(User.name).limit(10).all())
    return {"success": True, "data": [{"id": u.id, "name": u.name, "email": u.email,
                                       "plan": u.subscription_plan, "status": u.subscription_status} for u in users]}


@router.post("")
def send_email(body: SendEmailRequest, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Send the admin's email to one user and record it."""
    from emailing.email_service import email_service

    # 1. The user must exist and have an email address.
    user = db.get(User, body.user_id)
    if not user or not user.email:
        raise HTTPException(status_code=404, detail="User not found, or they have no email address")
    # 2. Send it (Resend, then SMTP; logged only if neither is set up).
    result = email_service.send_admin_message(user.email, user.name, body.subject.strip(), body.message.strip())
    status = (result or {}).get("status", "failed")
    # 3. Record it, whatever happened.
    record = AdminSentEmail(user_id=user.id, to_email=user.email, subject=body.subject.strip(),
                            message=body.message.strip(), status=status, sent_by=admin.id)
    db.add(record)
    db.commit()
    # 4. "logged" means no email service is configured: say so plainly.
    if status == "logged":
        return {"success": True, "data": _email_view(record),
                "warning": "No email service is set up on this server, so the email was only logged, not delivered."}
    return {"success": True, "data": _email_view(record)}


@router.get("")
def sent_emails(limit: int = 50, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Emails admins sent, newest first."""
    rows = db.query(AdminSentEmail).order_by(AdminSentEmail.created_at.desc()).limit(max(1, min(limit, 200))).all()
    return {"success": True, "data": [_email_view(e) for e in rows]}
