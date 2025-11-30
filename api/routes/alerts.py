from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime

from db.pg_connections import get_db
from db.pg_models import (User, Alert, Referral, UserAlert, UserResponse, UserCreate, AlertResponse, AlertCreate,
                            ViewAlertRequest, ShareAlertRequest, ChopsBreakdown, PinAlertRequest, UserPinnedAlert)
from api.routes.login import get_current_user

from typing import Optional, List

router = APIRouter(tags=["alerts"])

def is_pro_user(subscription_status: str) -> bool:
    return subscription_status == "active"


# API Endpoints
@router.get("/users/me")
def get_current_user_route(current_user=Depends(get_current_user)):
    user = current_user["user"]  # extract actual user object
    return {
        "id": user.id, 
        "email": user.email, 
        "subscription_status": user.subscription_status,
        "total_chops": user.total_chops,
        "alert_reading_chops": user.alert_reading_chops,
        "alert_sharing_chops": user.alert_sharing_chops,
        "insight_reading_chops": user.insight_reading_chops,
        "insight_sharing_chops": user.insight_sharing_chops,
        "referral_chops": user.referral_chops,
        "referral_count": user.referral_count
    }


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user details including chops breakdown"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/api/users/email/{email}", response_model=UserResponse)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Get user details by email"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/api/users/{user_id}/chops", response_model=ChopsBreakdown)
def get_user_chops(user_id: int, db: Session = Depends(get_db)):
    """Get detailed chops breakdown for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return ChopsBreakdown(
        total_chops=user.total_chops,
        alert_reading_chops=user.alert_reading_chops,
        alert_sharing_chops=user.alert_sharing_chops,
        insight_reading_chops=user.insight_reading_chops,
        insight_sharing_chops=user.insight_sharing_chops,
        referral_chops=user.referral_chops,
        referral_count=user.referral_count
    )


@router.post("/api/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    """Create a new alert"""
    db_alert = Alert(**alert.dict())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


@router.get("/api/alerts", response_model=List[AlertResponse])
def get_alerts(
    user_id: Optional[int] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all alerts with optional filtering and user interaction data"""
    # Use authenticated user's ID if not provided
    if not user_id:
        user_id = current_user["user"].id
    
    query = db.query(Alert).filter(Alert.is_active == True)
    
    if category:
        query = query.filter(Alert.category == category)
    if priority:
        query = query.filter(Alert.priority == priority)
    
    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get all pinned alerts for this user
    pinned_alert_ids = set(
        db.query(UserPinnedAlert.alert_id)
        .filter(UserPinnedAlert.user_id == user_id)
        .all()
    )

    pinned_alert_ids = {pid[0] for pid in pinned_alert_ids}

    # Always include user interaction data when authenticated
    result = []
    for alert in alerts:
        user_alert = db.query(UserAlert).filter(
            UserAlert.user_id == user_id,
            UserAlert.alert_id == alert.id
        ).first()
        
        # Mark as attended if ANY interaction exists
        is_attended = False
        if user_alert:
            is_attended = user_alert.has_viewed or user_alert.has_shared or user_alert.is_attended
        
        alert_dict = {
            "id": alert.id,
            "title": alert.title,
            "category": alert.category,
            "priority": alert.priority,
            "score": alert.score,
            "time_remaining": alert.time_remaining,
            "why_act_now": alert.why_act_now,
            "potential_reward": alert.potential_reward,
            "action_required": alert.action_required,
            "source": alert.source,
            "date": alert.date,
            "total_views": alert.total_views,
            "total_shares": alert.total_shares,
            "has_viewed": user_alert.has_viewed if user_alert else False,
            "has_shared": user_alert.has_shared if user_alert else False,
            "is_attended": is_attended,
            "is_pinned": alert.id in pinned_alert_ids
        }
        result.append(AlertResponse(**alert_dict))
    
    # Sort: pinned alerts first, then by created_at
    result.sort(key=lambda x: (not x.is_pinned, alerts[[a.id for a in alerts].index(x.id)].created_at), reverse=True)

    return result


@router.get("/api/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get a specific alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if user_id:
        user_alert = db.query(UserAlert).filter(
            UserAlert.user_id == user_id,
            UserAlert.alert_id == alert_id
        ).first()
        
        # Mark as attended if ANY interaction exists
        is_attended = False
        if user_alert:
            is_attended = user_alert.has_viewed or user_alert.has_shared or user_alert.is_attended
        
        alert_dict = {
            "id": alert.id,
            "title": alert.title,
            "category": alert.category,
            "priority": alert.priority,
            "score": alert.score,
            "time_remaining": alert.time_remaining,
            "why_act_now": alert.why_act_now,
            "potential_reward": alert.potential_reward,
            "action_required": alert.action_required,
            "source": alert.source,
            "date": alert.date,
            "total_views": alert.total_views,
            "total_shares": alert.total_shares,
            "has_viewed": user_alert.has_viewed if user_alert else False,
            "has_shared": user_alert.has_shared if user_alert else False,
            "is_attended": is_attended
        }
        return AlertResponse(**alert_dict)
    
    return alert


@router.post("/api/alerts/view")
def view_alert(request: ViewAlertRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark alert as viewed and award chops if first time"""
    # Get user and alert
    user = current_user["user"]
    alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Check if user_alert record exists
    user_alert = db.query(UserAlert).filter(
        UserAlert.user_id == user.id,
        UserAlert.alert_id == request.alert_id
    ).first()
    
    if not user_alert:
        # Create new record
        user_alert = UserAlert(
            user_id=user.id,
            alert_id=request.alert_id,
            has_viewed=True,
            is_attended=True,
            viewed_at=datetime.utcnow()
        )
        
        # Award chops based on subscription status (active = 5, free = 1)
        chops_to_award = 5 if is_pro_user(user.subscription_status) else 1
        user_alert.chops_earned_from_view = chops_to_award
        user.total_chops += chops_to_award
        user.alert_reading_chops += chops_to_award
        
        # Update alert view count
        alert.total_views += 1
        
        db.add(user_alert)
        db.commit()
        
        return {
            "message": "Alert viewed successfully",
            "chops_earned": chops_to_award,
            "total_chops": user.total_chops
        }
    else:
        # Already viewed, just mark as attended if not already
        if not user_alert.has_viewed:
            user_alert.has_viewed = True
            user_alert.viewed_at = datetime.utcnow()
            alert.total_views += 1
            
            # Award chops based on subscription status
            chops_to_award = 5 if is_pro_user(user.subscription_status) else 1
            user_alert.chops_earned_from_view = chops_to_award
            user.total_chops += chops_to_award
            user.alert_reading_chops += chops_to_award
            
            db.commit()
            
            return {
                "message": "Alert viewed successfully",
                "chops_earned": chops_to_award,
                "total_chops": user.total_chops
            }
        
        if not user_alert.is_attended:
            user_alert.is_attended = True
            db.commit()
        
        return {
            "message": "Alert already viewed",
            "chops_earned": 0,
            "total_chops": user.total_chops
        }


@router.post("/api/alerts/share")
def share_alert(request: ShareAlertRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark alert as shared and award chops if first time"""
    # Get user and alert
    user = current_user["user"]
    alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Check if user_alert record exists
    user_alert = db.query(UserAlert).filter(
        UserAlert.user_id == user.id,
        UserAlert.alert_id == request.alert_id
    ).first()
    
    if not user_alert:
        # Create new record
        user_alert = UserAlert(
            user_id=user.id,
            alert_id=request.alert_id,
            has_shared=True,
            is_attended=True,  # Mark as attended when sharing
            shared_at=datetime.utcnow()
        )
        
        # Award chops based on subscription status (active = 10, free = 5)
        chops_to_award = 10 if is_pro_user(user.subscription_status) else 5
        user_alert.chops_earned_from_share = chops_to_award
        user.total_chops += chops_to_award
        user.alert_sharing_chops += chops_to_award
        
        # Update alert share count
        alert.total_shares += 1
        
        db.add(user_alert)
        db.commit()
        
        return {
            "message": "Alert shared successfully",
            "chops_earned": chops_to_award,
            "total_chops": user.total_chops
        }
    else:
        # Check if already shared
        if not user_alert.has_shared:
            user_alert.has_shared = True
            user_alert.is_attended = True  # Mark as attended when sharing
            user_alert.shared_at = datetime.utcnow()
            
            # Award chops based on subscription status
            chops_to_award = 10 if is_pro_user(user.subscription_status) else 5
            user_alert.chops_earned_from_share = chops_to_award
            user.total_chops += chops_to_award
            user.alert_sharing_chops += chops_to_award
            
            # Update alert share count
            alert.total_shares += 1
            
            db.commit()
            
            return {
                "message": "Alert shared successfully",
                "chops_earned": chops_to_award,
                "total_chops": user.total_chops
            }
        
        return {
            "message": "Alert already shared",
            "chops_earned": 0,
            "total_chops": user.total_chops
        }


@router.get("/api/users/{user_id}/alerts/stats")
def get_user_alert_stats(user_id: int, db: Session = Depends(get_db)):
    """Get user's alert interaction statistics"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    total_alerts = db.query(Alert).filter(Alert.is_active == True).count()

    # All alerts the user has interacted with (viewed OR shared OR attended)
    attended_alert_ids = db.query(UserAlert.alert_id).filter(
        UserAlert.user_id == user_id
    ).filter(
        (UserAlert.has_viewed == True) |
        (UserAlert.has_shared == True) |
        (UserAlert.is_attended == True)
    ).subquery()

    viewed_count = db.query(UserAlert).filter(
        UserAlert.user_id == user_id,
        UserAlert.has_viewed == True
    ).count()
    
    shared_count = db.query(UserAlert).filter(
        UserAlert.user_id == user_id,
        UserAlert.has_shared == True
    ).count()

    # Count as attended if ANY interaction exists
    unattended_count = db.query(Alert).filter(
        Alert.is_active == True,
        ~Alert.id.in_(attended_alert_ids)  # This is the key!
    ).count()

    attended_count = total_alerts - unattended_count

    return {
        "total_alerts": total_alerts,
        "viewed_count": viewed_count,
        "shared_count": shared_count,
        "attended_count": attended_count,
        "unattended_count": unattended_count
    }


@router.post("/api/alerts/pin")
def pin_alert(
    request: PinAlertRequest, 
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Pin or unpin an alert"""
    user = current_user["user"]
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify alert exists
    alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Check if already pinned (fix the column name here)
    existing = db.query(UserPinnedAlert).filter(
        UserPinnedAlert.user_id == user.id,
        UserPinnedAlert.alert_id == request.alert_id  # Fixed: was alert_id_id
    ).first()
    
    if existing:
        # Unpin
        db.delete(existing)
        db.commit()
        return {"message": "Alert unpinned", "is_pinned": False}
    
    # Pin
    pinned_record = UserPinnedAlert(
        user_id=user.id,
        alert_id=request.alert_id
    )
    db.add(pinned_record)
    db.commit()
    
    return {"message": "Alert pinned", "is_pinned": True}

# Health check
@router.get("/")
def health_check():
    return {"status": "healthy", "service": "Alerts Management API"}