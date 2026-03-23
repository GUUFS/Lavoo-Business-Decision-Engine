from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import base64

from api.routes.auth.login import get_current_user
from api.utils.sub_utils import sync_user_subscription
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
    sync_user_subscription(db, current_user)
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "company_name": current_user.company_name,
        "industry": current_user.industry,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "subscription_status": current_user.subscription_status or "Free",
        "subscription_plan": current_user.subscription_plan,
        "is_beta_user": getattr(current_user, 'is_beta_user', False),
        "stripe_customer_id": current_user.stripe_customer_id,
        "stripe_payment_method_id": current_user.stripe_payment_method_id,
        "card_last4": current_user.card_last4,
        "card_brand": current_user.card_brand,
        "card_exp_month": current_user.card_exp_month,
        "card_exp_year": current_user.card_exp_year,
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
                "subscription_plan": current_user.subscription_plan,
                "is_beta_user": getattr(current_user, 'is_beta_user', False),
                "stripe_customer_id": current_user.stripe_customer_id,
                "stripe_payment_method_id": current_user.stripe_payment_method_id,
                "card_last4": current_user.card_last4,
                "card_brand": current_user.card_brand,
                "card_exp_month": current_user.card_exp_month,
                "card_exp_year": current_user.card_exp_year,
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a user profile avatar. Accepts image files up to 5MB."""
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # Read file content
    content = await file.read()

    # Limit to 5MB
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

    # Convert to base64 data URL for simple storage (no external storage required)
    mime_type = file.content_type
    b64 = base64.b64encode(content).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"

    # Store in avatar_url field
    current_user.avatar_url = data_url
    db.commit()

    return {"message": "Avatar uploaded successfully", "avatar_url": data_url}
