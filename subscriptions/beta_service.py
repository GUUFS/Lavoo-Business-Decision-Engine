
from datetime import datetime, timedelta
from typing import Optional, Dict
import os
from sqlalchemy.orm import Session
from database.pg_models import User

class BetaService:
    
    @staticmethod
    def get_app_mode() -> str:
        """
        Get current application mode: 'beta', 'launch', or 'development'
        Reads from APP_MODE env var, fallbacks to BETA_MODE.
        """
        mode = os.getenv("APP_MODE", "").lower()
        if mode in ["beta", "launch", "development"]:
            return mode
            
        # Legacy support / Fallback
        if os.getenv("BETA_MODE", "false").lower() == "true":
            return "beta"
            
        return "launch"

    @staticmethod
    def is_beta_mode() -> bool:
        """Check if system is in beta mode"""
        return BetaService.get_app_mode() == "beta"
    
    @staticmethod
    def get_launch_date() -> Optional[datetime]:
        """Get configured launch date"""
        launch_str = os.getenv("LAUNCH_DATE")
        if launch_str:
            return datetime.strptime(launch_str, "%Y-%m-%d")
        return None
    
    @staticmethod
    def get_grace_period_days() -> int:
        """Get grace period duration (default: 5 days)"""
        return int(os.getenv("GRACE_PERIOD_DAYS", "5"))
    
    @staticmethod
    def calculate_grace_period_end(launch_date: datetime) -> datetime:
        """Calculate when grace period ends"""
        grace_days = BetaService.get_grace_period_days()
        return launch_date + timedelta(days=grace_days)
    
    @staticmethod
    def is_in_grace_period() -> bool:
        """Check if we're currently in grace period"""
        if BetaService.is_beta_mode():
            return False  # Still in beta, not launched yet
        
        launch_date = BetaService.get_launch_date()
        if not launch_date:
            return False
        
        # Check if launch has happened
        if datetime.utcnow() < launch_date:
            return False  # Launch hasn't happened yet
        
        grace_end = BetaService.calculate_grace_period_end(launch_date)
        return datetime.utcnow() < grace_end
    
    @staticmethod
    def has_saved_card(user: User) -> bool:
        """Check if user has a saved payment method"""
        return bool(user.stripe_payment_method_id)
    
    @staticmethod
    def get_user_status(user: User) -> Dict:
        """
        Get comprehensive user status for dashboard display
        
        Returns dict with:
        - status: 'beta_no_card', 'beta_with_card', 'grace_no_card', 'grace_with_card', 'active', 'new_user'
        - message: Display message
        - action_required: Boolean
        - countdown_ends_at: Datetime or None
        - days_remaining: Integer or None
        """
        launch_date = BetaService.get_launch_date()
        has_card = BetaService.has_saved_card(user)
        
        # BETA PERIOD (Before Launch)
        if BetaService.is_beta_mode():
            if has_card:
                return {
                    "status": "beta_with_card",
                    "message": "You're All Set for Launch!",
                    "action_required": False,
                    "countdown_ends_at": None,
                    "days_remaining": None,
                    "show_card_info": True
                }
            else:
                return {
                    "status": "beta_no_card",
                    "message": "Save Your Card for Launch Access",
                    "action_required": True,
                    "countdown_ends_at": None,
                    "days_remaining": None,
                    "show_card_info": False
                }
        
        # GRACE PERIOD (Launch Day + 5 Days OR Signup Day + 5 Days)
        if BetaService.is_in_grace_period() or (user.grace_period_ends_at and datetime.utcnow() < user.grace_period_ends_at):
            grace_end = user.grace_period_ends_at
            
            if not grace_end:
                 return {
                    "status": "new_user",
                    "message": "Subscribe to get started with Lavoo",
                    "action_required": True,
                    "countdown_ends_at": None,
                    "days_remaining": None,
                    "show_card_info": False
                }

            time_remaining = grace_end - datetime.utcnow()
            days_rem = time_remaining.days
            
            if has_card:
                return {
                    "status": "grace_with_card",
                    "message": f"Welcome! First charge in {days_rem if days_rem > 0 else 5} days",
                    "action_required": False,
                    "countdown_ends_at": grace_end,
                    "days_remaining": days_rem,
                    "show_card_info": True
                }
            else:
                return {
                    "status": "grace_no_card",
                    "message": "ACTION REQUIRED",
                    "action_required": True,
                    "countdown_ends_at": grace_end,
                    "days_remaining": days_rem,
                    "hours_remaining": (time_remaining.seconds // 3600),
                    "minutes_remaining": (time_remaining.seconds % 3600) // 60,
                    "seconds_remaining": (time_remaining.seconds % 60),
                    "show_card_info": False
                }
        
        # AFTER GRACE PERIOD OR ACTIVE SUBSCRIPTION
        if has_card and user.subscription_status == "active":
            return {
                "status": "active",
                "message": "Your subscription is active",
                "action_required": False,
                "countdown_ends_at": user.subscription_expires_at,
                "days_remaining": (user.subscription_expires_at - datetime.utcnow()).days if user.subscription_expires_at else None,
                "show_card_info": True
            }
        
        # Pause access if grace period is over and no card/active sub
        if user.grace_period_ends_at and datetime.utcnow() >= user.grace_period_ends_at:
             return {
                "status": "grace_expired_no_card",
                "message": "Your access is paused. Add a payment method to reactivate.",
                "action_required": True,
                "countdown_ends_at": None,
                "days_remaining": None,
                "show_card_info": False
            }

        # NEW USER (No Grace Period set yet)
        return {
            "status": "new_user",
            "message": "Subscribe to get started with Lavoo",
            "action_required": True,
            "countdown_ends_at": None,
            "days_remaining": None,
            "show_card_info": False
        }
    
    @staticmethod
    def initialize_grace_period(user: User, db: Session):
        """
        Initialize grace period based on user type:
        - Beta users: 5 days from launch date
        - New users: 5 days from signup date
        """
        is_beta = BetaService.is_beta_mode()
        launch_date = BetaService.get_launch_date()
        grace_days = BetaService.get_grace_period_days()
        
        if is_beta:
            # Beta user: Grace period starts at launch
            user.is_beta_user = True
            user.beta_joined_at = datetime.utcnow()
            if launch_date:
                user.grace_period_ends_at = launch_date + timedelta(days=grace_days)
        else:
            # Post-launch user: Grace period starts now
            user.is_beta_user = False
            user.grace_period_ends_at = datetime.utcnow() + timedelta(days=grace_days)
            
        db.add(user)
        db.flush()

    @staticmethod
    def mark_as_beta_user(user: User, db: Session):
        """Mark user as beta participant (force beta status)"""
        user.is_beta_user = True
        user.beta_joined_at = datetime.utcnow()
        
        launch_date = BetaService.get_launch_date()
        if launch_date:
            user.grace_period_ends_at = BetaService.calculate_grace_period_end(launch_date)
        
        db.commit()
    
    @staticmethod
    def should_send_reminder(user: User, notification_type: str, db: Session) -> bool:
        """
        Check if we should send a reminder (prevent spam)
        Returns True if:
        - No notification of this type sent in last 24 hours
        - User hasn't completed the action
        """
        from database.pg_models import NotificationHistory
        
        # Check if notification was sent recently
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent = db.query(NotificationHistory).filter(
            NotificationHistory.user_id == user.id,
            NotificationHistory.notification_type == notification_type,
            NotificationHistory.sent_at >= cutoff
        ).first()
        
        if recent:
            return False
        
        # Check if action is still needed
        if notification_type == "beta_card_reminder":
            return not BetaService.has_saved_card(user)
        elif notification_type == "grace_period_warning":
            return not BetaService.has_saved_card(user) and BetaService.is_in_grace_period()
        
        return False