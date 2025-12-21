# import the fastAPI library into
import logging

# Load environment variables from .env file (must be done early)
import os
from datetime import datetime

from fastapi import FastAPI, Depends

# import the function for rendering the HTML sites
# import the function for rendering the static files
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect

from sqlalchemy.orm import Session

from passlib.context import CryptContext

try:
    from dotenv import load_dotenv

    # Try .env.local first (local development), fallback to .env
    if os.path.exists('.env.local'):
        load_dotenv('.env.local')
        print("✅ Environment variables loaded from .env.local file")
    else:
        load_dotenv()  # Load .env file
        print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed, using system environment")

# import the database connection file and models from the containing folder
# Using PostgreSQL (Neon) exclusively
from fastapi.middleware.cors import CORSMiddleware

# Set up centralized logging (handles both local and cloud environments)
from config.logging import get_logger, setup_logging
from db.pg_connections import get_db_info, init_db, get_db
from db.pg_models import User, CreateOrderRequest, CaptureRequest
from db.pg_connections import SessionLocal
from api.cache import init_cache, close_cache

# Initialize logging system
setup_logging(level=logging.INFO if os.getenv("DEBUG") != "true" else logging.DEBUG)
logger = get_logger(__name__)

# import the router page
from api.routes import ai_db as ai  # PostgreSQL-based AI routes
from api.routes import analyzer, index, login, signup, admin, dependencies, business_analyzer, earnings
from api.routes import customer_service, reviews, alerts, insights, referrals, security

from api.routes.control import revenue, users, dashboard, settings

#  Payment routes
from subscriptions import paypal, flutterwave, stripe, commissions, stripe_connect

logger.info("✓ Using Neon PostgreSQL database")


app = FastAPI(debug=True)
print("APP TYPE:", type(app))


origins = ["http://localhost:3000",
           "http://localhost:5173",
    "http://localhost:8080"]

# Enable CORS for (React form requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


# Health check endpoint for monitoring (Railway, Render, DigitalOcean, etc.)
@app.api_route("/health", methods=["GET", "HEAD"])
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
            "database": {"type": db_info.get("type"), "connected": True},
            "version": "1.0.0",
        }
    except Exception as e:
        return {"status": "unhealthy", "timestamp": datetime.now().isoformat(), "error": str(e)}


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# try creating an admin user if not exists
async def create_admin_user(db: Session=Depends(get_db)):
    admin_email = os.getenv("admin_email","admin@gmail.com")
    admin_password = os.getenv("admin_password","admin123")
    password = pwd_context.hash(admin_password)
    admin_name = os.getenv("admin_name","Admin")

    try:
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            logger.info("✓ Admin user already exists")
            return

        new_admin = User(
                name="Admin",
                email=admin_email,
                password= password,
                confirm_password = password,
                is_admin=True
        )
        db.add(new_admin)
        db.commit()
        logger.info("✓ Admin user created",admin_email)
    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and caching on application startup"""
    try:
        init_db()
        db_info = get_db_info()
        logger.info(f"✓ Database initialized: {db_info['type']} at {db_info['host']}")

        # Auto-migration for is_active column
        from sqlalchemy import text
        db = SessionLocal()
        try:
            # Check if column exists (PostgreSQL specific, but 'ADD COLUMN IF NOT EXISTS' handles it in modern PG)
            # However, IF NOT EXISTS is PG 9.6+. Assuming safe.
            # If SQLite, this syntax might fail. The project uses PG exclusively per line 32.
            # Optimizing partial migrations into fewer round-trips
            # Postgres supports adding multiple columns in one statement
            try:
                db.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
                    ADD COLUMN IF NOT EXISTS department VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS location VARCHAR(100) DEFAULT 'Nigeria',
                    ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT 'IT Operations',
                    ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS email_notifications BOOLEAN DEFAULT TRUE;
                """))
                
                db.execute(text("ALTER TABLE reviews ADD COLUMN IF NOT EXISTS is_attended BOOLEAN DEFAULT FALSE"))
            
            except Exception as e:
                # If batch fails (e.g. SQLite doesn't support multiple ADD COLUMN), fall back to individual or log
                logger.warning(f"Batch migration warning (will attempt individual if critical): {e}")

            db.commit()
            logger.info("✓ Checked/Added columns to users and reviews tables")
        except Exception as e:
            logger.warning(f"Migration warning: {e}")
            db.rollback()
        finally:
            db.close()

        # Create admin user
        await create_admin_user(SessionLocal())

        # Initialize Redis/in-memory cache
        await init_cache()

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    await close_cache()

origins = ["http://localhost:3000",
           "http://localhost:5173",
    "http://localhost:8080"]

# Enable CORS for (React form requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Path to the React build
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(BASE_DIR, "web")

# Serve static assets FIRST (must be before routers to avoid catch-all interception)
if os.path.exists(os.path.join(out_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(out_dir, "assets")), name="assets")

# Include API routers (specific routes)
app.include_router(ai.router, prefix="/api")
app.include_router(signup.router, prefix="/api")  # For React frontend that uses /api/signup
app.include_router(login.router, prefix="/api")  # For React frontend that uses /api/login
app.include_router(signup.router)  # Also register without prefix for /signup
app.include_router(login.router)  # Also register without prefix for /login
app.include_router(business_analyzer.router)  # Business analysis endpoints (YOUR FIX)
app.include_router(analyzer.router)
app.include_router(admin.router)
app.include_router(paypal.router)
app.include_router(flutterwave.router)
app.include_router(stripe.router)
app.include_router(customer_service.router)
app.include_router(reviews.router)
app.include_router(alerts.router)  # Clinton's feature
app.include_router(insights.router)  # Clinton's feature
app.include_router(referrals.router)  # Clinton's feature
app.include_router(earnings.router)
app.include_router(commissions.router)
app.include_router(revenue.router)
app.include_router(settings.router) # Register settings router
app.include_router(stripe_connect.router)
app.include_router(security.router, prefix="/api")
app.include_router(users.router)
app.include_router(dashboard.router)

# Include index.router LAST (catch-all for React app)
app.include_router(index.router)
