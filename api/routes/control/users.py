
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime, timedelta

from db.pg_connections import get_db
from db.pg_models import User, Subscriptions, BusinessAnalysis
from api.routes.login import get_current_user

router = APIRouter(prefix="/api/control/users", tags=["admin-users"])

def verify_admin(current_user):
    """Verify user is admin"""
    is_admin = False
    if hasattr(current_user, 'is_admin'):
        is_admin = current_user.is_admin
    elif isinstance(current_user, dict):
         user_data = current_user.get("user", current_user)
         if isinstance(user_data, dict):
             is_admin = user_data.get("is_admin", False)
         elif hasattr(user_data, 'is_admin'):
             is_admin = user_data.is_admin
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user statistics"""
    verify_admin(current_user)
    
    try:
        total_users = db.query(func.count(User.id)).scalar()
        
        # Pro Users: subscription_status == 'active'
        pro_users = db.query(func.count(User.id)).filter(
            User.subscription_status == 'active'
        ).scalar()
        
        # Free Users: subscription_status != 'active' (covers free, null, etc.)
        free_users = db.query(func.count(User.id)).filter(
            or_(User.subscription_status != 'active', User.subscription_status.is_(None))
        ).scalar()
        
        # Deactivated Users
        deactivated_users = db.query(func.count(User.id)).filter(User.is_active == False).scalar()

        # Inactive Users (Dormant > 90 days)
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        inactive_users = db.query(func.count(User.id)).filter(
            or_(User.updated_at < cutoff_date, User.updated_at.is_(None))
        ).scalar()
        
        return {
            "total": total_users,
            "pro": pro_users,
            "free": free_users,
            "deactivated": deactivated_users,
            "inactive": inactive_users
        }
        
    except Exception as e:
        print(f"Error in user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_user_details(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full user details for modal"""
    verify_admin(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Calculate days remaining
    days_remaining = 0
    if user.subscriptions:
        # Find active subscription
        active_sub = next((sub for sub in user.subscriptions if sub.status == 'active'), None)
        if active_sub and active_sub.end_date:
             delta = active_sub.end_date.replace(tzinfo=None) - datetime.utcnow()
             days_remaining = max(0, delta.days)
    
    # Get Referrals from the user (names)
    # referral.referrer_id = user.id
    # We want referred_user.name
    from db.pg_models import Referral
    referrals = db.query(Referral).filter(Referral.referrer_id == user.id).all()
    referral_names = [ref.referred_user.name for ref in referrals if ref.referred_user]
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "joinDate": user.created_at.isoformat(),
        "subscription_status": user.subscription_status,
        "subscription_plan": user.subscription_plan,
        "total_chops": user.total_chops,
        "referral_chops": user.referral_chops,
        "alert_reading_chops": user.alert_reading_chops,
        "insight_reading_chops": user.insight_reading_chops,
        "referral_count": user.referral_count,
        "referrals": referral_names,
        "insight_sharing_chops": user.insight_sharing_chops,
        "alert_sharing_chops": user.alert_sharing_chops,
        "days_remaining": days_remaining,
        "referral_code": user.referral_code,
        "is_active": user.is_active
    }

@router.get("")
async def get_users(
    limit: int = 10,
    page: int = 1,
    search: str = None,
    status: str = None, # 'active', 'inactive', 'suspended'
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get users with pagination and filtering"""
    verify_admin(current_user)
    
    offset = (page - 1) * limit
    
    query = db.query(User)
    
    # Search
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_term)) | 
            (User.email.ilike(search_term))
        )
    
    # Status Filter
    if status and status != 'all':
        if status == 'active':
            query = query.filter(User.is_active == True)
        elif status == 'inactive': # Dormant users (3 months)
             cutoff_date = datetime.utcnow() - timedelta(days=90)
             query = query.filter(or_(User.updated_at < cutoff_date, User.updated_at.is_(None)))
        elif status == 'suspended':
             query = query.filter(User.is_active == False)
        # Handle explicitly 'deactivated' if passed, mapping to suspended logic
        elif status == 'deactivated':
             query = query.filter(User.is_active == False)
        elif status == 'free':
             query = query.filter(or_(User.subscription_status != 'active', User.subscription_status.is_(None)))
        elif status == 'pro':
             query = query.filter(User.subscription_status == 'active')
    
    total = query.count()
    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for user in users:
        # Get Analysis Count
        analysis_count = db.query(func.count(BusinessAnalysis.id)).filter(
            BusinessAnalysis.user_id == user.id
        ).scalar()
        
        # Determine status string
        if not user.is_active:
             user_status = 'suspended' # or 'inactive'
        else:
             user_status = 'active'
        
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan": user.subscription_plan or "Free",
            "status": user_status,
            "joinDate": user.created_at.strftime("%Y-%m-%d"),
            "lastActive": user.updated_at.strftime("%Y-%m-%d %H:%M") if user.updated_at else "Never", # Fallback
            "analyses": analysis_count,
            "avatar": ''.join([n[0] for n in user.name.split(' ')[:2]]).upper() # Initials
        })
        
    return {
        "users": result,
        "total": total,
        "page": page,
        "limit": limit,
        "totalPages": (total + limit - 1) // limit
    }

@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle user active status (Deactivate/Activate)"""
    verify_admin(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent deactivating self if admin
    user_id_from_token = None
    if isinstance(current_user, dict):
        user_id_from_token = current_user.get("id") or current_user.get("user", {}).get("id")
    else:
        user_id_from_token = current_user.id
        
    if user.id == user_id_from_token:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account")
    
    # Toggle
    user.is_active = not user.is_active
    db.commit()
    
    action = "activated" if user.is_active else "deactivated"
    start_status = "active" if user.is_active else "suspended"
    
    return {
        "status": "success", 
        "message": f"User {user.email} has been {action}",
        "new_status": start_status
    }
