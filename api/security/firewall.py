"""
Dynamic Firewall with Real-time Rule Processing
Implements IP blocking, rate limiting, WAF rules, and pattern matching
"""

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Optional, Any
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from config.logging import get_logger

logger = get_logger(__name__)

class FirewallRule:
    def __init__(self, id: int, name: str, type: str, status: str, priority: str, 
                 rule_config: dict, hits: int = 0):
        self.id = id
        self.name = name
        self.type = type  # ip_block, rate_limit, waf_rule, geo_block, pattern_match
        self.status = status  # active, inactive
        self.priority = priority  # high, medium, low
        self.rule_config = rule_config
        self.hits = hits


class FirewallManager:
    def __init__(self):
        self.rules: List[FirewallRule] = []
        self.request_counts: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
    def load_rules(self, db: Session):
        """Load active firewall rules from database"""
        try:
            result = db.execute(text("""
                SELECT * FROM firewall_rules 
                WHERE is_active = true 
                ORDER BY 
                    CASE priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        WHEN 'low' THEN 3 
                    END
            """))
            
            self.rules = []
            for row in result:
                self.rules.append(FirewallRule(
                    id=row.id,
                    name=row.name,
                    type=row.type,
                    status='active',
                    priority=row.priority,
                    rule_config=json.loads(row.rule_config) if isinstance(row.rule_config, str) else row.rule_config,
                    hits=row.hits or 0
                ))
            
            logger.info(f"Loaded {len(self.rules)} active firewall rules")
        except Exception as e:
            logger.error(f"Failed to load firewall rules: {e}")
    
    async def process_request(self, request: Request, db: Session) -> Optional[dict]:
        """
        Process request through firewall rules
        Returns None if allowed, dict with error if blocked
        """
        try:
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            path = request.url.path
            method = request.method
            
            # Reload rules periodically (every 100 requests)
            if not hasattr(self, '_request_count'):
                self._request_count = 0
            self._request_count += 1
            if self._request_count % 100 == 0:
                self.load_rules(db)
            
            # Process each rule
            for rule in self.rules:
                should_block = self._evaluate_rule(rule, {
                    'ip': client_ip,
                    'user_agent': user_agent,
                    'path': path,
                    'method': method
                })
                
                if should_block:
                    # Increment hit counter
                    self._increment_rule_hits(db, rule.id)
                    
                    # Log blocked request
                    db.execute(text("""
                        INSERT INTO security_events (type, severity, ip_address, description, status, details)
                        VALUES (:type, :severity, :ip, :desc, :status, :details)
                    """), {
                        'type': 'firewall_block',
                        'severity': 'high' if rule.priority == 'high' else 'medium',
                        'ip': client_ip,
                        'desc': f"Request blocked by firewall rule: {rule.name}",
                        'status': 'blocked',
                        'details': json.dumps({'rule': rule.name, 'path': path, 'method': method})
                    })
                    db.commit()
                    
                    logger.warning(f"Request blocked by firewall: rule={rule.name}, ip={client_ip}, path={path}")
                    
                    return {
                        'error': 'Access denied',
                        'message': 'Request blocked by firewall'
                    }
            
            return None  # Allow request
            
        except Exception as e:
            logger.error(f"Firewall processing error: {e}")
            return None  # Don't block on errors
    
    def _evaluate_rule(self, rule: FirewallRule, context: dict) -> bool:
        """Evaluate a single firewall rule"""
        if rule.type == 'ip_block':
            return self._check_ip_block(rule, context['ip'])
        elif rule.type == 'rate_limit':
            return self._check_rate_limit(rule, context['ip'])
        elif rule.type == 'waf_rule':
            return self._check_waf_rule(rule, context)
        elif rule.type == 'pattern_match':
            return self._check_pattern_match(rule, context)
        return False
    
    def _check_ip_block(self, rule: FirewallRule, ip: str) -> bool:
        """Check if IP is in blocked list"""
        blocked_ips = rule.rule_config.get('blocked_ips', [])
        return ip in blocked_ips
    
    def _check_rate_limit(self, rule: FirewallRule, ip: str) -> bool:
        """Check rate limit for IP"""
        max_requests = rule.rule_config.get('max_requests', 100)
        time_window = rule.rule_config.get('time_window', 60000) / 1000  # Convert to seconds
        
        key = f"{rule.id}:{ip}"
        now = datetime.now()
        
        if key not in self.request_counts or 'reset_time' not in self.request_counts[key]:
            self.request_counts[key] = {
                'count': 1,
                'reset_time': now + timedelta(seconds=time_window)
            }
            return False
        
        record = self.request_counts[key]
        
        if now > record['reset_time']:
            # New window
            self.request_counts[key] = {
                'count': 1,
                'reset_time': now + timedelta(seconds=time_window)
            }
            return False
        
        record['count'] += 1
        
        if record['count'] > max_requests:
            return True  # Block - rate limit exceeded
        
        return False
    
    def _check_waf_rule(self, rule: FirewallRule, context: dict) -> bool:
        """Check WAF (Web Application Firewall) rule"""
        pattern = rule.rule_config.get('pattern')
        if not pattern:
            return False
        
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            
            # Check path
            if regex.search(context['path']):
                return True
            
            # Check user agent
            if regex.search(context['user_agent']):
                return True
            
        except re.error as e:
            logger.error(f"Invalid regex pattern in WAF rule: {e}")
        
        return False
    
    def _check_pattern_match(self, rule: FirewallRule, context: dict) -> bool:
        """Check pattern match rule"""
        # Check user agent blocking
        blocked_agents = rule.rule_config.get('blocked_user_agents', [])
        if blocked_agents:
            user_agent_lower = context['user_agent'].lower()
            for blocked_agent in blocked_agents:
                if blocked_agent.lower() in user_agent_lower:
                    return True
        
        # Check method restrictions
        allowed_methods = rule.rule_config.get('allowed_methods', [])
        if allowed_methods and context['method'] not in allowed_methods:
            return True
        
        return False
    
    def _increment_rule_hits(self, db: Session, rule_id: int):
        """Increment hit counter for rule"""
        try:
            db.execute(text("""
                UPDATE firewall_rules 
                SET hits = hits + 1, updated_at = NOW() 
                WHERE id = :id
            """), {'id': rule_id})
            db.commit()
        except Exception as e:
            logger.error(f"Failed to increment rule hits: {e}")


# Global firewall manager instance
firewall_manager = FirewallManager()


def initialize_default_firewall_rules(db: Session):
    """Initialize default firewall rules if none exist"""
    try:
        result = db.execute(text("SELECT COUNT(*) as count FROM firewall_rules"))
        count = result.fetchone()[0]
        
        if count > 0:
            logger.info("Firewall rules already initialized")
            return
        
        logger.info("Creating default firewall rules")
        
        # Rule 1: SQL Injection Protection
        db.execute(text("""
            INSERT INTO firewall_rules (name, type, is_active, priority, description, rule_config, hits)
            VALUES (:name, :type, true, :priority, :desc, :config, 0)
        """), {
            'name': 'SQL Injection Protection',
            'type': 'waf_rule',
            'priority': 'high',
            'desc': 'Detect and block SQL injection attempts',
            'config': json.dumps({
                'pattern': r'(\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b|\bUNION\b|--|/\*|;)'
            })
        })
        
        # Rule 2: XSS Protection
        db.execute(text("""
            INSERT INTO firewall_rules (name, type, is_active, priority, description, rule_config, hits)
            VALUES (:name, :type, true, :priority, :desc, :config, 0)
        """), {
            'name': 'XSS Attack Protection',
            'type': 'waf_rule',
            'priority': 'high',
            'desc': 'Detect and block cross-site scripting attempts',
            'config': json.dumps({
                'pattern': r'(<script|javascript:|onerror=|onload=|<iframe)'
            })
        })
        
        # Rule 3: Block Malicious Bots
        db.execute(text("""
            INSERT INTO firewall_rules (name, type, is_active, priority, description, rule_config, hits)
            VALUES (:name, :type, true, :priority, :desc, :config, 0)
        """), {
            'name': 'Block Malicious Bots',
            'type': 'pattern_match',
            'priority': 'medium',
            'desc': 'Block requests from known malicious bots',
            'config': json.dumps({
                'blocked_user_agents': ['sqlmap', 'nikto', 'masscan', 'nmap']
            })
        })
        
        db.commit()
        logger.info("Default firewall rules created successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize firewall rules: {e}")
        db.rollback()
