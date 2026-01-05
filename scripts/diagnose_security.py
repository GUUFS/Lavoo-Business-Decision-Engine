
import sys
import os
import json
from datetime import datetime

# Adjust path so we can import from app
sys.path.append(os.getcwd())

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from db.pg_connections import engine
from db.pg_models import SecurityMetricsSummary, SecurityEvent, FailedLoginAttempt

Session = sessionmaker(bind=engine)
session = Session()

def diagnose():
    print("=== Security Diagnostics ===")
    
    # 1. Check Metrics View
    print("\n[1] Checking SecurityMetricsSummary View...")
    try:
        metrics = session.query(SecurityMetricsSummary).first()
        if metrics:
            print(f"FAILED LOGINS (24h): {metrics.failed_logins_24h}")
            print(f"BLOCKED ATTACKS (24h): {metrics.blocked_attacks_24h}")
            print(f"HIGH SEVERITY (24h): {metrics.high_severity_events_24h}")
            print(f"ACTIVE FIREWALL RULES: {metrics.active_firewall_rules}")
        else:
            print("WARNING: SecurityMetricsSummary view returned NO rows (None).")
    except Exception as e:
        print(f"ERROR querying metrics view: {e}")

    # 2. Check Raw Tables
    print("\n[2] Checking Raw Tables...")
    try:
        event_count = session.query(SecurityEvent).count()
        failed_count = session.query(FailedLoginAttempt).count()
        print(f"Total SecurityEvents: {event_count}")
        print(f"Total FailedLoginAttempts: {failed_count}")
        
        # 3. Check Serializability (INET issues)
        print("\n[3] Checking Serialization (Last 3 Events)...")
        if event_count > 0:
            events = session.query(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(3).all()
            for e in events:
                print(f"Event ID: {e.id}")
                print(f"  Type: {e.type}")
                print(f"  IP Address: {e.ip_address} (Type: {type(e.ip_address)})")
                
        if failed_count > 0:
            attempts = session.query(FailedLoginAttempt).order_by(FailedLoginAttempt.created_at.desc()).limit(3).all()
            for a in attempts:
                print(f"Attempt ID: {a.id}")
                print(f"  IP Address: {a.ip_address} (Type: {type(a.ip_address)})")

    except Exception as e:
        print(f"ERROR querying raw tables: {e}")

    finally:
        session.close()

if __name__ == "__main__":
    diagnose()
