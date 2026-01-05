from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from db.pg_models import User, Subscriptions

logger = logging.getLogger(__name__)

def sync_user_subscription(db: Session, user: User) -> User:
    """
    Syncs the user's subscription status based on the 'first transaction' rule.
    Returns the updated user object.
    """
    try:
        # Get the FIRST subscription ever made (ordered by creation date/id)
        first_sub = db.query(Subscriptions).filter(
            Subscriptions.user_id == user.id
        ).order_by(Subscriptions.created_at.asc(), Subscriptions.id.asc()).first()

        if first_sub:
            # Handle timezone awareness for end_date
            if first_sub.end_date and first_sub.end_date.tzinfo is None:
                end_date = first_sub.end_date.replace(tzinfo=timezone.utc)
            else:
                end_date = first_sub.end_date

            # Get current time in same timezone as end_date
            now = datetime.now(end_date.tzinfo if end_date else timezone.utc)

            # Determine lifecycle status
            # Successful statuses: 'completed', 'active', 'paid', 'successful'
            if first_sub.status not in ('completed', 'active', 'paid', 'successful', 'succeeded'):
                new_sub_status = "Payment failed"
                new_user_status = "Free"
            elif end_date and end_date < now:
                new_sub_status = "expired"
                new_user_status = "Free"
            else:
                new_sub_status = "active"
                new_user_status = "active"

            # Update Subscriptions table record if lifecycle status changed
            if first_sub.subscription_status != new_sub_status:
                first_sub.subscription_status = new_sub_status
                db.add(first_sub)

            # Update Users table if status or plan changed
            # Plan should be the plan from the first subscription (if active)
            new_plan = first_sub.subscription_plan if new_user_status == "active" else None

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
            
    except Exception as e:
        logger.error(f"Error in sync_user_subscription for {user.email}: {e}")
        db.rollback()
        
    return user
