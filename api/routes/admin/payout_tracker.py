"""
Admin Payout Tracker page: what the payout system did with every payment
(logic in subscriptions/payout_tracker.py).

  GET /api/control/payout-tracker?show=all|with_commission|unpaid   payments, newest first
  GET /api/control/payout-tracker/commissions/{id}                  every try for one commission

For each payment it shows: who paid, how much and through which provider;
the referrer's commission (if any); the payout route (Flutterwave or Stripe);
whether it is cross-border (paid in another currency); what happened and why.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.routes.dependencies import admin_required
from database.pg_connections import get_db
from database.pg_models import Commission
from subscriptions import payout_tracker

router = APIRouter(prefix="/control/payout-tracker", tags=["admin-payout-tracker"])


@router.get("")
def list_payments(show: str = "all", limit: int = 50, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Recent payments and what the payout system did with each one."""
    # 1. Only the three known views.
    if show not in ("all", "with_commission", "unpaid"):
        raise HTTPException(status_code=400, detail="show must be all, with_commission or unpaid")
    # 2. The rows, plus the outcome labels for the page's legend.
    return {"success": True, "data": payout_tracker.tracker_rows(db, limit=max(1, min(limit, 200)), show=show),
            "labels": payout_tracker.OUTCOME_LABELS}


@router.get("/commissions/{commission_id}")
def commission_history(commission_id: int, admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Every try the payout system made for one commission, oldest first."""
    if not db.get(Commission, commission_id):
        raise HTTPException(status_code=404, detail="Commission not found")
    return {"success": True, "data": payout_tracker.commission_history(db, commission_id)}
