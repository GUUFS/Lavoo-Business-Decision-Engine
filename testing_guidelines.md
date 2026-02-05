# Security Testing Guidelines

This document provides comprehensive step-by-step instructions to verify all security features implemented in the application.

> [!IMPORTANT]
> **Prerequisite**: Ensure your API server is running (`uvicorn api.main:app --reload`). 
> If you recently updated WAF rules (via `fix_waf_regex.py`), **RESTART** your server to load the new rules immediately.

## 1. SQL Injection Protection (WAF)

### Test 1.1: JSON Body Injection (Login)
**Goal**: Verify that SQL injection attempts inside a JSON payload are blocked by the WAF.

**Command**:
```bash
curl -i -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin'\'' OR '\''1'\''='\''1", "password": "password"}'
```

**Expected Result**:
- ✅ **HTTP 403 Forbidden**
- Body: `{"error": "Access denied", "message": "Request blocked by firewall"}`
- Log: `WARNING: Request blocked by firewall: rule=SQL Injection Protection`

### Test 1.2: URL Parameter Injection
**Goal**: Verify that SQL injection attempts in URL parameters are blocked.

**Command**:
```bash
# Note: %20 is used for spaces
curl -i "http://localhost:8000/api/users?search=UNION%20SELECT%20password"
```

**Expected Result**:
- ✅ **HTTP 403 Forbidden**
- Body: `{"error": "Access denied", "message": "Request blocked by firewall"}`

---

## 2. Failed Login & IP Blacklisting

### Test 2.1: Trigger Auto-Block
**Goal**: Fail login 3 times and get blocked.

**Procedure**:
1. Run this loop to fail login 5 times:
   ```bash
   for i in {1..5}; do 
     echo "Attempt $i..."
     curl -i -X POST http://localhost:8000/api/login \
       -H "Content-Type: application/json" \
       -d '{"email":"test@example.com","password":"wrongpassword"}'
     echo "\n----------------"
   done
   ```

**Expected Result**:
- Attempts 1-3: **HTTP 401 Unauthorized** (`{"detail":"Incorrect email or password"}`)
- Attempt 4+: **HTTP 403 Forbidden** (`{"detail":"IP address blacklisted. Access denied."}`)

### Test 2.2: Verify Block in Database
**Command**:
```bash
# Check raw DB content (requires psql installed, or use the python script provided below)
python -c "from db.pg_connections import SessionLocal; from sqlalchemy import text; db=SessionLocal(); print(db.execute(text(\"SELECT ip_address, reason FROM ip_blacklist WHERE is_active=true ORDER BY blocked_at DESC LIMIT 1\")).fetchall()); db.close()"
```

---

## 3. XSS Protection

### Test 3.1: Stored XSS (Profile Bio)
**Goal**: Try to save a script tag in user profile.

**Command** (Requires Login Token):
```bash
# 1. Login to get token (if not blocked)
TOKEN=$(curl -s -X POST http://localhost:8000/api/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"adminpassword"}' | grep -o '"access_token":"[^"]*"' | awk -F':' '{print $2}' | tr -d '"')

# 2. Update Profile with XSS payload
curl -i -X PUT http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"bio": "<script>alert(\"XSS\")</script>"}'
```

**Expected Result**:
- The server should validly save it OR sanitize it depending on implementation. 
- **Verification**: Open the frontend Profile page. You should see the text `<script>...` displayed as plain text, **NOT** executed as a popup. React escapes content by default.

### Test 3.2: Reflected XSS (URL)
**Goal**: Verify WAF blocks common XSS vectors in URL.

**Command**:
```bash
curl -i "http://localhost:8000/api/users?search=<script>alert(1)</script>"
```

**Expected Result**:
- ✅ **HTTP 403 Forbidden** (Blocked by WAF "Pattern Match" or "XSS" rule)

---

## 4. Rate Limiting

### Test 4.1: Flood Detection
**Goal**: Trigger the 50 req/sec limit.

**Command** (Uses Apache Bench `ab` if available, or a loop):
```bash
# Using a simple loop for portability
start=$(date +%s)
for i in {1..60}; do
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health
  echo ""
done
end=$(date +%s)
echo "Duration: $((end-start)) seconds"
```

**Expected Result**:
- First ~50 requests: **200 OK**
- Subsequent requests: **429 Too Many Requests** or **403 Forbidden** (if Flood Detector triggers)

---

## 5. Security Metrics (Dashboard)

### Test 5.1: Verify Data
**Goal**: Ensure the dashboard shows the real counts.

**Command**:
```bash
python -c "from db.pg_connections import SessionLocal; from sqlalchemy import text; db=SessionLocal(); print('Blocked IPs:', db.execute(text(\"SELECT count(*) FROM ip_blacklist WHERE is_active=true\")).scalar()); print('Failed Logins:', db.execute(text(\"SELECT count(*) FROM failed_login_attempts\")).scalar()); db.close()"
```
Compare this output with what you see on `/admin/security`.

---

## 6. Secure Headers

### Test 6.1: Inspect Headers
**Command**:
```bash
curl -I http://localhost:8000/api/health
```

**Expected Result**:
- ✅ **HTTP 200 OK** (Previously 405/404)
- Should see headers like `X-Content-Type-Options: nosniff` if configured.

---

## Troubleshooting

- **"Email has not been registered!" (404)**: 
  - This means the request **passed** the WAF and reached the login endpoint.
  - **Fix**: The WAF regex is not loaded or not matching. 
  - **Action**: Restart successful? Run `python scripts/fix_waf_regex.py` again, then **restart the API server**.

- **"dbt" or "psql" not found**:
  - Use the provided `python -c` commands instead to interact with the DB directly.


### Test 8.1: Password Hashing
**Procedure**:
1. Create new user

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

> [!NOTE]
> `SELECT * FROM pg_views` only shows the **definition** of the view (the SQL code), not the data. 
> To see the actual data, run: `SELECT * FROM security_metrics_summary;`

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

# Security Testing Guidelines

## 1. Vulnerability Scanner
To trigger a full system vulnerability scan:
```bash
curl -X POST http://localhost:8000/api/security/scan/full \
     -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## 2. Firewall Protection

### SQL Injection Protection (JSON Body)
Test if the firewall blocks SQL injection patterns in POST requests:
```bash
curl -i -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin'\'' OR '\''1'\''='\''1", "password": "password"}'
```
**Expected Response**: `403 Forbidden` with a firewall block message, OR if the firewall is in "dry" mode, a `401 Unauthorized` with `{"detail": "Invalid email or password."}`. 
> [!NOTE]
> We use a generic message to prevent hackers from knowing if an email exists in our system.

### SQL Injection Protection (URL Parameters)
Test if the firewall blocks SQL injection in query strings:
```bash
# Correct way to pass special characters in URL
curl -i -G "http://localhost:8000/api/users" --data-urlencode "search=admin' OR '1'='1"
```
**Expected Response**: `403 Forbidden`. If you get `401 Unauthorized`, it means the firewall allowed the request through to the authentication layer, which is a bypass!

### Malicious Bot Blocking
Test if the firewall blocks known malicious user agents:
```bash
curl -i -H "User-Agent: sqlmap" http://localhost:8000/api/health
```

### Flood Detection (Rate Limiting)
Our flood detection is now set to **10 requests per second**.

#### For Bash (Ubuntu Default):
```bash
START_TIME=$(date +%s)
for i in {1..20}; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
  echo "Request $i: HTTP $CODE"
  if [ "$CODE" == "403" ] || [ "$CODE" == "429" ]; then
    echo "Rate limit triggered at request $i!"
    break
  fi
done
```

#### For Fish Shell:
```fish
set start (date +%s)
for i in (seq 1 20)
  set code (curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
  echo "Request $i: HTTP $code"
  if test "$code" = "403" -o "$code" = "429"
    echo "Rate limit triggered at request $i!"
    break
  end
end
```
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

## 11. Email Integration

### Prerequisites
Ensure your `.env` file has the following variables set to ensure functionality and visibility:
- `BREVO_API_KEY`: Your Brevo API Key
- `BREVO_FROM_EMAIL`: Sender email
- `BREVO_FROM_NAME`: Sender name
- `FRONTEND_URL`: URL of the frontend (e.g., http://localhost:3000)
- `DEBUG=true`: **Important** for seeing detailed console logs

### Test 11.1: Verification Endpoints
The email service exposes direct endpoints for testing email templates without completing a full user flow.

**1. Welcome Email**
```bash
curl -X POST http://localhost:8000/api/emails/welcome \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "your_email@example.com",
    "user_name": "Test User"
  }'
```

**2. Payout Email**
```bash
curl -X POST http://localhost:8000/api/emails/payout \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "your_email@example.com",
    "user_name": "Test User",
    "amount": 150.00,
    "commission_from": "Referral Bonus",
    "transaction_id": "TXN-123456"
  }'
```

**3. Payment Success Email**
```bash
curl -X POST http://localhost:8000/api/emails/payment-success \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "your_email@example.com",
    "user_name": "Test User",
    "amount": 29.99,
    "plan_name": "Pro Plan",
    "next_billing_date": "February 22, 2026"
  }'
```

**Verify**: 
- Check your inbox for the emails.
- Check the terminal where `uvicorn` is running. You should see `INFO: Email sent successfully. Message ID: ...` (or `DEBUG` logs if `DEBUG=true`).
