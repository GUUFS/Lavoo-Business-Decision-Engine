"""
Cache Warming Script for Production Deployment
===============================================

This script pre-populates Redis cache with frequently accessed data
to ensure fast response times immediately after deployment.

Usage:
    python scripts/cache_warming.py

Environment Variables Required:
    - DATABASE_URL: PostgreSQL connection string
    - REDIS_URL: Redis connection string (optional, defaults to localhost)
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis
import json

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/dbname")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Cache TTLs (in seconds)
DISPLAYED_REVIEWS_TTL = 300  # 5 minutes
SECURITY_METRICS_TTL = 30     # 30 seconds
SYSTEM_SETTINGS_TTL = 600     # 10 minutes

def get_redis_client():
    """Create Redis client connection"""
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        print("✅ Connected to Redis")
        return client
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("   Cache warming will be skipped (application will work without cache)")
        return None

def get_db_session():
    """Create database session"""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    print("✅ Connected to PostgreSQL")
    return SessionLocal()

def warm_displayed_reviews(redis_client, db_session):
    """
    Pre-cache displayed reviews for homepage.
    This is the most frequently accessed endpoint by public visitors.
    """
    print("\n📦 Warming displayed reviews cache...")
    
    try:
        # Query displayed reviews with full details
        query = text("""
            SELECT 
                r.id, r.user_id, r.business_name, r.review_title,
                r.rating, r.review_text, r.date_submitted, r.verified,
                u.name as user_name,
                dr.display_order
            FROM displayed_reviews dr
            JOIN reviews r ON dr.review_id = r.id
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.status = 'published'
            ORDER BY dr.display_order
        """)
        
        result = db_session.execute(query).fetchall()
        
        # Format reviews
        reviews = []
        for row in result:
            reviews.append({
                "id": row.id,
                "user_name": row.user_name or "Anonymous",
                "business_name": row.business_name,
                "review_title": row.review_title,
                "rating": row.rating,
                "review_text": row.review_text,
                "date_submitted": row.date_submitted.isoformat() if row.date_submitted else None,
                "verified": row.verified or False
            })
        
        # Cache the results
        cache_key = "displayed_reviews:all"
        redis_client.setex(
            cache_key,
            DISPLAYED_REVIEWS_TTL,
            json.dumps(reviews)
        )
        
        print(f"   ✓ Cached {len(reviews)} displayed reviews")
        print(f"   ✓ Cache key: {cache_key}")
        print(f"   ✓ TTL: {DISPLAYED_REVIEWS_TTL}s")
        
    except Exception as e:
        print(f"   ✗ Error warming displayed reviews: {e}")

def warm_security_metrics(redis_client, db_session):
    """
    Pre-cache security metrics for admin dashboard.
    Reduces load on security_metrics_summary view.
    """
    print("\n🔒 Warming security metrics cache...")
    
    try:
        # Query security metrics summary
        query = text("""
            SELECT 
                total_events_24h,
                high_severity_events_24h,
                blocked_attacks_24h,
                failed_logins_24h,
                active_blacklisted_ips,
                active_firewall_rules
            FROM security_metrics_summary
            LIMIT 1
        """)
        
        result = db_session.execute(query).fetchone()
        
        if result:
            # Determine threat level
            high_events = result.high_severity_events_24h or 0
            threat_level = "Low"
            if high_events > 10:
                threat_level = "High"
            elif high_events > 5:
                threat_level = "Medium"
            
            # Get last scan
            last_scan_query = text("""
                SELECT completed_at 
                FROM vulnerability_scans 
                ORDER BY completed_at DESC 
                LIMIT 1
            """)
            last_scan = db_session.execute(last_scan_query).fetchone()
            
            metrics = {
                "threatLevel": threat_level,
                "blockedAttacks": result.blocked_attacks_24h or 0,
                "failedLogins": result.failed_logins_24h or 0,
                "suspiciousActivity": high_events,
                "activeFirewallRules": result.active_firewall_rules or 0,
                "lastSecurityScan": last_scan[0].isoformat() if last_scan and last_scan[0] else "Never"
            }
            
            # Cache the results
            cache_key = "security:metrics"
            redis_client.setex(
                cache_key,
                SECURITY_METRICS_TTL,
                json.dumps(metrics)
            )
            
            print(f"   ✓ Cached security metrics")
            print(f"   ✓ Threat Level: {threat_level}")
            print(f"   ✓ Failed Logins (24h): {metrics['failedLogins']}")
            print(f"   ✓ Blocked Attacks (24h): {metrics['blockedAttacks']}")
        else:
            print("   ⚠️  No security metrics found (empty database)")
            
    except Exception as e:
        print(f"   ✗ Error warming security metrics: {e}")

def warm_system_settings(redis_client, db_session):
    """
    Pre-cache system settings (pricing, etc.) for upgrade page.
    """
    print("\n⚙️  Warming system settings cache...")
    
    try:
        query = text("""
            SELECT monthly_price, yearly_price, commission_rate
            FROM system_settings
            LIMIT 1
        """)
        
        result = db_session.execute(query).fetchone()
        
        if result:
            settings = {
                "monthly_price": float(result.monthly_price) if result.monthly_price else 29.00,
                "yearly_price": float(result.yearly_price) if result.yearly_price else 290.00,
                "commission_rate": float(result.commission_rate) if result.commission_rate else 50.00
            }
            
            cache_key = "system:settings"
            redis_client.setex(
                cache_key,
                SYSTEM_SETTINGS_TTL,
                json.dumps(settings)
            )
            
            print(f"   ✓ Cached system settings")
            print(f"   ✓ Monthly: ${settings['monthly_price']}")
            print(f"   ✓ Yearly: ${settings['yearly_price']}")
        else:
            print("   ⚠️  No system settings found")
            
    except Exception as e:
        print(f"   ✗ Error warming system settings: {e}")

def main():
    """Main cache warming function"""
    print("=" * 60)
    print("🚀 Starting Cache Warming Process")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to Redis
    redis_client = get_redis_client()
    if not redis_client:
        print("\n⚠️  Skipping cache warming (Redis unavailable)")
        print("   Application will fetch data from database directly")
        return
    
    # Connect to Database
    try:
        db_session = get_db_session()
    except Exception as e:
        print(f"\n❌ Failed to connect to database: {e}")
        return
    
    try:
        # Warm all caches
        warm_displayed_reviews(redis_client, db_session)
        warm_security_metrics(redis_client, db_session)
        warm_system_settings(redis_client, db_session)
        
        print("\n" + "=" * 60)
        print("✅ Cache warming completed successfully!")
        print("=" * 60)
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n💡 Tip: Run this script after each deployment for optimal performance")
        
    except Exception as e:
        print(f"\n❌ Cache warming failed: {e}")
    finally:
        db_session.close()
        redis_client.close()

if __name__ == "__main__":
    main()
