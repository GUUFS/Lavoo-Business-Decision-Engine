from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database.pg_models import UserNotification, NotificationType, UserSettings, PushSubscription
from api.routes.support.customer_service import notification_manager
import json
import logging
import os

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def _send_web_push(db: Session, user_id: int, payload: dict) -> None:
        """Deliver a native browser/PWA notification to registered devices."""
        private_key = os.getenv("VAPID_PRIVATE_KEY")
        subject = os.getenv("VAPID_SUBJECT", "mailto:security@lavoo.io")
        if not private_key:
            return

        try:
            import json
            from pywebpush import WebPushException, webpush
        except ImportError:
            logger.error("pywebpush is not installed; browser push delivery is unavailable")
            return

        subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                    },
                    data=json.dumps(payload),
                    vapid_private_key=private_key,
                    vapid_claims={"sub": subject},
                )
            except WebPushException as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in (404, 410):
                    db.delete(subscription)
                    db.commit()
                logger.warning("Web Push delivery failed for user=%s: %s", user_id, exc)
            except Exception as exc:
                logger.warning("Web Push delivery failed for user=%s: %s", user_id, exc)

    @staticmethod
    def _is_enabled(db: Session, user_id: int, notification_type: str) -> bool:
        """Check the user's notification switches before creating a notification."""
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings is None:
            return True
        if not settings.push_notifications:
            return False

        analysis_types = {"mission_overdue", "analysis_reminder", "analysis_ready"}
        community_types = {
            "community_cooked", "community_chops", "community_spice",
            "community_reply", "user_tagged", "voo_checkin",
        }
        if notification_type in analysis_types and not settings.analysis_reminders:
            return False
        if notification_type in community_types and not settings.community_notifications:
            return False
        return True

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        type: str,
        title: str,
        message: str,
        link: str = None
    ):
        """
        Create a new notification and notify user via WebSocket if connected
        """
        try:
            if not NotificationService._is_enabled(db, user_id, type):
                logger.info("Notification suppressed by user preferences: user=%s type=%s", user_id, type)
                return None

            notification = UserNotification(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                link=link,
                created_at=datetime.now(timezone.utc)
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)

            # Map type to icon/color if needed for frontend or just send payload
            payload = {
                "type": "new_notification",
                "payload": {
                    "id": notification.id,
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "link": notification.link,
                    "created_at": notification.created_at.isoformat(),
                    "is_read": notification.is_read
                }
            }

            # Import the notification manager from customer_service
            # Note: We use the already established WebSocket infrastructure
            import asyncio
            asyncio.create_task(notification_manager.send_personal_message(json.dumps(payload), user_id))
            NotificationService._send_web_push(db, user_id, payload["payload"])

            return notification
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            db.rollback()
            return None
