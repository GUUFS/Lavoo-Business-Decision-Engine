
import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db.pg_models import SecurityEvent, FailedLoginAttempt

# Setup DB connection
# Assuming DATABASE_URL is in env or typical location. Use the one from .env if needed
# For now, I'll try to load from .env or assume a default for the user environment if known.
# Looking at previous logs, I don't see the exact URL string, but I can try to import get_db

sys.path.append(os.getcwd())
from db.pg_connections import get_db, engine

def check_data():
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        se_count = session.query(SecurityEvent).count()
        fla_count = session.query(FailedLoginAttempt).count()
        
        print(f"Security Events Count: {se_count}")
        print(f"Failed Login Attempts Count: {fla_count}")
        
        if se_count > 0:
            print("\nLast 3 Security Events:")
            events = session.query(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(3).all()
            for e in events:
                print(f"- {e.type}: {e.description} ({e.created_at})")
                
        if fla_count > 0:
            print("\nLast 3 Failed Login Attempts:")
            attempts = session.query(FailedLoginAttempt).order_by(FailedLoginAttempt.created_at.desc()).limit(3).all()
            for a in attempts:
                print(f"- {a.email}: {a.ip_address} ({a.created_at})")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_data()
