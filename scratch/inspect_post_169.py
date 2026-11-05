import sys
sys.path.insert(0, '.')
from database.pg_connections import SessionLocal
from database.pg_models import CommunityDiscussion, User, VooCallLog, VooAngleLog
from sqlalchemy import text

db = SessionLocal()
try:
    d = db.query(CommunityDiscussion).filter_by(id=169).first()
    if not d:
        print("Discussion 169 NOT FOUND!")
    else:
        print(f"=== Discussion 169 ===")
        print(f"Title: {d.title}")
        print(f"User ID: {d.user_id}")
        print(f"Post Type: {d.post_type}")
        print(f"Voo Status: {d.voo_status}")
        print(f"Voo Scheduled For: {d.voo_scheduled_for}")
        print(f"Voo Reply ID: {d.voo_reply_id}")
        print(f"Created At: {d.created_at}")
        
        u = db.query(User).filter_by(id=d.user_id).first()
        if u:
            print(f"\n=== Author User ({u.id}) ===")
            print(f"Name: {u.name}")
            print(f"Email: {u.email}")
            print(f"Is Admin: {u.is_admin}")
            print(f"Subscription Status: {getattr(u, 'subscription_status', None)}")
            print(f"Subscription Plan: {getattr(u, 'subscription_plan', None)}")

    print(f"\n=== Voo Call Logs for 169 ===")
    call_logs = db.query(VooCallLog).filter_by(post_id=169).all()
    print(f"Found {len(call_logs)} call logs")
    for cl in call_logs:
        print(f"- Mode: {cl.mode}, Result: {cl.validation_result}, Created: {cl.created_at}")

    print(f"\n=== Voo Angle Logs for 169 ===")
    angle_logs = db.query(VooAngleLog).filter_by(post_id=169).all()
    print(f"Found {len(angle_logs)} angle logs")
    for al in angle_logs:
        print(f"- Type: {al.angle_type}, Opening: {al.opening}, Created: {al.created_at}")

    # Also check discussion 168, 167 etc if any
    print(f"\n=== Recent Discussions ===")
    recents = db.query(CommunityDiscussion).order_by(CommunityDiscussion.id.desc()).limit(5).all()
    for r in recents:
        print(f"ID {r.id}: '{r.title[:40]}' | voo_status={r.voo_status} | sched={r.voo_scheduled_for}")

finally:
    db.close()
