# db/pg_connections.py
"""
PostgreSQL database connection manager.

This module handles PostgreSQL connections for any cloud deployment platform
(Railway, DigitalOcean, Render, Heroku, AWS, etc.) or local development.

Environment Variables Required:
    DATABASE_URL: Full PostgreSQL connection URL
    Format: postgresql://user:password@host:port/database?sslmode=require

Logging:
    - Outputs to stdout (works in all cloud environments)
    - Compatible with Railway, DigitalOcean, Render, Heroku, etc.
"""

import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file into environment
except ImportError:
    # python-dotenv not installed, will use system environment variables
    pass

# Base class for all ORM models
Base = declarative_base()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL environment variable not set!")
    print("Please set DATABASE_URL in your .env file or environment")
    print("Format: postgresql://user:password@host:port/database")
    sys.exit(1)

print("✓ Connecting to PostgreSQL database...")

try:
    # Create PostgreSQL engine
    # Connection pooling settings optimized for cloud deployments
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=300,  # Recycle connections every 5 minutes (prevents stale connections)
        pool_size=15,  # Number of permanent connections
        max_overflow=20,  # Additional connections when needed
        echo=False,  # Set to True for SQL query logging (debugging)
    )

    # Test the connection
    with engine.connect() as conn:
        print("✓ Successfully connected to PostgreSQL!")

except Exception as e:
    print("❌ Failed to connect to PostgreSQL database!")
    print(f"Error: {e}")
    print(f"URL format: {DATABASE_URL.split('@')[0]}@***")
    sys.exit(1)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database tables.
    Creates all tables defined in the models.
    """
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def get_db_info():
    """
    Get information about current database connection.

    Returns:
        dict: Database connection info
    """
    return {
        "type": "postgresql",
        "driver": "psycopg2",
        "host": str(engine.url).split("@")[-1].split("/")[0]
        if "@" in str(engine.url)
        else "unknown",
        "database": engine.url.database,
        "url": str(engine.url).replace(str(engine.url.password), "***")
        if engine.url.password
        else str(engine.url),
        "pool_size": engine.pool.size() if hasattr(engine.pool, "size") else None,
    }


def get_db():
    """
    Dependency function for FastAPI routes.
    Yields a database session and closes it after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
