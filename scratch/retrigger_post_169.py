import sys
import time
import asyncio
from datetime import datetime, timezone
sys.path.insert(0, '.')

for attempt in range(5):
    try:
        from database.pg_connections import SessionLocal
        from database.pg_models import CommunityDiscussion, DiscussionReply
        from api.routes.community.community import cron_process_pending_voo_replies
        
        db = SessionLocal()
        # Test connection
        db.execute(text("SELECT 1")) if False else None
        break
    except Exception as e:
        print(f"Connection attempt {attempt+1} failed: {e}. Retrying in 3s...")
        time.sleep(3)
else:
    print("Failed to connect after 5 attempts.")
    sys.exit(1)

try:
    d = db.query(CommunityDiscussion).filter_by(id=169).first()
    if not d:
        print("Discussion 169 not found!")
    else:
        print(f"Post 169 current status: {d.voo_status}")
        d.voo_status = "scheduled"
        d.voo_scheduled_for = datetime.now(timezone.utc)
        db.commit()
        print("Set Post 169 status to 'scheduled'. Triggering cron...")
        asyncio.run(cron_process_pending_voo_replies(db))
        
        # Check result
        db.refresh(d)
        print(f"Post 169 updated status: {d.voo_status}")
        print(f"Post 169 reply id: {d.voo_reply_id}")
        if d.voo_reply_id:
            reply = db.query(DiscussionReply).filter_by(id=d.voo_reply_id).first()
            if reply:
                print(f"\n=== Voo Reply Posted to Thread ===\n{reply.content}")
finally:
    db.close()
