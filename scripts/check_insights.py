#!/usr/bin/env python3
"""Quick script to check insights in database."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(".env.local")

from db.pg_connections import SessionLocal
from db.pg_models import Insight

def main():
    session = SessionLocal()
    try:
        insights = session.query(Insight).order_by(Insight.created_at.desc()).limit(5).all()
        print(f"Found {len(insights)} insights:\n")
        for i in insights:
            url_status = "✅" if i.url and i.url.startswith("http") else "❌"
            print(f"{url_status} Title: {i.title[:60]}")
            print(f"   URL: {i.url}")
            print(f"   Date: {i.date}")
            print("---")
    finally:
        session.close()

if __name__ == "__main__":
    main()
