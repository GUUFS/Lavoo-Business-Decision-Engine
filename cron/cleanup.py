#!/usr/bin/env python3
"""
Cron Job: Data Cleanup
Runs once per day
Deletes insights and alerts older than 4 months
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv(".env.production")

from db.pg_connections import SessionLocal
from db.pg_models import Insight, Alert, UserInsight, UserAlert
from config.logging import setup_logging
import logging

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger("cron.cleanup")

# Retention period: 4 months (approximately 120 days)
RETENTION_DAYS = 120

def main():
    """Run data cleanup cron job."""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🕐 CRON JOB START: Data Cleanup - {start_time}")
    logger.info(f"   Retention period: {RETENTION_DAYS} days (4 months)")
    logger.info("=" * 60)

    session = SessionLocal()

    try:
        cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
        logger.info(f"Deleting data older than: {cutoff_date.date()}")

        # Get old insights
        old_insights = session.query(Insight).filter(
            Insight.created_at < cutoff_date
        ).all()
        old_insight_ids = [i.id for i in old_insights]

        # Get old alerts
        old_alerts = session.query(Alert).filter(
            Alert.created_at < cutoff_date
        ).all()
        old_alert_ids = [a.id for a in old_alerts]

        # Delete related user_insights first (foreign key constraint)
        if old_insight_ids:
            user_insights_deleted = session.query(UserInsight).filter(
                UserInsight.insight_id.in_(old_insight_ids)
            ).delete(synchronize_session=False)
            logger.info(f"   Deleted {user_insights_deleted} user_insight records")

        # Delete related user_alerts first (foreign key constraint)
        if old_alert_ids:
            user_alerts_deleted = session.query(UserAlert).filter(
                UserAlert.alert_id.in_(old_alert_ids)
            ).delete(synchronize_session=False)
            logger.info(f"   Deleted {user_alerts_deleted} user_alert records")

        # Delete old insights
        insights_deleted = session.query(Insight).filter(
            Insight.created_at < cutoff_date
        ).delete(synchronize_session=False)

        # Delete old alerts
        alerts_deleted = session.query(Alert).filter(
            Alert.created_at < cutoff_date
        ).delete(synchronize_session=False)

        session.commit()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info(f"✅ CRON JOB COMPLETE: Data Cleanup")
        logger.info(f"   Duration: {duration:.2f} seconds")
        logger.info(f"   Insights deleted: {insights_deleted}")
        logger.info(f"   Alerts deleted: {alerts_deleted}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        session.rollback()
        logger.error(f"❌ CRON JOB FAILED: {str(e)}", exc_info=True)
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
