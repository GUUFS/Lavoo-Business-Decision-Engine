"""
Admin Contact Management API Routes
Provides endpoints for viewing, filtering, searching, and replying to contact inquiries
using Resend email dispatch from hello@lavoo.io.
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func

from database.pg_connections import get_db
from database.pg_models import ContactMessage, User
from api.routes.dependencies import admin_required
from emailing.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/control/contact", tags=["admin-contact"])


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class ContactReplyRequest(BaseModel):
    reply_message: str = Field(..., min_length=2, max_length=10000, description="Response text to send to user")
    subject: Optional[str] = Field(None, max_length=255, description="Optional custom email subject")
    new_status: Optional[str] = Field("replied", description="Updated status after reply (e.g. 'replied' or 'resolved')")


class UpdateContactStatusRequest(BaseModel):
    status: str = Field(..., description="Status value: unread, in_progress, replied, resolved, archived")


# ─── Helper Functions ────────────────────────────────────────────────────────

def _format_relative_time(dt: Optional[datetime]) -> str:
    if not dt:
        return "Never"
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    diff = datetime.utcnow() - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    elif seconds < 604800:
        return f"{seconds // 86400}d ago"
    else:
        return dt.strftime("%b %d, %Y")


def _serialize_contact_message(c: ContactMessage) -> Dict[str, Any]:
    replies = getattr(c, 'admin_replies', None) or []
    if isinstance(replies, str):
        import json
        try:
            replies = json.loads(replies)
        except Exception:
            replies = []

    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "company": c.company,
        "reason": c.reason or "general",
        "subject": c.subject,
        "message": c.message,
        "status": c.status or "unread",
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "last_replied_at": c.last_replied_at.isoformat() if c.last_replied_at else None,
        "last_replied_by": c.last_replied_by,
        "relative_time": _format_relative_time(c.created_at),
        "reply_count": len(replies),
        "admin_replies": replies,
        "notes": c.notes,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("")
async def list_contact_inquiries(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    reason: Optional[str] = Query(None),
    current_admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get paginated contact messages with stats, search, and category/status filtering.
    """
    query = db.query(ContactMessage)

    # Status filter
    if status and status.strip() and status.lower() != 'all':
        query = query.filter(ContactMessage.status == status.strip().lower())

    # Category / Reason filter
    if reason and reason.strip() and reason.lower() != 'all':
        query = query.filter(ContactMessage.reason == reason.strip().lower())

    # Search filter across name, email, company, subject, and message
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(ContactMessage.name).like(term),
                func.lower(ContactMessage.email).like(term),
                func.lower(ContactMessage.company).like(term),
                func.lower(ContactMessage.subject).like(term),
                func.lower(ContactMessage.message).like(term),
            )
        )

    total = query.count()
    items_raw = query.order_by(desc(ContactMessage.created_at)).offset((page - 1) * limit).limit(limit).all()

    # Calculate global summary stats
    total_all = db.query(ContactMessage).count()
    unread_count = db.query(ContactMessage).filter(ContactMessage.status == "unread").count()
    replied_count = db.query(ContactMessage).filter(ContactMessage.status == "replied").count()
    resolved_count = db.query(ContactMessage).filter(ContactMessage.status == "resolved").count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(ContactMessage).filter(ContactMessage.created_at >= today_start).count()

    return {
        "success": True,
        "items": [_serialize_contact_message(item) for item in items_raw],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 1,
        "stats": {
            "total": total_all,
            "unread": unread_count,
            "replied": replied_count,
            "resolved": resolved_count,
            "today": today_count,
        }
    }


@router.get("/{inquiry_id}")
async def get_contact_inquiry_detail(
    inquiry_id: int,
    current_admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get detailed information and full reply thread for a single contact message.
    """
    msg = db.query(ContactMessage).filter_by(id=inquiry_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact inquiry not found")

    return {
        "success": True,
        "data": _serialize_contact_message(msg)
    }


@router.post("/{inquiry_id}/reply")
async def reply_to_contact_inquiry(
    inquiry_id: int,
    payload: ContactReplyRequest,
    current_admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Reply to a contact inquiry by sending an email directly to the user from hello@lavoo.io via Resend.
    Logs the reply to the conversation thread and updates message status.
    """
    msg = db.query(ContactMessage).filter_by(id=inquiry_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact inquiry not found")

    clean_reply = payload.reply_message.strip()
    admin_display_name = current_admin.name or current_admin.username or "Lavoo Support Team"

    # 1. Dispatch email via Resend (from hello@lavoo.io)
    send_result = email_service.send_contact_reply_via_resend(
        user_email=msg.email,
        name=msg.name,
        reply_message=clean_reply,
        original_message=msg.message,
        subject=payload.subject or msg.subject,
        reason=msg.reason,
        admin_name=admin_display_name
    )

    # 2. Append reply entry to DB JSON history
    existing_replies = getattr(msg, 'admin_replies', None) or []
    if not isinstance(existing_replies, list):
        existing_replies = []

    now_iso = datetime.now(timezone.utc).isoformat()
    new_reply_entry = {
        "id": str(uuid.uuid4())[:8],
        "admin_id": current_admin.id,
        "admin_name": admin_display_name,
        "admin_email": current_admin.email,
        "message": clean_reply,
        "sent_at": now_iso,
        "resend_id": send_result.get("message_id") if isinstance(send_result, dict) else None,
    }

    # Assign new list to trigger SQLAlchemy JSON dirty detection
    msg.admin_replies = existing_replies + [new_reply_entry]
    msg.last_replied_at = datetime.now(timezone.utc)
    msg.last_replied_by = admin_display_name
    msg.status = (payload.new_status or "replied").strip().lower()

    db.add(msg)
    db.commit()
    db.refresh(msg)

    logger.info(f"✅ Admin #{current_admin.id} ({admin_display_name}) replied to Contact Inquiry #{msg.id} ({msg.email}) via Resend")

    return {
        "success": True,
        "message": f"Reply successfully sent to {msg.email} from hello@lavoo.io",
        "data": _serialize_contact_message(msg),
        "email_delivery": send_result
    }


@router.patch("/{inquiry_id}/status")
async def update_contact_inquiry_status(
    inquiry_id: int,
    payload: UpdateContactStatusRequest,
    current_admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Update status of a contact inquiry (unread, in_progress, replied, resolved, archived).
    """
    msg = db.query(ContactMessage).filter_by(id=inquiry_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact inquiry not found")

    new_status = payload.status.strip().lower()
    valid_statuses = {"unread", "in_progress", "replied", "resolved", "archived"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{new_status}'. Allowed: {', '.join(valid_statuses)}"
        )

    msg.status = new_status
    if new_status == "resolved" and not msg.resolved_at:
        msg.resolved_at = datetime.now(timezone.utc)
    elif new_status != "resolved":
        msg.resolved_at = None

    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        "success": True,
        "data": _serialize_contact_message(msg)
    }


@router.delete("/{inquiry_id}")
async def delete_contact_inquiry(
    inquiry_id: int,
    current_admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Delete a contact inquiry record.
    """
    msg = db.query(ContactMessage).filter_by(id=inquiry_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact inquiry not found")

    db.delete(msg)
    db.commit()

    return {
        "success": True,
        "message": f"Contact inquiry #{inquiry_id} deleted"
    }
