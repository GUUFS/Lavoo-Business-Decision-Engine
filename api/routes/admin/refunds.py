"""
Admin Refunds page: recent Stripe payments, everything about one payment,
and refunding it (logic in subscriptions/admin_refunds.py).

  GET  /api/control/refunds/payments                    recent payments
  GET  /api/control/refunds/payments/{charge_id}        one payment, in full
  POST /api/control/refunds/payments/{charge_id}/refund refund it
  GET  /api/control/refunds/history                     refunds admins made

The endpoints are plain functions (not async), so FastAPI runs the slow
Stripe calls in a worker thread instead of blocking the server.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.routes.dependencies import admin_required
from database.pg_connections import get_db
from subscriptions import admin_refunds

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/control/refunds", tags=["admin-refunds"])


class RefundRequest(BaseModel):
    """Why the payment is being refunded."""
    reason: str = Field("requested_by_customer", pattern="^(requested_by_customer|duplicate|fraudulent)$")
    note: str | None = Field(None, max_length=1000)


def _stripe_error(e: Exception) -> HTTPException:
    """A Stripe or lookup failure as a readable error for the admin page."""
    logger.warning(f"[refunds] {e}")
    return HTTPException(status_code=502, detail=f"Stripe said: {getattr(e, 'user_message', None) or e}")


@router.get("/payments")
def list_payments(limit: int = 25, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """The latest Stripe payments, newest first."""
    try:
        return {"success": True, "data": admin_refunds.recent_payments(db, limit=max(1, min(limit, 100)))}
    except Exception as e:
        raise _stripe_error(e) from e


@router.get("/payments/{charge_id}")
def get_payment(charge_id: str, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Everything about one payment: who, card, fee, why it was charged, our records."""
    try:
        return {"success": True, "data": admin_refunds.payment_details(db, charge_id)}
    except Exception as e:
        raise _stripe_error(e) from e


@router.post("/payments/{charge_id}/refund")
def refund(charge_id: str, body: RefundRequest, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Refund the payment in full, stop future charges, end access now and
    cancel (or claw back) the referrer's commission."""
    # 1. A payment that can't be refunded is a 400 with the reason.
    try:
        result = admin_refunds.refund_payment(db, charge_id, admin.id, body.reason, body.note)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    # 2. Stripe failed: nothing in our records was changed before the refund itself.
    except Exception as e:
        db.rollback()
        raise _stripe_error(e) from e
    return {"success": True, "data": result}


@router.get("/history")
def history(limit: int = 50, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Refunds admins made, newest first, with the steps each one took."""
    return {"success": True, "data": admin_refunds.refund_history(db, limit=max(1, min(limit, 200)))}
