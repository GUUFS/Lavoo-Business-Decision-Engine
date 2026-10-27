import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta, timezone

from database.pg_connections import get_db
from database.pg_models import User, Commission, Ticket, Review, Subscriptions, Payout
from api.routes.dependencies import admin_required

router = APIRouter(prefix="/admin/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Get real-time system statistics for the admin dashboard.
    """
    try:
        # 1. Total Users (excluding deactivated if preferred, but usually Total means all)
        total_users = db.query(User).count()
        
        # 2. Total Revenue (Sum of paid commissions - this is a proxy for platform revenue if we take a cut, 
        #    or just total volume. Adjust logic if 'revenue' means platform profit vs total payouts).
        #    Let's assume Revenue = Total Paid Commissions for now, or maybe Subscription revenue?
        #    For this MVP, let's use Total Paid Commissions as a metric of activity.
        #    Or if we have Subscription tables, use that.
        #    Let's check models... Commission has 'amount'.
        # 2. Total Revenue
        # 2. Total Revenue
        try:
            # Grouped by currency — summing Subscriptions.amount across NGN/
            # USD/GBP with no group_by blends incompatible currencies into
            # one meaningless number (same bug class fixed in
            # admin/revenue.py's /stats this session, missed here). Status
            # filter also widened to cover every provider's spelling of
            # "paid" — Flutterwave writes 'successful'/'succeeded', never
            # 'active'/'paid', so every NGN subscription was previously
            # excluded entirely.
            revenue_rows = db.query(
                Subscriptions.currency,
                func.sum(Subscriptions.amount)
            ).filter(
                Subscriptions.status.in_(['active', 'completed', 'paid', 'successful', 'succeeded'])
            ).group_by(Subscriptions.currency).all()
            revenue_by_currency = {(row[0] or 'USD'): float(row[1] or 0) for row in revenue_rows}

            payout_rows = db.query(
                Payout.currency,
                func.sum(Payout.amount)
            ).filter(
                Payout.status == 'completed'
            ).group_by(Payout.currency).all()
            payouts_by_currency = {(row[0] or 'USD'): float(row[1] or 0) for row in payout_rows}

            total_revenue_by_currency = {
                ccy: revenue_by_currency.get(ccy, 0.0) - payouts_by_currency.get(ccy, 0.0)
                for ccy in set(revenue_by_currency) | set(payouts_by_currency)
            }
        except Exception as ex:
            logger.warning(f"Revenue calc error: {ex}")
            total_revenue_by_currency = {}

        # 3. Active Users (Active in last 30 days)
        # Ensure timezone awareness for PostgreSQL timestamptz comparison
        try:
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            # active_users = db.query(User).filter(User.updated_at >= thirty_days_ago).count()
            # Use 'created_at' as fallback if 'updated_at' causes issues, but updated_at should be fine.
            # Adding logging to trace execution
            active_users = db.query(User).filter(User.updated_at >= thirty_days_ago).count()
        except Exception as ex:
            logger.warning(f"Active users calc error: {ex}")
            active_users = 0

        # 4. System Uptime
        system_uptime = "99.9%"

        # 5. Recent Activity (Mix of new users and recent tickets)
        try:
            recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
            recent_tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).limit(5).all()
            
            activity_stream = []
            for u in recent_users:
                activity_stream.append({
                    "action": "New user registered",
                    "user": u.name or u.email,
                    "time": u.created_at.isoformat() if u.created_at else None,
                    "type": "new_user"
                })
            for t in recent_tickets:
                activity_stream.append({
                    "action": f"Support ticket: {(t.issue or 'General inquiry')[:40]}",
                    "user": t.user.name if hasattr(t, 'user') and t.user else f"User #{t.user_id}",
                    "time": t.created_at.isoformat() if t.created_at else None,
                    "type": "new_ticket"
                })
                
            # Sort combined activity by time desc
            activity_stream.sort(key=lambda x: x['time'] or '', reverse=True)
            activity_stream = activity_stream[:10]
        except Exception as ex:
             logger.warning(f"Activity stream error: {ex}")
             activity_stream = []

        return {
            "total_users": total_users,
            "total_revenue_by_currency": total_revenue_by_currency,
            "active_users": active_users,
            "system_uptime": system_uptime,
            "recent_activity": activity_stream
        }

    except Exception as e:
        logger.warning(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard stats: {str(e)}")
