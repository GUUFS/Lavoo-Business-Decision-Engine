import sys
import os
 
# Add project root to path
sys.path.append(os.getcwd())
 
from db.pg_connections import SessionLocal
from sqlalchemy import text
 
def check_data():
    db = SessionLocal()
    try:
        print("--- Checking Security Events Table ---")
        events = db.execute(text("SELECT count(*) FROM security_events")).scalar()
        print(f"Total Security Events: {events}")
        
        last_event = db.execute(text("SELECT * FROM security_events ORDER BY created_at DESC LIMIT 1")).fetchone()
        print(f"Last Event: {last_event}")
 
        print("\n--- Checking Firewall Rules Table ---")
        rules = db.execute(text("SELECT count(*) FROM firewall_rules")).scalar()
        print(f"Total Firewall Rules: {rules}")
 
        print("\n--- Checking Security Metrics View ---")
        try:
            metrics = db.execute(text("SELECT * FROM security_metrics_summary")).fetchone()
            print(f"Metrics View Row: {metrics}")
            if metrics:
                # Print columns to verify names
                print(f"Keys: {metrics._mapping.keys() if hasattr(metrics, '_mapping') else 'Unknown'}")
        except Exception as e:
            print(f"Error querying view: {e}")
 
    except Exception as e:
        print(f"Database Error: {e}")
    finally:
        db.close()
 
if __name__ == "__main__":
    check_data()
