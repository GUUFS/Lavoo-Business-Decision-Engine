# Testing Guide for Security, Reviews & Admin System Enhancements

## Overview
This guide provides step-by-step testing procedures for all changes made to the security metrics, IP blacklist, reviews display system, and admin header functionality.

## Prerequisites

### Environment Setup
```bash
# Ensure database is running
psql $DATABASE_URL -c "SELECT 1;"

# Ensure backend server is running
cd /home/emeka/ai-business-analyst
python backend.py

# Ensure frontend is running (in another terminal)
cd /home/emeka/ai-business-analyst
npm run dev
```

### Test Data Setup
```sql
-- Create test admin user if not exists
INSERT INTO users (name, email, password, is_admin, is_active)
VALUES ('Test Admin', 'admin@test.com', '$argon2id$...', true, true)
ON CONFLICT (email) DO NOTHING;

-- Create test reviews
INSERT INTO reviews (user_id, business_name, review_title, rating, review_text, status)
VALUES 
  (1, 'TechCorp', 'Amazing Service!', 5, 'This platform transformed our business operations.', 'published'),
  (1, 'StartupHub', 'Great Experience', 4, 'Very helpful for our startup journey.', 'published'),
  (2, 'Enterprise Inc', 'Highly Recommended', 5, 'Best AI business analyst tool we have used.', 'published')
ON CONFLICT DO NOTHING;
```

## Test Suite

### 1. Security Metrics Accuracy Test (UPDATED)

**Objective**: Verify that security metrics show correct TOTAL counts from database (All Time)

**Steps**:
1. Open browser and navigate to `http://localhost:3000/admin/security`
2. Login with admin credentials
3. Note the current values for:
   - Failed Logins (Total All Time)
   - Blocked Attacks (Total All Time)
   - Suspicious Activity
   - Active Firewall Rules

4. Open a new incognito window
5. Navigate to `http://localhost:3000/login`
6. Attempt login with WRONG password 3 times using email: `test@example.com`
   - Password: `wrongpassword123`
   
7. Return to admin security page and click "Refresh" button

**Expected Results**:
- ✅ "Failed Logins" count increased by 3
- ✅ "Blocked Attacks" count increased by 1 (IP auto-blocked)
- ✅ "Suspicious Activity" may increase if severity is high
- ✅ Recent Security Events section shows 3 new "failed_login" events
- ✅ Recent Security Events section shows 1 new "ip_blocked" event

**Database Verification**:
```sql
-- Check failed login attempts (Total Count equals Metric)
SELECT COUNT(*) FROM failed_login_attempts;

-- Check IP blacklist (Total Count equals Metric)
SELECT COUNT(*) FROM ip_blacklist WHERE is_active = true;
```

---

### 2. Public IP Detection & Behavior Analysis Test

**Objective**: Verify firewall correctly identifies Public IPs and blocks flooding.

**Steps (Using cURL)**:
1. **Public IP Test**: Send a request with a spoofed X-Forwarded-For header representing a public IP.
   ```bash
   curl -H "X-Forwarded-For: 203.0.113.195" http://localhost:8000/api/login
   ```
   *Verify in logs/database that request is logged from `203.0.113.195` (Public), NOT `127.0.0.1` (Private).*

2. **Behavior Analysis (Flood)**: Send 60 requests in < 1 second.
   ```bash
   for i in {1..60}; do curl -s -o /dev/null http://localhost:8000/api/login & done
   ```
   *Expected Result*: Requests after the 50th should receive `403 Forbidden` or `Block` response due to "Suspicious behavior detected".

**Expected Database State**:
- ✅ 3 records in `failed_login_attempts` with email 'test@example.com'
- ✅ 1 record in `ip_blacklist` with `is_active = true` and `email = 'test@example.com'`
- ✅ 4 records in `security_events` (3 failed_login + 1 ip_blocked)

---

### 2. IP Blacklist Email Tracking Test

**Objective**: Verify that IP blacklist records include the email address

**Steps**:
1. Follow steps from Test 1 to trigger IP blacklist
2. Query the database:

```sql
SELECT ip_address, email, reason, blocked_at, expires_at
FROM ip_blacklist
WHERE is_active = true
ORDER BY blocked_at DESC
LIMIT 1;
```

**Expected Results**:
- ✅ `email` column contains 'test@example.com'
- ✅ `reason` is 'Brute force protection: Multiple failed logins'
- ✅ `expires_at` is 24 hours from `blocked_at`
- ✅ `is_active` is `true`

---

### 3. IP Unblock API Test

**Objective**: Verify that the unblock-ip endpoint works correctly

**Steps**:
1. Get the blocked IP from Test 1:
```sql
SELECT ip_address FROM ip_blacklist WHERE is_active = true LIMIT 1;
```

2. Get admin JWT token:
   - Login to admin panel
   - Open browser DevTools → Application → Local Storage
   - Copy the `token` value

3. Test the unblock endpoint:
```bash
# Replace with actual values
IP_TO_UNBLOCK="192.168.1.100"
ADMIN_TOKEN="your_jwt_token_here"

curl -X POST http://localhost:8000/api/security/unblock-ip \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"ip\": \"$IP_TO_UNBLOCK\"}"
```

**Expected Results**:
- ✅ API returns: `{"message": "IP unblocked successfully"}`
- ✅ Database shows `is_active = false` for that IP:
```sql
SELECT is_active FROM ip_blacklist WHERE ip_address = '192.168.1.100';
```

4. Verify user can now login:
   - Try logging in from the previously blocked IP
   - ✅ Login should succeed (if credentials are correct)

---

### 4. Admin Name Display Test

**Objective**: Verify admin first name displays correctly across all pages

**Steps**:
1. Login as admin user with name "John Doe"
2. Navigate to `/admin/security`
3. Check header - should show "John" (first name only)
4. Navigate to `/admin/reviews`
5. Check header - should show "John" (first name only)
6. Navigate to `/admin/dashboard`
7. Check header - should show "John" (first name only)

**Expected Results**:
- ✅ All admin pages show first name only ("John")
- ✅ Avatar shows initials ("JD")
- ✅ No hardcoded "Lavoo" or "Admin User" text
- ✅ Loading state shows "Loading..." briefly on first load

**Edge Cases**:
- Single name: "Madonna" → displays "Madonna"
- Three names: "John Paul Smith" → displays "John"
- Empty name: fallback to "Admin"

---

### 5. Reviews Display Management Test

**Objective**: Verify admin can add/remove reviews from homepage display

**Steps**:
1. Login as admin
2. Navigate to `/admin/reviews`
3. Click "All Reviews" tab
4. Find a 5-star review
5. Click the "Display" button
6. ✅ Alert: "Review added to homepage display!"

7. Click "Displayed Reviews" tab
8. ✅ The review should appear in this list

9. Click "Hide" button on that review
10. ✅ Alert: "Review removed from homepage display!"
11. ✅ Review disappears from the list

**Database Verification**:
```sql
-- Check displayed reviews
SELECT dr.id, dr.review_id, dr.display_order, r.review_title
FROM displayed_reviews dr
JOIN reviews r ON dr.review_id = r.id
ORDER BY dr.display_order;
```

**Expected Results**:
- ✅ After clicking "Display": 1 record in `displayed_reviews` table
- ✅ After clicking "Hide": 0 records in `displayed_reviews` table

---

### 6. Homepage Dynamic Reviews Test

**Objective**: Verify homepage shows only admin-selected reviews

**Steps**:
1. Open homepage in incognito: `http://localhost:3000/`
2. Scroll to "What Our Customers Say" section
3. ✅ Should see message: "No reviews yet" or empty carousel

4. As admin, add 3 reviews to display:
   - Navigate to `/admin/reviews`
   - Click "Display" on 3 different 5-star reviews

5. Refresh homepage
6. ✅ Carousel should show exactly 3 reviews
7. ✅ Reviews should match those selected by admin
8. ✅ Carousel navigation arrows should work

9. As admin, hide 1 review
10. Refresh homepage
11. ✅ Carousel should now show 2 reviews

**API Test**:
```bash
# Public endpoint (no auth required)
curl http://localhost:8000/api/reviews/displayed
```

**Expected Response**:
```json
[
  {
    "id": 1,
    "user_name": "John Doe",
    "business_name": "TechCorp",
    "review_title": "Amazing Service!",
    "rating": 5,
    "review_text": "This platform transformed our business...",
    "date_submitted": "2025-12-30T10:00:00",
    "verified": false
  },
  ...
]
```

---

### 7. Cache Warming Script Test

**Objective**: Verify cache warming script populates Redis correctly

**Steps**:
1. Ensure Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

2. Clear Redis cache:
```bash
redis-cli FLUSHDB
```

3. Run cache warming script:
```bash
cd /home/emeka/ai-business-analyst
python scripts/cache_warming.py
```

**Expected Output**:
```
============================================================
🚀 Starting Cache Warming Process
============================================================
⏰ Started at: 2025-12-30 16:30:00
✅ Connected to Redis
✅ Connected to PostgreSQL

📦 Warming displayed reviews cache...
   ✓ Cached 3 displayed reviews
   ✓ Cache key: displayed_reviews:all
   ✓ TTL: 300s

🔒 Warming security metrics cache...
   ✓ Cached security metrics
   ✓ Threat Level: Low
   ✓ Failed Logins (24h): 3
   ✓ Blocked Attacks (24h): 1

⚙️  Warming system settings cache...
   ✓ Cached system settings
   ✓ Monthly: $29.00
   ✓ Yearly: $290.00

============================================================
✅ Cache warming completed successfully!
============================================================
```

4. Verify cache in Redis:
```bash
# Check displayed reviews cache
redis-cli GET "displayed_reviews:all"

# Check security metrics cache
redis-cli GET "security:metrics"

# Check TTL
redis-cli TTL "displayed_reviews:all"
# Should return ~300 (5 minutes)
```

---

### 8. Production Load Test

**Objective**: Verify system handles concurrent requests

**Prerequisites**:
```bash
# Install Apache Bench if not available
sudo apt-get install apache-bench
```

**Test 1: Displayed Reviews Endpoint**
```bash
ab -n 1000 -c 50 http://localhost:8000/api/reviews/displayed
```

**Expected Results**:
- ✅ 0% failed requests
- ✅ 95th percentile response time < 200ms
- ✅ Requests per second > 100

### Test 9.2: WAF Rule - SQL Injection Detection
**Procedure**:
1. Open a terminal and run this EXACT command to simulate a SQL injection attack via JSON body:
   ```bash
   curl -X POST http://localhost:8000/api/login \
     -H "Content-Type: application/json" \
     -d '{"email": "admin'\'' OR '\''1'\''='\''1", "password": "hacker"}'
   ```

**Expected Result**:
- ✅ **HTTP 403 Forbidden** (This confirms the Firewall blocked it)
- ✅ Response Body: `{"error": "Access denied", "message": "Request blocked by firewall"}`
- ✅ Check Database: The event will appear in "Recent Security Events" as a `firewall_block`.

2. To verify header/URL based injection matching:
   ```bash
   curl "http://localhost:8000/api/users?search=UNION SELECT password"
   ```
- ✅ Expected: **HTTP 403 Forbidden**

**Why this works**:
The firewall now inspects the JSON body of your request. It sees the pattern `' OR '1'='1` and blocks the request *before* it even reaches the Login system.
```bash
# Get admin token first
ADMIN_TOKEN="your_jwt_token"

ab -n 1000 -c 50 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/security/metrics
```

**Expected Results**:
- ✅ 0% failed requests
- ✅ 95th percentile response time < 300ms
- ✅ No database connection errors

---

## Regression Testing

### Critical Paths to Verify

1. **User Login Flow**
   - ✅ Successful login with correct credentials
   - ✅ Failed login with wrong password
   - ✅ Account lockout after 3 failed attempts
   - ✅ Password reset functionality still works

2. **Admin Dashboard**
   - ✅ All metrics load correctly
   - ✅ Charts and graphs display
   - ✅ Navigation between pages works

3. **Reviews System**
   - ✅ Users can still submit reviews
   - ✅ Admin can approve/reject reviews
   - ✅ Conversation system works
   - ✅ Email notifications sent (if configured)

4. **Homepage**
   - ✅ All sections load
   - ✅ Navigation works
   - ✅ Signup/Login buttons functional
   - ✅ Mobile responsive

---

## Troubleshooting Common Issues

### Issue: Security metrics show 0

**Diagnosis**:
```sql
-- Check if view exists
SELECT * FROM security_metrics_summary LIMIT 1;

-- Check if data exists
SELECT COUNT(*) FROM security_events;
SELECT COUNT(*) FROM failed_login_attempts;
```

**Solution**: If view returns no data, ensure security events are being created

### Issue: IP not getting blacklisted

**Diagnosis**:
```sql
-- Check if trigger exists
SELECT tgname FROM pg_trigger WHERE tgname = 'trigger_auto_block';

-- Check trigger function
SELECT prosrc FROM pg_proc WHERE proname = 'auto_block_attacking_ip';
```

**Solution**: Re-run `db/security_setup.sql` if trigger is missing

### Issue: Reviews not appearing on homepage

**Diagnosis**:
```bash
# Check API endpoint
curl http://localhost:8000/api/reviews/displayed

# Check database
SELECT COUNT(*) FROM displayed_reviews;
```

**Solution**: Ensure reviews are marked as 'published' and added to display

### Issue: Admin name not showing

**Diagnosis**:
- Check browser console for errors
- Verify `/api/me` endpoint returns user data
- Check if `getAuthToken()` returns valid token

**Solution**: Clear browser cache and localStorage, re-login

---

## Performance Benchmarks

### Expected Response Times (95th percentile)

| Endpoint | Without Cache | With Cache |
|----------|--------------|------------|
| `/api/reviews/displayed` | 150ms | 20ms |
| `/api/security/metrics` | 200ms | 30ms |
| `/api/admin/reviews` | 180ms | N/A |
| `/api/admin/reviews/displayed` | 160ms | N/A |

### Database Query Performance

```sql
-- Should complete in < 50ms
EXPLAIN ANALYZE
SELECT * FROM security_metrics_summary;

-- Should complete in < 30ms
EXPLAIN ANALYZE
SELECT * FROM displayed_reviews dr
JOIN reviews r ON dr.review_id = r.id
ORDER BY dr.display_order;
```

---

## Sign-off Checklist

Before deploying to production, verify:

- [ ] All 8 test suites pass
- [ ] No console errors in browser
- [ ] No errors in backend logs
- [ ] Database migration completed successfully
- [ ] Cache warming script runs without errors
- [ ] Load tests show acceptable performance
- [ ] Regression tests pass
- [ ] IP unblock documentation reviewed by team
- [ ] Admin users trained on new features
- [ ] Rollback plan documented and tested

---

## Support & Escalation

If tests fail:
1. Check application logs: `tail -f logs/app.log`
2. Check database logs: `tail -f /var/log/postgresql/postgresql.log`
3. Review this testing guide for troubleshooting steps
4. Contact development team with:
   - Test that failed
   - Error messages
   - Database state (relevant SQL queries)
   - Browser console logs (if frontend issue)
