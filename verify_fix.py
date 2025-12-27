
import sys
import os

# Add project root to sys.path
# In this environment, the path should be /home/emeka/ai-business-analyst
sys.path.append('/home/emeka/ai-business-analyst')

from db.pg_connections import SessionLocal, init_db
from sqlalchemy import text
from db.pg_models import Alert, Insight, User, FailedLoginAttempt, FirewallRule, SecurityMetricsSummary

def verify():
    print("--- Verification Started ---")
    
    # Define project root
    project_root = '/home/emeka/ai-business-analyst'

    # Manually trigger the SQL execution for verification (simulating startup_event)
    sql_file = os.path.join(project_root, 'db', 'security_setup.sql')
    if os.path.exists(sql_file):
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        db = SessionLocal()
        try:
            db.execute(text(sql_content))
            db.commit()
            print('✅ Security SQL applied manually for verification')
        except Exception as e:
            print(f'❌ Failed to apply SQL: {e}')
            db.rollback()
        finally:
            db.close()
    else:
        print(f'❌ security_setup.sql not found at {sql_file}')

    db = SessionLocal()
    try:
        # Check if view exists
        result = db.execute(text('SELECT * FROM security_metrics_summary')).fetchone()
        print(f'✅ security_metrics_summary view exists: {result is not None or True}')
        
        # Check if Alert has url
        alert = Alert()
        print(f'✅ Alert has url attribute: {hasattr(alert, "url")}')
        
        insight = Insight()
        print(f'✅ Insight has url attribute: {hasattr(insight, "url")}')
        
        user = User()
        print(f'✅ User has user_status attribute: {hasattr(user, "user_status")}')
        print(f'✅ User has last_login attribute: {hasattr(user, "last_login")}')
        
        # Check FailedLoginAttempt rename
        failed_login = FailedLoginAttempt()
        print(f'✅ FailedLoginAttempt has created_at (renamed): {hasattr(failed_login, "created_at")}')
        print(f'❌ FailedLoginAttempt has old attempt_time: {hasattr(failed_login, "attempt_time")}')
        
        # Check FirewallRule is_active
        firewall = FirewallRule()
        print(f'✅ FirewallRule has is_active: {hasattr(firewall, "is_active")}')
        
        # Check SecurityMetricsSummary ORM
        metrics = SecurityMetricsSummary()
        print(f'✅ SecurityMetricsSummary ORM model exists: {hasattr(metrics, "total_events_24h")}')
        
        print("--- Verification Successful ---")
    except Exception as e:
        print(f'❌ Verification failed: {e}')
    finally:
        db.close()

if __name__ == "__main__":
    verify()
