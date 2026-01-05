import json
import os
import sys
from sqlalchemy import text

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.pg_connections import SessionLocal
from api.security.firewall import initialize_default_firewall_rules, firewall_manager

def sync():
    print("Starting Firewall Rule Synchronization...")
    db = SessionLocal()
    try:
        initialize_default_firewall_rules(db)
        print("✓ Default rules initialized/updated in database.")
        
        firewall_manager.load_rules(db)
        print("✓ Rules loaded into memory.")
        
        # Verify WAF rule specifically
        result = db.execute(text("SELECT rule_config FROM firewall_rules WHERE name = 'SQL Injection Protection'")).fetchone()
        if result:
            config = json.loads(result[0])
            print(f"✓ SQL Injection Pattern: {config.get('pattern')}")
        
    except Exception as e:
        print(f"❌ Synchronization failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync()
