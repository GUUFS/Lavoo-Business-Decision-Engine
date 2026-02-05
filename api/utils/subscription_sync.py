"""
Subscription Status Sync Utility
Checks and updates user subscription status based on database records.
Called from dashboard/user endpoints to keep status in sync without blocking login.

This module now delegates to api.utils.sub_utils to ensure consistent logic across the application.
"""

from sqlalchemy.orm import Session
from db.pg_models import User
import logging
from api.utils.sub_utils import sync_user_subscription as core_sync

logger = logging.getLogger(__name__)


def sync_user_subscription(user: User, db: Session) -> None:
    """
    Sync user's subscription status based on their subscription records.
    
    This acts as a wrapper around the core logic in sub_utils.py.
    It maintains the existing signature (user, db) expected by some callers,
    but delegates to the single source of truth (db, user).

    Args:
        user: User object to sync
        db: Database session

    Returns:
        None (updates user object in place)
    """
    try:
        # Delegate to the core logic which handles the 'First Subscription' rule
        # Note: sub_utils.sync_user_subscription takes (db, user)
        core_sync(db, user)
        
    except Exception as e:
        logger.error(f"Error syncing subscription for user {user.id}: {e}")
        # Don't raise - subscription sync failure shouldn't break the request
