
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from db.pg_connections import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Check raw columns from information_schema
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'payout_accounts'
        """))
        print("Information Schema columns for 'payout_accounts':")
        for row in result.fetchall():
            print(f"- {row[0]} ({row[1]})")
            
except Exception as e:
    print(f"Error: {e}")
