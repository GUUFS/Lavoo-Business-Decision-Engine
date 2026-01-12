
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from db.pg_connections import engine
    from sqlalchemy import text
    
    with engine.connect() as conn:
        result = conn.execute(text('SELECT user_id, default_payout_method FROM payout_accounts LIMIT 5'))
        rows = result.fetchall()
        print("Data in 'payout_accounts' table (user_id, default_payout_method):")
        for row in rows:
            print(f"- {row}")
except Exception as e:
    print(f"Error: {e}")
