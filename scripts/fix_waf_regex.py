
import sys
import os
import json
from sqlalchemy import create_engine, text

# Add parent directory to path to allow importing from api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.pg_connections import get_db

def fix_firewall_rules():
    print("🔧 Fixing firewall rules...")
    
    # Database connection
    # We'll use the get_db context manager manually
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 1. Update SQL Injection Rule Pattern
        # OLD: r'(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b|--|/\*|;)'
        # NEW: r'(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b|--|/\*)'
        # Removing the trailing semicolon which flags User-Agents
        
        new_config = json.dumps({
            'pattern': r'(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b|\'\s+OR\s+\')'
        })
        
        db.execute(text("""
            UPDATE firewall_rules 
            SET rule_config = :config, updated_at = NOW()
            WHERE name = 'SQL Injection Protection'
        """), {'config': new_config})
        
        db.commit()
        print("✅ Successfully patched 'SQL Injection Protection' rule in database.")
        
    except Exception as e:
        print(f"❌ Failed to patch rules: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_firewall_rules()
