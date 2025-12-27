from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta

from db.pg_connections import get_db
from db.pg_models import SecurityMetricsSummary
from api.routes.dependencies import admin_required
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/security", tags=["security"])

@router.get("/metrics")
async def get_security_metrics(db: Session = Depends(get_db), _user=Depends(admin_required)):
    try:
        # Get metrics from the view security_metrics_summary using ORM
        result = db.query(SecurityMetricsSummary).first()
        
        if not result:
            # Fallback for empty table
            return {
                "threatLevel": "Low",
                "blockedAttacks": 0,
                "failedLogins": 0,
                "suspiciousActivity": 0,
                "activeFirewallRules": 0,
                "lastSecurityScan": "Never"
            }

        # Determine threat level
        high_events = result.high_severity_events_24h or 0
        threat_level = "Low"
        if high_events > 10:
            threat_level = "High"
        elif high_events > 5:
            threat_level = "Medium"

        # Get last scan
        last_scan = db.execute(text("SELECT completed_at FROM vulnerability_scans ORDER BY completed_at DESC LIMIT 1")).fetchone()
        
        return {
            "threatLevel": threat_level,
            "blockedAttacks": result.active_blacklisted_ips or 0,  # Show count of blacklisted IPs
            "failedLogins": result.failed_logins_24h or 0,
            "suspiciousActivity": high_events,
            "activeFirewallRules": result.active_firewall_rules or 0,
            "lastSecurityScan": last_scan[0].isoformat() if last_scan and last_scan[0] else "Never"
        }
    except Exception as e:
        logger.error(f"Failed to get security metrics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security metrics")

@router.get("/events")
async def get_security_events(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user=Depends(admin_required)
):
    try:
        result = db.execute(
            text("SELECT * FROM security_events ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset}
        ).fetchall()
        
        total = db.execute(text("SELECT COUNT(*) FROM security_events")).scalar() or 0
        
        events = []
        for row in result:
            # Handle potential differences in row structure if needed
            events.append({
                "id": row.id,
                "type": row.type,
                "severity": row.severity,
                "description": row.description,
                "ip_address": row.ip_address,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "status": getattr(row, 'status', 'logged')
            })

        return {
            "events": events,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get security events: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security events")


@router.get("/firewall-rules")
async def get_firewall_rules(db: Session = Depends(get_db), _user=Depends(admin_required)):
    try:
        result = db.execute(text("SELECT * FROM firewall_rules ORDER BY priority DESC, created_at DESC")).fetchall()
        rules = []
        for row in result:
            rules.append({
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "type": row.type,
                "status": row.status if hasattr(row, 'status') else ('active' if row.is_active else 'inactive'),
                "hits": getattr(row, 'hits', 0)
            })
        return {"rules": rules}
    except Exception as e:
        logger.error(f"Failed to get firewall rules: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve firewall rules")


@router.get("/vulnerability-scans")
async def get_vulnerability_scans(db: Session = Depends(get_db), _user=Depends(admin_required)):
    try:
        result = db.execute(text("SELECT * FROM vulnerability_scans ORDER BY started_at DESC LIMIT 10")).fetchall()
        scans = []
        for row in result:
            scans.append({
                "id": row.id,
                "scan_type": row.scan_type,
                "status": row.status,
                "findings": row.findings,
                "severity": row.severity,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "duration_seconds": row.duration_seconds
            })
        return {"scans": scans}
    except Exception as e:
        logger.error(f"Failed to get vulnerability scans: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vulnerability scans")

@router.get("/top-attacking-ips")
async def get_top_attacking_ips(db: Session = Depends(get_db), _user=Depends(admin_required)):
    try:
        result = db.execute(text("SELECT * FROM top_attacking_ips")).fetchall()
        ips = []
        for row in result:
            ips.append({
                "ip_address": row.ip_address,
                "total_events": row.total_events,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                "event_types": row.event_types
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
