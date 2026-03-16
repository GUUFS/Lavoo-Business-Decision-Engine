"""
User Settings API routes
Handles user preferences and settings management
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.pg_connections import get_db
from database.pg_models import User, UserSettings
from api.routes.auth.login import get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


# ===== Pydantic Models =====

class UserSettingsResponse(BaseModel):
    # Notification Settings
    emailNotifications: bool
    pushNotifications: bool
    analysisReminders: bool
    communityNotifications: bool

    # Decision Engine Settings
    activeConstraintMode: bool
    pendingTaskReminders: bool

    # Display Settings
    darkMode: bool
    compactView: bool

    # Privacy Settings
    profileVisibility: str
    showEarnings: bool


class UpdateSettingsRequest(BaseModel):
    # Notification Settings
    emailNotifications: Optional[bool] = None
    pushNotifications: Optional[bool] = None
    analysisReminders: Optional[bool] = None
    communityNotifications: Optional[bool] = None

    # Decision Engine Settings
    activeConstraintMode: Optional[bool] = None
    pendingTaskReminders: Optional[bool] = None

    # Display Settings
    darkMode: Optional[bool] = None
    compactView: Optional[bool] = None

    # Privacy Settings
    profileVisibility: Optional[str] = None
    showEarnings: Optional[bool] = None


# ===== Helper Functions =====

def get_or_create_settings(db: Session, user_id: int) -> UserSettings:
    """Get user settings or create with defaults if not exists"""
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

    if not settings:
        settings = UserSettings(
            user_id=user_id,
            email_notifications=True,
            push_notifications=True,
            analysis_reminders=True,
            community_notifications=True,
            active_constraint_mode=True,
            pending_task_reminders=True,
            dark_mode=False,
            compact_view=False,
            profile_visibility='community',
            show_earnings=True
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        logger.info(f"Created default settings for user {user_id}")

    return settings


# ===== API Endpoints =====

@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user settings (creates defaults if not exists)"""
    try:
        settings = get_or_create_settings(db, current_user.id)

        return UserSettingsResponse(
            emailNotifications=settings.email_notifications,
            pushNotifications=settings.push_notifications,
            analysisReminders=settings.analysis_reminders,
            communityNotifications=settings.community_notifications,
            activeConstraintMode=settings.active_constraint_mode,
            pendingTaskReminders=settings.pending_task_reminders,
            darkMode=settings.dark_mode,
            compactView=settings.compact_view,
            profileVisibility=settings.profile_visibility,
            showEarnings=settings.show_earnings
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch settings")


@router.put("")
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings"""
    try:
        settings = get_or_create_settings(db, current_user.id)

        # Update only provided fields
        if request.emailNotifications is not None:
            settings.email_notifications = request.emailNotifications
        if request.pushNotifications is not None:
            settings.push_notifications = request.pushNotifications
        if request.analysisReminders is not None:
            settings.analysis_reminders = request.analysisReminders
        if request.communityNotifications is not None:
            settings.community_notifications = request.communityNotifications
        if request.activeConstraintMode is not None:
            settings.active_constraint_mode = request.activeConstraintMode
        if request.pendingTaskReminders is not None:
            settings.pending_task_reminders = request.pendingTaskReminders
        if request.darkMode is not None:
            settings.dark_mode = request.darkMode
        if request.compactView is not None:
            settings.compact_view = request.compactView
        if request.profileVisibility is not None:
            if request.profileVisibility not in ['public', 'community', 'private']:
                raise HTTPException(status_code=400, detail="Invalid profile visibility value")
            settings.profile_visibility = request.profileVisibility
        if request.showEarnings is not None:
            settings.show_earnings = request.showEarnings

        db.commit()
        db.refresh(settings)

        logger.info(f"Updated settings for user {current_user.id}")

        return {
            "success": True,
            "message": "Settings updated successfully",
            "data": UserSettingsResponse(
                emailNotifications=settings.email_notifications,
                pushNotifications=settings.push_notifications,
                analysisReminders=settings.analysis_reminders,
                communityNotifications=settings.community_notifications,
                activeConstraintMode=settings.active_constraint_mode,
                pendingTaskReminders=settings.pending_task_reminders,
                darkMode=settings.dark_mode,
                compactView=settings.compact_view,
                profileVisibility=settings.profile_visibility,
                showEarnings=settings.show_earnings
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.get("/notifications")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification-specific settings"""
    try:
        settings = get_or_create_settings(db, current_user.id)

        return {
            "success": True,
            "data": {
                "emailNotifications": settings.email_notifications,
                "pushNotifications": settings.push_notifications,
                "analysisReminders": settings.analysis_reminders,
                "communityNotifications": settings.community_notifications
            }
        }
    except Exception as e:
        logger.error(f"Error fetching notification settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch notification settings")


@router.get("/privacy")
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get privacy-specific settings"""
    try:
        settings = get_or_create_settings(db, current_user.id)

        return {
            "success": True,
            "data": {
                "profileVisibility": settings.profile_visibility,
                "showEarnings": settings.show_earnings
            }
        }
    except Exception as e:
        logger.error(f"Error fetching privacy settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch privacy settings")
