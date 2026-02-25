from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from api.routes.auth.login import get_current_user
from database.pg_connections import get_db

# Import PostgreSQL user models
from database.pg_models import User, UserResponse

router = APIRouter(prefix="/api/profile", tags=["profile"])


class ProfileUpdateRequest(BaseModel):
    """Profile update request model"""
    name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    bio: Optional[str] = None


@router.get("")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "company_name": current_user.company_name,
        "industry": current_user.industry,
        "bio": current_user.bio,
        "subscription_status": current_user.subscription_status or "Free",
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("")
def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    try:
        # Update fields if provided
        if profile_data.name is not None:
            current_user.name = profile_data.name
        if profile_data.company_name is not None:
            current_user.company_name = profile_data.company_name
        if profile_data.industry is not None:
            current_user.industry = profile_data.industry
        if profile_data.bio is not None:
            current_user.bio = profile_data.bio

        db.commit()
        db.refresh(current_user)

        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "company_name": current_user.company_name,
                "industry": current_user.industry,
                "bio": current_user.bio,
                "subscription_status": current_user.subscription_status or "Free",
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")
