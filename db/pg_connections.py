# db/pg_connections.py
"""
PostgreSQL database connections for production deployment.
This file handles both PostgreSQL (production) and SQLite (local development).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Get database URL from environment variable (Render will provide this)
# Falls back to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL")

# Render provides PostgreSQL URL starting with 'postgres://'
# But SQLAlchemy 2.0+ requires 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# If no DATABASE_URL provided, use SQLite for local development
if not DATABASE_URL:
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(CURRENT_DIR, "aitugo.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    print(f"ℹ️  Using SQLite for local development: {db_path}")
    # SQLite-specific configuration
    connect_args = {"check_same_thread": False}
    is_sqlite = True
else:
    print(f"✓ Using PostgreSQL database")
    # PostgreSQL doesn't need check_same_thread
    connect_args = {}
    is_sqlite = False

# Create engine with appropriate settings
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        # Connection pool settings (only for PostgreSQL)
        pool_pre_ping=True if not is_sqlite else False,
        pool_recycle=3600 if not is_sqlite else None,
    )
    # Test connection
    with engine.connect() as conn:
        pass
except Exception as e:
    print(f"⚠️  Database connection failed: {e}")
    print(f"⚠️  Falling back to SQLite...")
    # Fallback to SQLite if PostgreSQL connection fails
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(CURRENT_DIR, "aitugo.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    connect_args = {"check_same_thread": False}
    is_sqlite = True
    engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Create session factory
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Declare base for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Used in FastAPI route dependencies.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    Call this on application startup.
    """
    from .pg_models import User, AITool  # Import models
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def get_db_info():
    """
    Get information about current database connection.
    Useful for debugging.
    
    Returns:
        dict: Database connection info
    """
    db_type = "postgresql" if "postgresql" in str(engine.url) else "sqlite"
    return {
        "type": db_type,
        "url": str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url),
        "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
    }
