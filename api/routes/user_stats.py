# api/routes/user_stats.py
"""
User Statistics API Routes
Provides user-specific stats like total analyses count.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.pg_connections import get_db
from db.pg_models import BusinessAnalysis, User, Commission
from api.routes.login import get_current_user

router = APIRouter(prefix="/api/user", tags=["User Stats"])


@router.get("/stats")
async def get_user_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's statistics.

    Returns:
        - total_analyses: Count of user's business analyses
        - avg_confidence: Average confidence score
        - total_duration: Total time spent on analyses
    """
    try:
        # Get user ID
        if isinstance(current_user, dict):
            user_obj = current_user.get("user")
            user_id = user_obj.id if user_obj else None
        else:
            user_id = current_user.id

        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Count total analyses
        total_analyses = db.query(func.count(BusinessAnalysis.id)).filter(
            BusinessAnalysis.user_id == user_id
        ).scalar()

        # Calculate average confidence score
        avg_confidence = db.query(func.avg(BusinessAnalysis.confidence_score)).filter(
            BusinessAnalysis.user_id == user_id,
            BusinessAnalysis.confidence_score.isnot(None)
        ).scalar()

        # Get all analyses for this user
        analyses = db.query(BusinessAnalysis).filter(
            BusinessAnalysis.user_id == user_id
        ).all()

        # Calculate total duration (parse duration strings like "116.7s")
        total_seconds = 0
        for analysis in analyses:
            if analysis.duration:
                try:
                    # Parse format like "116.7s" or "2.5s"
                    duration_str = analysis.duration.replace('s', '').strip()
                    total_seconds += float(duration_str)
                except (ValueError, AttributeError):
                    pass

        # Calculate total commissions (all status)
        total_commissions = db.query(func.sum(Commission.amount)).filter(
            Commission.user_id == user_id
        ).scalar() or 0.0

        # Calculate paid commissions
        paid_commissions = db.query(func.sum(Commission.amount)).filter(
            Commission.user_id == user_id,
            Commission.status == 'paid'
        ).scalar() or 0.0

        return {
            "total_analyses": total_analyses or 0,
            "avg_confidence": int(avg_confidence) if avg_confidence else 0,
            "total_duration_seconds": int(total_seconds),
            "total_duration_formatted": f"{int(total_seconds / 60)}m {int(total_seconds % 60)}s" if total_seconds > 60 else f"{int(total_seconds)}s",
            "total_commissions": float(total_commissions),
            "paid_commissions": float(paid_commissions)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
