"""
Handle automatic billing of beta users whose grace period has ended.
Run daily via cron.

Each user is charged by subscriptions/beta_billing.py (the same code the
admin "charge beta users" action uses): in the currency and plan they picked
when saving their card, at the founding or standard price, with the amount
Stripe actually charged recorded.
"""

import logging
import os
import sys
from datetime import datetime, timezone

# Add the project root to the Python path to resolve imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.pg_connections import SessionLocal
from database.pg_models import User
from subscriptions.beta_billing import charge_beta_user
from subscriptions.beta_service import BetaService

logger = logging.getLogger(__name__)


def process_beta_billing():
    """
    Find users whose grace period has ended and charge their saved cards.
    """
    with SessionLocal() as db:
        # Determine if we are in beta mode
        is_beta = BetaService.is_beta_mode()

        # 1. Base filter: Beta users with card, not active
        query = db.query(User.id).filter(
            User.is_beta_user == True,
            User.subscription_status != "active",
            User.stripe_payment_method_id.isnot(None),
            User.stripe_customer_id.isnot(None),
        )

        # 2. Apply timing filter
        if is_beta:
            # If still in beta, ONLY charge if grace period specifically ended (unlikely in beta but safe)
            query = query.filter(User.grace_period_ends_at <= datetime.now(timezone.utc))
        # IF LAUNCHED: Charge everyone with a card immediately.
        # The grace period is only for users WITHOUT cards to add one.

        user_ids = [row.id for row in query.all()]

    print(f"[{'BETA' if is_beta else 'LAUNCH'}] Found {len(user_ids)} users to charge")
    charged = 0
    for user_id in user_ids:
        if charge_beta_user(user_id):
            charged += 1
            print(f"✅ [CRON] Charged and activated user {user_id}")
        else:
            print(f"⚠️ [CRON] User {user_id} not charged (see [beta-charge] logs)")
    print(f"[CRON] Done: {charged} of {len(user_ids)} charged")
    logger.info(f"[CRON] beta billing: {charged} of {len(user_ids)} charged")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    process_beta_billing()
