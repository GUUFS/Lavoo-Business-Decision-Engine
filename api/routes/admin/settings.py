from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.pg_connections import get_db
from database.pg_models import SystemSettings, User
from api.routes.auth.login import get_current_user

router = APIRouter(prefix="/control/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    # General
    site_name: Optional[str] = None
    system_name: Optional[str] = None  # alias for site_name
    support_email: Optional[str] = None
    default_language: Optional[str] = None
    timezone: Optional[str] = None
    allow_new_registrations: Optional[bool] = None  # frontend compatibility field

    # Limits
    max_analyses_basic: Optional[int] = None
    max_analyses_pro: Optional[int] = None
    max_analyses_premium: Optional[int] = None
    max_analyses_per_user: Optional[int] = None  # sets all three tiers
    
    # AI
    primary_ai_model: Optional[str] = None
    analysis_timeout: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    enable_predictive_analytics: Optional[bool] = None
    generate_recommendations: Optional[bool] = None
    include_confidence_scores: Optional[bool] = None
    enable_experimental_features: Optional[bool] = None
    
    # Security
    require_mfa_admin: Optional[bool] = None
    force_password_reset_90: Optional[bool] = None
    lock_accounts_after_failed_attempts: Optional[bool] = None
    data_retention_days: Optional[int] = None
    backup_frequency: Optional[str] = None
    
    # Billing
    monthly_price: Optional[float] = None
    quarterly_price: Optional[float] = None
    yearly_price: Optional[float] = None

@router.get("")
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Allow all authenticated users to read settings (required for pricing on Upgrade page)
    # if not current_user.is_admin:
    #    raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = db.query(SystemSettings).first()
    if not settings:
        # Create default
        settings = SystemSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    # Build response dict with aliases for frontend compatibility
    result = {col.name: getattr(settings, col.name) for col in settings.__table__.columns}
    result["system_name"] = settings.site_name  # alias for frontend compatibility
    result["allow_new_registrations"] = True  # no DB field; echo back as always-true default
    return result

@router.patch("")
def update_settings(
    update_data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)
    
    # Resolve aliases before applying updates
    if update_data.system_name is not None and update_data.site_name is None:
        update_data.site_name = update_data.system_name
    if update_data.max_analyses_per_user is not None:
        settings.max_analyses_basic = update_data.max_analyses_per_user
        settings.max_analyses_pro = update_data.max_analyses_per_user
        settings.max_analyses_premium = update_data.max_analyses_per_user

    # Apply updates (skip virtual/alias fields that have no DB column)
    _virtual_fields = {"system_name", "max_analyses_per_user", "allow_new_registrations"}
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if key not in _virtual_fields:
            setattr(settings, key, value)

    db.commit()
    db.refresh(settings)
    result = {col.name: getattr(settings, col.name) for col in settings.__table__.columns}
    result["system_name"] = settings.site_name
    result["allow_new_registrations"] = True
    return result
