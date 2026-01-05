
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta

from db.pg_connections import get_db
from db.pg_models import SecurityMetricsSummary, FailedLoginAttempt, SecurityEvent
from api.routes.dependencies import admin_required
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/security", tags=["security"])

@router.get("/metrics")
async def get_security_metrics(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """
    Get real-time security metrics for the admin dashboard.
    Returns threat level, attack counts, failed logins, and firewall status.
    """
    try:
        # Use Raw SQL to query the view - safer handling of nulls/types
        query = text("SELECT * FROM security_metrics_summary LIMIT 1")
        result = db.execute(query).fetchone()
        
        # Get TOTAL counts for failed logins and blocked IPs (All Time)
        total_failed_logins = db.execute(text("SELECT COUNT(*) FROM failed_login_attempts")).scalar() or 0
        total_blocked_ips = db.execute(text("SELECT COUNT(*) FROM ip_blacklist WHERE is_active = true")).scalar() or 0
        
        if not result:
             return {
                "threatLevel": "Low",
                "blockedAttacks": int(total_blocked_ips),
                "failedLogins": int(total_failed_logins),
                "suspiciousActivity": 0,
                "activeFirewallRules": 0,
                "lastSecurityScan": "Never"
            }

        # Convert Row to dict for safer access
        # SQLAlchemy 1.4/2.0+ supports ._mapping
        row_dict = result._mapping if hasattr(result, '_mapping') else dict(result)
        
        # Determine threat level based on high severity events in last 24h
        high_events = row_dict.get('high_severity_events_24h') or 0
        threat_level = "Low"
        if high_events > 10:
            threat_level = "High"
        elif high_events > 5:
            threat_level = "Medium"

        # Get last scan timestamp
        last_scan = db.execute(text("SELECT completed_at FROM vulnerability_scans ORDER BY completed_at DESC LIMIT 1")).fetchone()
        last_scan_date = "Never"
        if last_scan and last_scan[0]:
             last_scan_date = last_scan[0].isoformat()

        # Get TOTAL firewall blocks from security_events
        blocked_attacks = db.execute(text("SELECT COUNT(*) FROM security_events WHERE type = 'firewall block'")).scalar() or 0

        return {
            "threatLevel": threat_level,
            "blockedAttacks": int(blocked_attacks),
            "failedLogins": int(total_failed_logins),
            "suspiciousActivity": int(high_events),
            "activeFirewallRules": int(row_dict.get('active_firewall_rules') or 0),
            "lastSecurityScan": last_scan_date
        }
    except Exception as e:
        logger.error(f"Failed to get security metrics: {str(e)}")
        # Return zeroed metrics on error
        return {
            "threatLevel": "Low",
            "blockedAttacks": 0,
            "failedLogins": 0,
            "suspiciousActivity": 0,
            "activeFirewallRules": 0,
            "lastSecurityScan": "Never",
            "error": str(e)
        }


@router.get("/events")
async def get_security_events(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user=Depends(admin_required)
):
    try:
        # Use Raw SQL for maximum robustness against ORM/Type issues
        # Union security_events and failed_login_attempts
        query = text("""
            SELECT 
                id::text, 
                type, 
                severity, 
                description, 
                host(ip_address) as ip_str, 
                created_at, 
                status,
                'event' as source
            FROM security_events
            UNION ALL
            SELECT 
                'attempt_' || id::text as id, 
                'failed_login' as type, 
                'medium' as severity, 
                'Failed login attempt from ' || email as description, 
                host(ip_address) as ip_str, 
                created_at, 
                'logged' as status,
                'attempt' as source
            FROM failed_login_attempts
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.execute(query, {"limit": limit, "offset": offset}).fetchall()
        
        # Count query for pagination (approximate is fine for performance)
        total_query = text("SELECT (SELECT COUNT(*) FROM security_events) + (SELECT COUNT(*) FROM failed_login_attempts)")
        total = db.execute(total_query).scalar() or 0
        
        events = []
        events = []
        for row in result:
             # Safer access
            row_dict = row._mapping if hasattr(row, '_mapping') else dict(row)
            events.append({
                "id": row_dict['id'],
                "type": row_dict['type'],
                "severity": row_dict.get('severity'),
                "description": row_dict.get('description'),
                "ip_address": row_dict.get('ip_str'), 
                "created_at": row_dict['created_at'].isoformat() if row_dict.get('created_at') else None,
                "source": row_dict.get('source'),
                "status": row_dict.get('status')
            })

        return {
            "events": events,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get security events: {str(e)}")
        # Return empty list instead of 500 to keep UI alive
        return {
            "events": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e)
        }


@router.get("/firewall-rules")
async def get_firewall_rules(db: Session = Depends(get_db), _user=Depends(admin_required)):
    try:
        result = db.execute(text("SELECT * FROM firewall_rules ORDER BY priority DESC, created_at DESC")).fetchall()
        rules = []
        for row in result:
             # Safer access
            row_dict = row._mapping if hasattr(row, '_mapping') else dict(row)
            rules.append({
                "id": row_dict['id'],
                "name": row_dict['name'],
                "description": row_dict.get('description', ''),
                "type": row_dict['type'],
                "status": row_dict.get('status', 'active' if row_dict.get('is_active') else 'inactive'),
                "hits": row_dict.get('hits', 0)
            })
        return {"rules": rules}
    except Exception as e:
        logger.error(f"Failed to get firewall rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve firewall rules")


@router.get("/vulnerability-scans")
async def get_vulnerability_scans(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db), 
    _user=Depends(admin_required)
):
    try:
        # Get total count for pagination
        total = db.execute(text("SELECT COUNT(*) FROM vulnerability_scans")).scalar() or 0
        
        result = db.execute(text("""
            SELECT * FROM vulnerability_scans 
            ORDER BY started_at DESC 
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset}).fetchall()
        
        scans = []
        for row in result:
             # Safer access
            row_dict = row._mapping if hasattr(row, '_mapping') else dict(row)
            scans.append({
                "id": row_dict['id'],
                "scan_type": row_dict['scan_type'],
                "status": row_dict['status'],
                "findings": row_dict.get('findings'),
                "severity": row_dict.get('severity'),
                "started_at": row_dict['started_at'].isoformat() if row_dict.get('started_at') else None,
                "duration_seconds": row_dict.get('duration_seconds')
            })
        return {
            "scans": scans,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get vulnerability scans: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vulnerability scans")


@router.get("/top-attacking-ips")
async def get_top_attacking_ips(db: Session = Depends(get_db), _user=Depends(admin_required)):
    try:
        result = db.execute(text("SELECT * FROM top_attacking_ips")).fetchall()
        ips = []
        ips = []
        for row in result:
             # Safer access
            row_dict = row._mapping if hasattr(row, '_mapping') else dict(row)
            ips.append({
                "ip_address": row_dict['ip_address'],
                "total_events": row_dict.get('total_events', 0),
                "last_seen": row_dict['last_seen'].isoformat() if row_dict.get('last_seen') else None,
                "event_types": row_dict.get('event_types')
            })
        return {"ips": ips}
    except Exception as e:
        logger.error(f"Failed to get top attacking IPs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve attacking IPs")


@router.post("/block-ip")
async def block_ip(request: Request, db: Session = Depends(get_db), user=Depends(admin_required)):
    try:
        data = await request.json()
        ip = data.get("ip")
        reason = data.get("reason")

        if not ip or not reason:
            raise HTTPException(status_code=400, detail="IP and reason required")

        db.execute(
            text("INSERT INTO ip_blacklist (ip_address, reason, blocked_by) VALUES (:ip, :reason, :blocked_by)"),
            {"ip": ip, "reason": reason, "blocked_by": user.id}
        )
        
        # Log event
        db.execute(
            text("INSERT INTO security_events (type, severity, description, ip_address, user_id) VALUES ('blocked_ip', 'high', :desc, :ip, :user_id)"),
            {"desc": f"IP blocked: {reason}", "ip": ip, "user_id": user.id}
        )
        
        db.commit()
        return {"message": "IP blocked successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to block IP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to block IP")


@router.post("/unblock-ip")
async def unblock_ip(request: Request, db: Session = Depends(get_db), user=Depends(admin_required)):
    try:
        data = await request.json()
        ip = data.get("ip")
        
        if not ip:
            raise HTTPException(status_code=400, detail="IP required")

        db.execute(
            text("UPDATE ip_blacklist SET is_active = false WHERE ip_address = :ip"),
            {"ip": ip}
        )
        db.commit()
        return {"message": "IP unblocked successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to unblock IP: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to unblock IP")
