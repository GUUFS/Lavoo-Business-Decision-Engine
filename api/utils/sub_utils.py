from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from db.pg_models import User, Subscriptions

logger = logging.getLogger(__name__)

def sync_user_subscription(db: Session, user: User) -> User:
    """
    Syncs the user's subscription status based on the LATEST successful transaction.
    Returns the updated user object.
    """
    try:
        # Get the LATEST successful/active subscription (by ID/Creation)
        # Ordering by ID ensures that the VERY LAST payment made is prioritized.
        latest_sub = db.query(Subscriptions).filter(
            Subscriptions.user_id == user.id,
            Subscriptions.status.in_(('completed', 'active', 'paid', 'successful', 'succeeded'))
        ).order_by(Subscriptions.id.desc()).first()

        if latest_sub:
            # Handle timezone awareness for end_date
            if latest_sub.end_date and latest_sub.end_date.tzinfo is None:
                end_date = latest_sub.end_date.replace(tzinfo=timezone.utc)
            else:
                end_date = latest_sub.end_date

            # Get current time in same timezone as end_date
            now = datetime.now(end_date.tzinfo if end_date else timezone.utc)

            # Determine lifecycle status
            if end_date and end_date < now:
                new_sub_status = "Free"
                new_user_status = "Free"
            else:
                new_sub_status = "active"
                new_user_status = "active"

            # Update Subscriptions table record if lifecycle status changed
            if latest_sub.subscription_status != new_sub_status:
                latest_sub.subscription_status = new_sub_status
                db.add(latest_sub)

            # Update Users table if status or plan changed
            # Plan should be the plan from the latest subscription (if active)
            new_plan = latest_sub.subscription_plan if new_user_status == "active" else None

            if user.subscription_status != new_user_status or user.subscription_plan != new_plan:
                user.subscription_status = new_user_status
                user.subscription_plan = new_plan
                db.add(user)
                logger.info(f"User {user.email} subscription synced: {new_user_status} ({new_plan})")
            
            db.commit()
        
        elif user.subscription_status != "Free":
            # No subscription found at all, but user has a stale status
            user.subscription_status = "Free"
            user.subscription_plan = None
            db.add(user)
            db.commit()
            logger.info(f"User {user.email} status reset to Free (no subscriptions found)")
            
    except Exception as e:
        logger.error(f"Error in sync_user_subscription for {user.email}: {e}")
        db.rollback()
        
    return user
