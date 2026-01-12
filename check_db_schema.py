
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from db.pg_connections import engine
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    columns = inspector.get_columns('payout_accounts')
    print("Columns in 'payout_accounts' table:")
    for column in columns:
        print(f"- {column['name']}")
except Exception as e:
    print(f"Error: {e}")
