"""
API Routes for Firewall and Vulnerability Scanner Management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from pydantic import BaseModel

from db.pg_connections import get_db
from api.routes.dependencies import admin_required
from api.security.firewall import firewall_manager, initialize_default_firewall_rules
from api.security.vulnerability_scanner import vulnerability_scanner
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/security", tags=["security"])


class FirewallRuleCreate(BaseModel):
    name: str
    type: str  # ip_block, rate_limit, waf_rule, pattern_match
    priority: str  # high, medium, low
    description: str
    rule_config: dict


class FirewallRuleUpdate(BaseModel):
    is_active: bool


@router.post("/firewall/initialize")
async def initialize_firewall(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """Initialize default firewall rules"""
    try:
        initialize_default_firewall_rules(db)
        firewall_manager.load_rules(db)
        return {"message": "Firewall rules initialized successfully"}
    except Exception as e:
        logger.error(f"Failed to initialize firewall: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/firewall/rules")
async def get_firewall_rules(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """Get all firewall rules"""
    try:
        result = db.execute(text("""
            SELECT id, name, type, is_active, priority, description, rule_config, hits, created_at
            FROM firewall_rules
            ORDER BY priority DESC, created_at DESC
        """))
        
        rules = []
        for row in result:
            rules.append({
                'id': row.id,
                'name': row.name,
                'type': row.type,
                'is_active': row.is_active,
                'priority': row.priority,
                'description': row.description,
                'rule_config': row.rule_config,
                'hits': row.hits,
                'created_at': row.created_at.isoformat() if row.created_at else None
            })
        
        return {"rules": rules}
    except Exception as e:
        logger.error(f"Failed to get firewall rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/firewall/rules")
async def create_firewall_rule(
    rule: FirewallRuleCreate,
    db: Session = Depends(get_db),
    _user=Depends(admin_required)
):
    """Create a new firewall rule"""
    try:
        import json
        result = db.execute(text("""
            INSERT INTO firewall_rules (name, type, is_active, priority, description, rule_config, hits)
            VALUES (:name, :type, true, :priority, :desc, :config, 0)
            RETURNING id
        """), {
            'name': rule.name,
            'type': rule.type,
            'priority': rule.priority,
            'desc': rule.description,
            'config': json.dumps(rule.rule_config)
        })
        rule_id = result.fetchone()[0]
        db.commit()
        
        # Reload rules
        firewall_manager.load_rules(db)
        
        return {"id": rule_id, "message": "Firewall rule created successfully"}
    except Exception as e:
        logger.error(f"Failed to create firewall rule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/firewall/rules/{rule_id}")
async def update_firewall_rule(
    rule_id: int,
    update: FirewallRuleUpdate,
    db: Session = Depends(get_db),
    _user=Depends(admin_required)
):
    """Update firewall rule status"""
    try:
        db.execute(text("""
            UPDATE firewall_rules 
            SET is_active = :active, updated_at = NOW()
            WHERE id = :id
        """), {'active': update.is_active, 'id': rule_id})
        db.commit()
        
        # Reload rules
        firewall_manager.load_rules(db)
        
        return {"message": "Firewall rule updated successfully"}
    except Exception as e:
        logger.error(f"Failed to update firewall rule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/firewall/rules/{rule_id}")
async def delete_firewall_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _user=Depends(admin_required)
):
    """Delete a firewall rule"""
    try:
        db.execute(text("DELETE FROM firewall_rules WHERE id = :id"), {'id': rule_id})
        db.commit()
        
        # Reload rules
        firewall_manager.load_rules(db)
        
        return {"message": "Firewall rule deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete firewall rule: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/full")
async def run_full_scan(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """Run full vulnerability scan"""
    try:
        result = await vulnerability_scanner.run_full_scan(db)
        return result
    except Exception as e:
        logger.error(f"Failed to run vulnerability scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan/database")
async def run_database_scan(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """Run database security scan"""
    try:
        result = await vulnerability_scanner.run_database_scan(db)
        return result
    except Exception as e:
        logger.error(f"Failed to run database scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scans")
async def get_vulnerability_scans(db: Session = Depends(get_db), _user=Depends(admin_required)):
    """Get vulnerability scan history"""
    try:
        result = db.execute(text("""
            SELECT id, scan_type, status, severity, findings, duration_seconds, started_at, completed_at
            FROM vulnerability_scans
            ORDER BY started_at DESC
            LIMIT 20
        """))
        
        scans = []
        for row in result:
            scans.append({
                'id': row.id,
                'scan_type': row.scan_type,
                'status': row.status,
                'severity': row.severity,
                'findings': row.findings,
                'duration_seconds': row.duration_seconds,
                'started_at': row.started_at.isoformat() if row.started_at else None,
                'completed_at': row.completed_at.isoformat() if row.completed_at else None
            })
        
        return {"scans": scans}
    except Exception as e:
        logger.error(f"Failed to get vulnerability scans: {e}")
        raise HTTPException(status_code=500, detail=str(e))
