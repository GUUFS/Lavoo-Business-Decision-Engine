import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.pg_connections import SessionLocal
from sqlalchemy import text

def apply_sql():
    try:
        print("Connecting to database...")
        db = SessionLocal()
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "security_setup.sql")
        print(f"Reading SQL from {script_path}")
        
        with open(script_path, "r") as f:
            sql_content = f.read()
            
        print("Applying SQL...")
        # First drop the view if it exists to allow modification
        db.execute(text("DROP VIEW IF EXISTS security_metrics_summary CASCADE"))
        db.execute(text(sql_content))
        db.commit()
        print("✅ Security setup SQL applied successfully!")
        
    except Exception as e:
        print(f"❌ Error applying SQL: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    apply_sql()
