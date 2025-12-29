#!/usr/bin/env python3
"""Fix alembic version to known good state"""

from db.pg_connections import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Get current version
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    current = result.scalar()
    print(f"Current version in DB: {current}")
    
    # Update to latest common ancestor migration
    conn.execute(text("UPDATE alembic_version SET version_num = 'ef3c9479f1ad'"))
    conn.commit()
    print("✅ Updated to ef3c9479f1ad (latest before dual heads)")
