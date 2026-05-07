"""
Seed 2 creator listings from real users to verify all fields work.
Usage: PYTHONPATH=. uv run python scripts/seed_creator_listings.py
"""
import sys
from dotenv import load_dotenv

load_dotenv(".env.local")

from database.pg_connections import SessionLocal
from database.pg_models import CreatorListing, User


def main():
    db = SessionLocal()
    try:
        users = db.query(User).limit(2).all()
        if not users:
            print("ERROR: No users found in database — create a user first.")
            sys.exit(1)

        user1 = users[0]
        user2 = users[1] if len(users) > 1 else users[0]

        listings_data = [
            {
                "user_id": user1.id,
                "title": "Social Media Content Automation Playbook",
                "description": "A step-by-step playbook for automating weekly social media content using AI tools. Covers scheduling, caption generation, and cross-platform posting.",
                "full_description": "This playbook walks you through setting up a fully automated social media pipeline. You'll learn how to connect AI writing tools for caption generation, schedule posts across Instagram, TikTok, and LinkedIn from one dashboard, and track performance metrics automatically. Includes templates, tool links, and a 7-day launch checklist.",
                "listing_type": "Playbook",
                "category": "Marketing",
                "price": 0.0,
                "tags": ["social media", "automation", "content", "AI", "scheduling"],
                "features": [
                    "7-day launch checklist",
                    "AI caption generation templates",
                    "Cross-platform scheduling guide",
                    "Performance tracking setup",
                    "Works with Buffer, Later, and Hootsuite",
                ],
                "icon_name": "Zap",
                "color_theme": "orange",
                "purchase_url": None,
            },
            {
                "user_id": user2.id,
                "title": "Freelance Invoice & Proposal Automation Kit",
                "description": "A ready-to-use template kit and workflow guide for automating client proposals, contracts, and invoice reminders as a freelancer.",
                "full_description": "Stop chasing clients manually. This kit includes proposal templates triggered by intake forms, contract auto-send workflows, invoice generation on project completion, and payment reminder sequences at 3-day and 7-day overdue intervals. Built for freelancers using tools like Dubsado, HoneyBook, or Bonsai.",
                "listing_type": "Template",
                "category": "Automation",
                "price": 29.0,
                "tags": ["freelance", "invoicing", "proposals", "contracts", "automation"],
                "features": [
                    "Proposal template triggered by intake form",
                    "Auto contract send on proposal acceptance",
                    "Invoice generation on project completion",
                    "Payment reminder sequences (3-day + 7-day)",
                    "Compatible with Dubsado, HoneyBook, Bonsai",
                ],
                "icon_name": "Package",
                "color_theme": "blue",
                "purchase_url": "https://example.com/freelance-kit",
            },
        ]

        for data in listings_data:
            existing = db.query(CreatorListing).filter_by(
                user_id=data["user_id"], title=data["title"]
            ).first()
            if existing:
                print(f"  SKIP (already exists): {data['title']}")
                continue

            listing = CreatorListing(**data)
            db.add(listing)
            db.flush()
            print(
                f"  CREATED id={listing.id}: [{data['listing_type']}] {data['title']}"
                f" — user_id={data['user_id']}, price=${data['price']}"
            )

        db.commit()
        print("\nSeed complete. Verifying all fields round-trip...")

        for data in listings_data:
            row = db.query(CreatorListing).filter_by(
                user_id=data["user_id"], title=data["title"]
            ).first()
            assert row is not None, f"Missing row for {data['title']}"
            assert row.listing_type == data["listing_type"], f"listing_type mismatch for {data['title']}"
            assert row.tags == data["tags"], f"tags mismatch for {data['title']}"
            assert row.features == data["features"], f"features mismatch for {data['title']}"
            assert row.icon_name == data["icon_name"], f"icon_name mismatch for {data['title']}"
            assert row.color_theme == data["color_theme"], f"color_theme mismatch for {data['title']}"
            assert row.purchase_url == data["purchase_url"], f"purchase_url mismatch for {data['title']}"
            print(f"  OK: {row.title} (id={row.id}, tags={row.tags[:2]}...)")

        print("\nAll fields verified successfully.")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
