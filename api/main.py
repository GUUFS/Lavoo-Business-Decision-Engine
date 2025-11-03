# import the fastAPI library into
from fastapi import FastAPI, Request, HTTPException

# import the function for rendering the HTML sites
from fastapi.responses import FileResponse

# import the function for rendering the static files
from fastapi.staticfiles import StaticFiles

# Load environment variables from .env file (must be done early)
import os
import logging
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment")

# import the database connection file and models from the containing folder
# Using PostgreSQL (Neon) exclusively
from db.pg_connections import engine, SessionLocal, Base, init_db, get_db_info
import db.pg_models as models

from fastapi.middleware.cors import CORSMiddleware

# Set up centralized logging (handles both local and cloud environments)
from config.logging import setup_logging, get_logger

# Initialize logging system
setup_logging(level=logging.INFO if os.getenv('DEBUG') != 'true' else logging.DEBUG)
logger = get_logger(__name__)

# import the router page
from api.routes import index, signup, login, analyzer
from api.routes import ai_db as ai  # PostgreSQL-based AI routes

logger.info("✓ Using Neon PostgreSQL database")


app = FastAPI(debug = True)

# Health check endpoint for monitoring (Railway, Render, DigitalOcean, etc.)
@app.get("/health")
async def health_check():
    """
    Health check endpoint for cloud platform monitoring.
    Returns 200 OK if app is running and database is connected.
    """
    try:
        db_info = get_db_info()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "type": db_info.get("type"),
                "connected": True
            },
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup"""
    try:
        init_db()
        db_info = get_db_info()
        logger.info(f"✓ Database initialized: {db_info['type']} at {db_info['host']}")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


# Enable CORS for (React form requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

# Path to the React build
BASE_DIR = os.path.dirname(os.path.dirname((os.path.abspath(__file__))))
out_dir = os.path.join(BASE_DIR, "web")

# Serve static assets FIRST (must be before routers to avoid catch-all interception)
if os.path.exists(os.path.join(out_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(out_dir, "assets")), name="assets")

# Include API routers (specific routes)
app.include_router(ai.router, prefix="/api")
app.include_router(signup.router, prefix="/api")  # For React frontend that uses /api/signup
app.include_router(login.router, prefix="/api")    # For React frontend that uses /api/login
app.include_router(signup.router)  # Also register without prefix for /signup
app.include_router(login.router)    # Also register without prefix for /login
app.include_router(analyzer.router)

# Include index.router LAST (catch-all for React app)
app.include_router(index.router)