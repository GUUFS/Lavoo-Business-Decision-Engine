
-- PURPOSE: SQL Views, Functions, and Triggers for Real-time Security Monitoring
-- ============================================================================

-- 1. VIEW: Recent security events with user details
CREATE OR REPLACE VIEW recent_security_events AS
SELECT 
    se.id,
    se.type,
    se.severity,
    se.description,
    se.ip_address,
    se.created_at,
    u.name as user_name,
    u.email as user_email
FROM security_events se
LEFT JOIN users u ON (se.user_id::text)::integer = u.id
ORDER BY se.created_at DESC
LIMIT 100;

-- 2. VIEW: Security metrics summary for the last 24 hours
CREATE OR REPLACE VIEW security_metrics_summary AS
SELECT
    (SELECT COUNT(*) FROM security_events WHERE created_at > NOW() - INTERVAL '24 hours') as total_events_24h,
    (SELECT COUNT(*) FROM security_events WHERE severity = 'high' AND created_at > NOW() - INTERVAL '24 hours') as high_severity_events_24h,
    (SELECT COUNT(*) FROM security_events WHERE type IN ('blocked_attack', 'ip_blocked') AND created_at > NOW() - INTERVAL '24 hours') as blocked_attacks_24h,
    (SELECT COUNT(*) FROM failed_login_attempts WHERE created_at > NOW() - INTERVAL '24 hours') as failed_logins_24h,
    (SELECT COUNT(*) FROM ip_blacklist WHERE is_active = true) as active_blacklisted_ips,
    (SELECT COUNT(*) FROM firewall_rules WHERE is_active = true) as active_firewall_rules;

-- 3. VIEW: Active User Sessions with IP and Last Activity
CREATE OR REPLACE VIEW active_user_sessions AS
SELECT 
    us.id,
    us.user_id,
    u.email,
    us.ip_address,
    us.user_agent,
    us.last_activity,
    us.created_at
FROM user_sessions us
JOIN users u ON (us.user_id::text)::integer = u.id
WHERE us.is_active = true AND us.last_activity > NOW() - INTERVAL '24 hours'
ORDER BY us.last_activity DESC;

-- 4. VIEW: Top attacking IPs based on failed logins and security events
CREATE OR REPLACE VIEW top_attacking_ips AS
SELECT 
    ip_address,
    COUNT(*) as total_events,
    MAX(created_at) as last_seen,
    JSONB_AGG(DISTINCT type) as event_types
FROM security_events
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY ip_address
ORDER BY total_events DESC
LIMIT 10;

-- 5. FUNCTION: Automatically block IP after multiple failed logins
CREATE OR REPLACE FUNCTION auto_block_attacking_ip()
RETURNS TRIGGER AS $$
DECLARE
    failed_count INTEGER;
    attempt_email VARCHAR(255);
BEGIN
    -- Only check for failed_login events
    IF NEW.type = 'failed_login' THEN
        -- Count failed attempts from this IP in the last 15 minutes
        SELECT COUNT(*) INTO failed_count
        FROM security_events
        WHERE ip_address = NEW.ip_address 
          AND type = 'failed_login'
          AND created_at > NOW() - INTERVAL '15 minutes';
          
        -- If more than 5 failed attempts, block the IP
        IF failed_count >= 5 THEN
            -- Get the email from the most recent failed login attempt
            SELECT email INTO attempt_email
            FROM failed_login_attempts
            WHERE ip_address = NEW.ip_address
            ORDER BY created_at DESC
            LIMIT 1;
            
            INSERT INTO ip_blacklist (ip_address, reason, email, expires_at)
            VALUES (NEW.ip_address, 'Brute force protection: Multiple failed logins', attempt_email, NULL)
            ON CONFLICT (ip_address) DO UPDATE 
            SET expires_at = NULL, is_active = true, email = EXCLUDED.email;
            
            -- Log the block event
            INSERT INTO security_events (type, severity, description, ip_address, status)
            VALUES ('ip_blocked', 'high', 'IP automatically blocked due to brute force', NEW.ip_address, 'logged');
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 6. TRIGGER: Auto-block trigger on security_events
DROP TRIGGER IF EXISTS trigger_auto_block ON security_events;
CREATE TRIGGER trigger_auto_block
AFTER INSERT ON security_events
FOR EACH ROW
EXECUTE FUNCTION auto_block_attacking_ip();

-- 7. FUNCTION: Cleanup old sessions and security logs
CREATE OR REPLACE FUNCTION cleanup_security_data()
RETURNS void AS $$
BEGIN
    -- Deactivate sessions older than 7 days
    UPDATE user_sessions SET is_active = false WHERE last_activity < NOW() - INTERVAL '7 days';
    
    -- Delete failed login attempts older than 30 days
    DELETE FROM failed_login_attempts WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Delete security events older than 90 days (keeping the audit trail slim)
    DELETE FROM security_events WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;
