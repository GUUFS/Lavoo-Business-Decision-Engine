
import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.pg_connections import SessionLocal
from api.routes.security import get_security_metrics, get_security_events
from sqlalchemy.orm import Session

# Mock dependency
def get_db_custom():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def test_api():
    print("Testing Security API Functions directly...")
    
    db = SessionLocal()
    try:
        # Test Metrics
        print("\n--- Testing get_security_metrics ---")
        metrics = await get_security_metrics(db=db, _user=None)
        print(f"Metrics Result: {metrics}")
        
        # Test Events
        print("\n--- Testing get_security_events ---")
        events = await get_security_events(limit=10, offset=0, db=db, _user=None)
        print(f"Events Result Keys: {events.keys()}")
        print(f"Total Events: {events.get('total')}")
        if events.get('events'):
            print(f"First Event: {events['events'][0]}")
        else:
            print("No events returned.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_api())
