# api/routes/user_stats.py
"""
User Statistics API Routes
Provides user-specific stats like total analyses count.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.pg_connections import get_db
from db.pg_models import BusinessAnalysis, User, Commission, Referral
from api.routes.login import get_current_user

router = APIRouter(prefix="/api/user", tags=["User Stats"])


@router.get("/stats")
async def get_user_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Get user ID robustly (matching business_analyzer logic)
        user_id = None
        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
            if not user_id and "user" in current_user:
                user_data = current_user["user"]
                if isinstance(user_data, dict):
                    user_id = user_data.get("id") or user_data.get("user_id")
                elif hasattr(user_data, 'id'):
                    user_id = user_data.id
        elif hasattr(current_user, "id"):
             user_id = current_user.id
        
        # Handle string 'sub' (email or id)
        if user_id and str(user_id).isdigit():
            user_id = int(str(user_id))
        elif user_id and "@" in str(user_id):
             # Resolve email to ID
             user_obj = db.query(User).filter(User.email == str(user_id)).first()
             if user_obj:
                 user_id = user_obj.id
             else:
                 print(f"[WARN] Stats: User not found for email {user_id}")
                 user_id = None

        if not user_id:
             print(f"[WARN] Stats: Could not resolve user_id from token: {current_user}")
             raise HTTPException(status_code=401, detail="User identity not found in token")

        print(f"[INFO] Stats: Fetching for user_id={user_id}")

        # 1. Analyses Stats (Handle missing/bad data gracefully)
        # 1. Analyses Stats (Handle missing/bad data gracefully)
        total_analyses = 0
        avg_confidence = 0
        total_seconds = 0.0
        
        try:
            print(f"[DEBUG] Executing Analysis Count Query for user_id={user_id}...")
            total_analyses = db.query(func.count(BusinessAnalysis.id)).filter(
                BusinessAnalysis.user_id == user_id
            ).scalar() or 0
            print(f"[DEBUG] Analysis Count Result: {total_analyses}")
            
        except Exception as e:
             print(f"[ERROR] Failed to count analyses for user {user_id}: {e}")
             import traceback
             traceback.print_exc()

        try:
            avg_confidence = db.query(func.avg(BusinessAnalysis.confidence_score)).filter(
                BusinessAnalysis.user_id == user_id,
                BusinessAnalysis.confidence_score.isnot(None)
            ).scalar() or 0
            
            # Safe duration verification
            analyses_with_duration = db.query(BusinessAnalysis.duration).filter(
                BusinessAnalysis.user_id == user_id,
                BusinessAnalysis.duration.isnot(None)
            ).all()

            for row in analyses_with_duration:
                if row.duration and isinstance(row.duration, str):
                    try:
                        cleaned = row.duration.lower().replace('s', '').strip()
                        total_seconds += float(cleaned)
                    except ValueError:
                        pass
        except Exception as e:
            print(f"[ERROR] Analysis stats partial fail (confidence/duration) for user {user_id}: {e}")
            # Do not re-raise, partial stats are better than none

        # 2. Commission Stats (CRITICAL FIX: Sum all valid statuses)
        total_commissions = 0.0
        paid_commissions = 0.0
        
        try:
            # Sum 'paid', 'pending', 'processing', 'approved'
            total_commissions = db.query(func.sum(Commission.amount)).filter(
                Commission.user_id == user_id,
                Commission.status.in_(['paid', 'pending', 'processing', 'approved']) 
            ).scalar() or 0.0

            paid_commissions = db.query(func.sum(Commission.amount)).filter(
                Commission.user_id == user_id,
                Commission.status == 'paid'
            ).scalar() or 0.0
            
        except Exception as e:
             print(f"[WARN] Commission/Referral stats partial fail for user {user_id}: {e}")
             import traceback
             traceback.print_exc()

        # 3. ✅ NEW: Referral Stats
        total_referrals = 0
        referrals_this_month = 0
        
        try:
            # Method A: Use the synced count from User table (Fastest/Safest)
            user_obj = db.query(User).filter(User.id == user_id).first()
            if user_obj:
                total_referrals = user_obj.referral_count or 0
            
            # Method B: Verify with Referral table (Optional, but good for "this month")
            # referrals_count_db = db.query(func.count(Referral.id)).filter(
            #    Referral.referrer_id == user_id
            # ).scalar() or 0
            
            # Count referrals this month
            from datetime import datetime
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            referrals_this_month = db.query(func.count(Referral.id)).filter(
                Referral.referrer_id == user_id,
                Referral.created_at >= month_start
            ).scalar() or 0
            
        except Exception as e:
            print(f"[WARN] Referral stats partial fail for user {user_id}: {e}")

        result = {
            "total_analyses": int(total_analyses),
            "avg_confidence": int(avg_confidence),
            "total_duration_seconds": int(total_seconds),
            "total_duration_formatted": f"{int(total_seconds / 60)}m {int(total_seconds % 60)}s" if total_seconds > 60 else f"{int(total_seconds)}s",
            "total_commissions": float(total_commissions),
            "paid_commissions": float(paid_commissions),
            
            # ✅ NEW: Add referral data
            "total_referrals": int(total_referrals),
            "referrals_this_month": int(referrals_this_month)
        }
        
        print(f"[DEBUG] /api/user/stats SUCCESS for user_id={user_id}: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/user/stats CRITICAL FAIL: {e}")
        import traceback
        traceback.print_exc()
        # Return valid zero structure to prevent dashboard crash
        return {
            "total_analyses": 0,
            "avg_confidence": 0,
            "total_duration_seconds": 0,
            "total_duration_formatted": "0s",
            "total_commissions": 0.0,
            "paid_commissions": 0.0,
            "total_referrals": 0,
            "referrals_this_month": 0
        }