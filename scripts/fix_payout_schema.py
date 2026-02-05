
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path to import db modules if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

def fix_schema():
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    columns_to_add = [
        ("provider", "VARCHAR(50)"),
        ("payment_method", "VARCHAR(50)"),
        ("provider_payout_id", "VARCHAR(255)"),
        ("provider_response", "TEXT"),
        ("recipient_email", "VARCHAR(255)"),
        ("recipient_name", "VARCHAR(255)"),
        ("account_details", "TEXT"),
        ("failure_reason", "TEXT"),
        ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
        ("completed_at", "TIMESTAMP WITH TIME ZONE"),
        ("requested_at", "TIMESTAMP WITH TIME ZONE"),
        ("processed_at", "TIMESTAMP WITH TIME ZONE")
    ]
    
    try:
        with engine.connect() as conn:
            # 1. Clear alembic version to fix "ghost revision" errors
            print("Clearing 'alembic_version' table to reset migration history...")
            try:
                conn.execute(text("DELETE FROM alembic_version"))
                conn.commit()
                print("✅ Migration history cleared.")
            except Exception as e:
                print(f"ℹ️ Note: Could not clear alembic_version (it might already be empty or not exist): {e}")

            # 2. Check existing columns in payouts
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'payouts'"))
            existing_columns = [row[0] for row in result.fetchall()]
            print(f"Current columns in 'payouts': {existing_columns}")
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    print(f"Adding column '{col_name}' to 'payouts' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE payouts ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"✅ Column '{col_name}' added successfully.")
                    except Exception as e:
                        print(f"❌ Error adding column '{col_name}': {e}")
                else:
                    print(f"✓ Column '{col_name}' already exists.")
            
            print("\nSchema fix complete!")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fix_schema()
