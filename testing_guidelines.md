
# Security Testing Guidelines

This document provides comprehensive step-by-step instructions to verify all security features implemented in the application.

## 1. Failed Login Attempts & IP Blacklisting (3-Attempt Threshold)

### Test 1.1: Record Failed Login Attempts
**Procedure**:
1. Clear existing records: `DELETE FROM failed_login_attempts; DELETE FROM security_events WHERE type='failed_login';`
2. Attempt login with valid email but wrong password
3. Check database: `SELECT * FROM failed_login_attempts ORDER BY created_at DESC LIMIT 5;`

**Expected Result**:
- Entry in `failed_login_attempts` table with email, IP address, and user agent
- Entry in `security_events` table with type='failed_login', severity='medium'
- HTTP 401 Unauthorized response

### Test 1.2: Automatic IP Blacklisting After 3 Failed Attempts
**Procedure**:
1. Clear blacklist: `DELETE FROM ip_blacklist;`
2. Make 3 failed login attempts with the same email from the same IP
3. Check blacklist: `SELECT * FROM ip_blacklist WHERE is_active=true;`
4. Verify email is recorded: Check the `email` column in the blacklist entry

**Expected Result**:
- After 3rd attempt, IP is automatically added to `ip_blacklist`
- `email` column contains the email from failed login attempts
- `reason` is "Brute force protection: Multiple failed logins"
- `expires_at` is set to 24 hours from now
- `security_events` table has an 'ip_blocked' event

### Test 1.3: Block Login from Blacklisted IP
**Procedure**:
1. After IP is blacklisted (from Test 1.2), attempt to login again
2. Try with both correct and incorrect passwords

**Expected Result**:
- HTTP 403 Forbidden response
- Error message: "IP address blacklisted. Access denied."
- Login blocked BEFORE password verification
- No new entries in `failed_login_attempts` (blocked at IP check)

### Test 1.4: Security Dashboard Updates
**Procedure**:
1. Navigate to `/admin/security`
2. Check "Blocked Attacks" metric
3. View "Recent Security Events" tab

**Expected Result**:
- "Blocked Attacks" shows count of active blacklisted IPs
- Recent events show failed_login and ip_blocked events
- Email address displayed in blacklist table (if frontend updated)

## 2. SQL Injection Protection

### Test 2.1: Detection
**Procedure**:
1. Send POST request to `/api/login` with payload:
   ```json
   {"email": "admin' OR '1'='1", "password": "anything"}
   ```
2. Check application logs

**Expected Result**:
- Request is logged with "Potential SQL injection detected" warning
- No SQL injection occurs (ORM prevents it)
- HTTP 401 or 404 response (user not found)

### Test 2.2: Blocking
**Procedure**:
1. Try various SQL injection patterns in different endpoints:
   - `'; DROP TABLE users; --`
   - `1' UNION SELECT * FROM users --`
   - `admin'--`

**Expected Result**:
- All attempts fail safely
- Database remains intact
- Security events logged

## 3. XSS Protection

### Test 3.1: Script Injection in User Input
**Procedure**:
1. Update user profile with bio: `<script>alert('XSS')</script>`
2. View profile page
3. Check database: `SELECT bio FROM users WHERE id=<user_id>;`

**Expected Result**:
- Script tags are sanitized or escaped
- No JavaScript execution in browser
- Database stores sanitized version

### Test 3.2: XSS in URL Parameters
**Procedure**:
1. Navigate to: `/dashboard?search=<img src=x onerror=alert('XSS')>`
2. Check browser console

**Expected Result**:
- No alert popup
- Input is escaped/sanitized

## 4. Session Management & JWT Authentication

### Test 4.1: Unauthorized Access
**Procedure**:
1. Clear all cookies and localStorage
2. Attempt to access `/api/security/metrics`

**Expected Result**:
- HTTP 401 Unauthorized or 403 Forbidden
- Redirected to login page

### Test 4.2: Token Expiration
**Procedure**:
1. Log in and copy the JWT token
2. Wait for token to expire (check JWT_EXPIRATION in .env)
3. Attempt to access protected endpoint

**Expected Result**:
- HTTP 401 Unauthorized
- Error: "Token expired"

### Test 4.3: Session Invalidation
**Procedure**:
1. Log in and note session ID
2. Manually delete session: `DELETE FROM user_sessions WHERE id=<session_id>;`
3. Refresh dashboard

**Expected Result**:
- Redirected to login
- Session no longer valid

## 5. Rate Limiting

### Test 5.1: Login Rate Limit
**Procedure**:
1. Send 11+ login requests within 1 minute using curl or Postman:
   ```bash
   for i in {1..15}; do curl -X POST http://localhost:8000/api/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@test.com","password":"wrong"}'; done
   ```

**Expected Result**:
- First 10 requests: HTTP 401 (wrong password)
- 11th+ requests: HTTP 429 Too Many Requests
- Error: "Rate limit exceeded"

### Test 5.2: API Rate Limit
**Procedure**:
1. Send 100+ requests to any API endpoint within 1 minute

**Expected Result**:
- HTTP 429 after threshold
- Rate limit resets after time window

## 6. CSRF Token Validation

### Test 6.1: Missing CSRF Token
**Procedure**:
1. Send POST request without CSRF token (if implemented)
2. Check response

**Expected Result**:
- HTTP 403 Forbidden (if CSRF protection enabled)
- Error: "CSRF token missing or invalid"

## 7. Secure Headers

### Test 7.1: Security Headers Present
**Procedure**:
1. Make any request and inspect response headers:
   ```bash
   curl -I http://localhost:8000/api/health
   ```

**Expected Headers**:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000` (if HTTPS)
- `Content-Security-Policy: ...`

## 8. Database Security

### Test 8.1: Password Hashing
**Procedure**:
1. Create new user
2. Check database: `SELECT password FROM users WHERE email='newuser@test.com';`

**Expected Result**:
- Password is hashed (bcrypt, 60+ characters)
- Not stored in plaintext

### Test 8.2: SQL Views and Triggers
**Procedure**:
1. Check views exist:
   ```sql
   SELECT * FROM pg_views WHERE schemaname='public' AND viewname LIKE 'security%';
   ```
2. Check trigger exists:
   ```sql
   SELECT * FROM pg_trigger WHERE tgname='trigger_auto_block';
   ```

**Expected Result**:
- Views: `security_metrics_summary`, `recent_security_events`, `active_user_sessions`, `top_attacking_ips`
- Trigger: `trigger_auto_block` on `security_events` table

## 9. Firewall Rules

### Test 9.1: Initialize Default Firewall Rules
**Procedure**:
1. Call API endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/security/firewall/initialize \
     -H "Authorization: Bearer <admin_token>"
   ```
2. Check database:
   ```sql
   SELECT * FROM firewall_rules WHERE is_active=true;
   ```

**Expected Result**:
- Default rules created: SQL Injection Protection, XSS Attack Protection, Block Malicious Bots
- All rules have `is_active=true`
- Response: `{"message": "Firewall rules initialized successfully"}`

### Test 9.2: WAF Rule - SQL Injection Detection
**Procedure**:
1. Ensure SQL Injection Protection rule is active
2. Send request with SQL injection pattern:
   ```bash
   curl "http://localhost:8000/api/users?search=admin' OR '1'='1"
   ```

**Expected Result**:
- HTTP 403 Forbidden
- Response: `{"error": "Access denied", "message": "Request blocked by firewall"}`
- Entry in `security_events` table with type='firewall_block'
- Rule hit counter incremented

### Test 9.3: Pattern Match - Block Malicious Bots
**Procedure**:
1. Send request with malicious user agent:
   ```bash
   curl -H "User-Agent: sqlmap/1.0" http://localhost:8000/api/health
   ```

**Expected Result**:
- HTTP 403 Forbidden
- Request blocked by "Block Malicious Bots" rule
- Security event logged

### Test 9.4: Create Custom Firewall Rule
**Procedure**:
1. Create IP block rule:
   ```bash
   curl -X POST http://localhost:8000/api/security/firewall/rules \
     -H "Authorization: Bearer <admin_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Block Test IP",
       "type": "ip_block",
       "priority": "high",
       "description": "Block specific test IP",
       "rule_config": {"blocked_ips": ["192.168.1.100"]}
     }'
   ```
2. Verify rule created in database

**Expected Result**:
- Rule created with ID returned
- Rule appears in `firewall_rules` table
- Rule is automatically loaded and active

### Test 9.5: Get Firewall Rules
**Procedure**:
1. Call API endpoint:
   ```bash
   curl http://localhost:8000/api/security/firewall/rules \
     -H "Authorization: Bearer <admin_token>"
   ```

**Expected Result**:
- List of all firewall rules with details
- Includes hit counts for each rule

## 10. Vulnerability Scanner

### Test 10.1: Run Full Vulnerability Scan
**Procedure**:
1. Call API endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/security/scan/full \
     -H "Authorization: Bearer <admin_token>"
   ```
2. Check scan results:
   ```sql
   SELECT * FROM vulnerability_scans ORDER BY started_at DESC LIMIT 1;
   ```

**Expected Result**:
- Scan completes successfully
- Response includes: `status`, `scan_id`, `findings`, `severity`, `duration`
- Scan record in database with status='completed'
- Findings include checks for: database security, configuration security, Python dependencies

### Test 10.2: Database Security Scan
**Procedure**:
1. Call API endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/security/scan/database \
     -H "Authorization: Bearer <admin_token>"
   ```

**Expected Result**:
- Scan checks for:
  - Weak password hashes (< 60 characters)
  - Users without roles
  - Stale sessions (> 30 days old)
- Findings categorized by severity (critical, high, medium, low)
- Recommendations provided for each finding

### Test 10.3: Configuration Security Check
**Procedure**:
1. Run full scan (includes configuration check)
2. Review findings for:
   - JWT secret strength
   - Default/weak secrets
   - Database URL security

**Expected Result**:
- Critical finding if JWT_SECRET < 32 characters
- Critical finding if using default secrets
- Medium finding if database credentials in plaintext

### Test 10.4: Get Scan History
**Procedure**:
1. Call API endpoint:
   ```bash
   curl http://localhost:8000/api/security/scans \
     -H "Authorization: Bearer <admin_token>"
   ```

**Expected Result**:
- List of recent vulnerability scans (last 20)
- Each scan shows: type, status, severity, findings count, duration, timestamps
- Scans ordered by most recent first

### Test 10.5: Verify Scan Findings
**Procedure**:
1. Run a scan
2. Query scan results:
   ```sql
   SELECT scan_results FROM vulnerability_scans WHERE id = <scan_id>;
   ```
3. Parse JSON results

**Expected Result**:
- Detailed findings in JSON format
- Each finding includes: severity, type, description, recommendation, location
- Findings are actionable and specific

---

## Critical Security Checklist

- [ ] JWT secrets generated and stored in `.env` (minimum 32 characters)
- [ ] SSL/TLS enabled in production (HTTPS)
- [ ] All admin routes protected with `admin_required` dependency
- [ ] Database user has minimum required permissions
- [ ] Failed login threshold set to 3 attempts
- [ ] IP blacklist check occurs BEFORE password verification
- [ ] Email addresses tracked in `ip_blacklist` table
- [ ] Security events logged for all suspicious activity
- [ ] Rate limiting active on all endpoints
- [ ] XSS and SQL injection protection verified
- [ ] Secure headers configured
- [ ] Session management working correctly
- [ ] Backend server restarted to apply trigger changes

## Verification Commands

```sql
-- Check failed login attempts
SELECT * FROM failed_login_attempts ORDER BY created_at DESC LIMIT 10;

-- Check IP blacklist with emails
SELECT ip_address, email, reason, is_active, blocked_at, expires_at 
FROM ip_blacklist WHERE is_active=true;

-- Check security events
SELECT type, severity, ip_address, description, created_at 
FROM security_events ORDER BY created_at DESC LIMIT 20;

-- Check active sessions
SELECT * FROM active_user_sessions;

-- Check security metrics
SELECT * FROM security_metrics_summary;
```
