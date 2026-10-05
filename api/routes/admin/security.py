
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta

from database.pg_connections import get_db
from api.routes.dependencies import admin_required
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/security", tags=["security"])

@router.get("/metrics")
async def get_security_metrics(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """
    Real-time security metrics for the admin dashboard's stat cards. Field
    names here must match app/(admin)/admin/security/page.tsx's
    SecurityMetrics interface exactly, since that's the only consumer and it
    has no fallback beyond `?? 0`.

    security_events is the authoritative event log — a failed login is
    recorded there too (see api/routes/auth/login.py), in addition to its
    own row in failed_login_attempts, so total_events counts security_events
    alone rather than adding both tables and double-counting.
    """
    try:
        total_events = db.execute(text("SELECT COUNT(*) FROM security_events")).scalar() or 0

        failed_logins_today = db.execute(text(
            "SELECT COUNT(*) FROM failed_login_attempts WHERE created_at >= date_trunc('day', NOW())"
        )).scalar() or 0

        blocked_ips = db.execute(text(
            "SELECT COUNT(*) FROM ip_blacklist WHERE is_active = true"
        )).scalar() or 0

        vulnerability_scans = db.execute(text("SELECT COUNT(*) FROM vulnerability_scans")).scalar() or 0

        critical_events = db.execute(text(
            "SELECT COUNT(*) FROM security_events WHERE severity ILIKE 'critical'"
        )).scalar() or 0

        return {
            "total_events": int(total_events),
            "failed_logins_today": int(failed_logins_today),
            "blocked_ips": int(blocked_ips),
            "vulnerability_scans": int(vulnerability_scans),
            "critical_events": int(critical_events),
        }
    except Exception as e:
        logger.error(f"Failed to get security metrics: {str(e)}")
        return {
            "total_events": 0,
            "failed_logins_today": 0,
            "blocked_ips": 0,
            "vulnerability_scans": 0,
            "critical_events": 0,
            "error": str(e),
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
