"""
Subscription Status Sync Utility
Checks and updates user subscription status based on database records.
Called from dashboard/user endpoints to keep status in sync without blocking login.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from db.pg_models import User
import logging

logger = logging.getLogger(__name__)


def sync_user_subscription(user: User, db: Session) -> None:
    """
    Sync user's subscription status based on their subscription records.

    This checks if user has active subscriptions and updates their status accordingly.
    Called lazily (on dashboard load, user profile access) to avoid blocking login.

    Args:
        user: User object to sync
        db: Database session

    Returns:
        None (updates user object in place)
    """
    try:
        # Check if user has any subscriptions
        if not user.subscriptions:
            # No subscriptions = Free tier
            if user.subscription_status != 'Free':
                user.subscription_status = 'Free'
                user.subscription_plan = 'Free'
                db.commit()
                logger.info(f"User {user.id} subscription synced: Free (no subscriptions)")
            return

        # Check for active subscriptions
        has_active_sub = False
        now = datetime.utcnow()

        for sub in user.subscriptions:
            # Skip if not active status
            if sub.status != 'active':
                continue

            # Check if subscription end date is in the future
            if sub.end_date:
                end_date = sub.end_date.replace(tzinfo=None) if sub.end_date.tzinfo else sub.end_date

                if end_date > now:
                    # Active and not expired
                    has_active_sub = True

                    # Update user subscription info
                    if user.subscription_status != 'active':
                        user.subscription_status = 'active'
                        user.subscription_plan = sub.subscription_plan or 'Pro'
                        logger.info(f"User {user.id} subscription synced: Active ({sub.subscription_plan})")

                    break  # Found active subscription, stop checking
                else:
                    # Subscription expired - mark it
                    sub.status = 'expired'
                    logger.info(f"Marked subscription {sub.id} as expired for user {user.id}")

        # If no active subscription found, revert to Free
        if not has_active_sub and user.subscription_status != 'Free':
            user.subscription_status = 'Free'
            user.subscription_plan = 'Free'
            db.commit()
            logger.info(f"User {user.id} subscription synced: Free (no active subs)")
        elif has_active_sub:
            db.commit()  # Commit the active status update

    except Exception as e:
        logger.error(f"Error syncing subscription for user {user.id}: {e}")
        db.rollback()
        # Don't raise - subscription sync failure shouldn't break the request
