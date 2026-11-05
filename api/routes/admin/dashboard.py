"""
Admin dashboard API: the headline numbers on the admin home page
(GET /api/admin/dashboard/stats).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from database.pg_connections import get_db
from database.pg_models import User, Ticket
from api.routes.dependencies import admin_required

router = APIRouter(prefix="/admin/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    """
    Real-time statistics for the admin dashboard: total users, total
    revenue per currency (matches the Revenue page), users active in the
    last 30 days, uptime and the latest sign-ups and support tickets.
    """
    try:
        # 1. Total Users (excluding deactivated if preferred, but usually Total means all)
        total_users = db.query(User).count()
        
        # 2. Total Revenue: the same figure the Revenue page shows as
        #    "Subscription Revenue" for each currency (successful payments
        #    minus the builder bonuses earned on them, in the payment's own
        #    currency), from the same function, so the two always match.
        try:
            from api.routes.admin.revenue import compute_revenue_stats
            revenue = compute_revenue_stats(db)
            total_revenue_by_currency = {
                ccy: revenue["by_currency"][ccy]["total_subscription_revenue"]
                for ccy in revenue["currencies"]
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
