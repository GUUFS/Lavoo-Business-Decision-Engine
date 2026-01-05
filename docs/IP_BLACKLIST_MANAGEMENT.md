# IP Blacklist Management Guide

## Overview
The system automatically blacklists IP addresses after 3 failed login attempts within 15 minutes. This guide explains how to unblock IP addresses when needed.

## Automatic Blacklisting Process

### How It Works
1. User attempts login with wrong password
2. System records attempt in `failed_login_attempts` table
3. System creates security event in `security_events` table
4. Database trigger `auto_block_attacking_ip()` checks failed attempt count
5. If ≥3 attempts in 15 minutes, IP is added to `ip_blacklist` table
6. IP is blocked for 24 hours by default

### What Gets Recorded
- **IP Address**: The attacking IP
- **Email**: Email address used in failed login attempts
- **Reason**: "Brute force protection: Multiple failed logins"
- **Expires At**: 24 hours from block time
- **Is Active**: true (actively blocking)

## Checking Blacklisted IPs

### Via Database Query
```sql
-- View all active blacklisted IPs
SELECT 
    ip_address,
    email,
    reason,
    blocked_at,
    expires_at,
    is_active
FROM ip_blacklist
WHERE is_active = true
ORDER BY blocked_at DESC;
```

### Via Admin Dashboard
1. Navigate to `/admin/security`
2. Scroll to "Recent Security Events" section
3. Look for events with type `ip_blocked`
4. Check the IP address and associated email

## Unblocking an IP Address

### Method 1: Using the API Endpoint (Recommended)

**Endpoint**: `POST /api/security/unblock-ip`

**Authentication**: Requires admin token

**Request Body**:
```json
{
  "ip": "192.168.1.100"
}
```

**Example using cURL**:
```bash
# Replace YOUR_ADMIN_TOKEN with actual admin JWT token
# Replace 192.168.1.100 with the IP to unblock

curl -X POST http://localhost:8000/api/security/unblock-ip \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{"ip": "192.168.1.100"}'
```

**Example using Python**:
```python
import requests

API_BASE = "http://localhost:8000/api"
ADMIN_TOKEN = "your_admin_jwt_token_here"

response = requests.post(
    f"{API_BASE}/security/unblock-ip",
    headers={
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"ip": "192.168.1.100"}
)

print(response.json())
# Expected: {"message": "IP unblocked successfully"}
```

**Example using JavaScript (Frontend)**:
```javascript
const API_BASE = 'http://localhost:8000/api';
const adminToken = localStorage.getItem('token');

async function unblockIP(ipAddress) {
  try {
    const response = await fetch(`${API_BASE}/security/unblock-ip`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ip: ipAddress })
    });
    
    const data = await response.json();
    console.log(data.message); // "IP unblocked successfully"
    return true;
  } catch (error) {
    console.error('Failed to unblock IP:', error);
    return false;
  }
}

// Usage
unblockIP('192.168.1.100');
```

### Method 2: Direct Database Update

**Use Case**: When API is unavailable or for bulk operations

```sql
-- Unblock a specific IP
UPDATE ip_blacklist
SET is_active = false
WHERE ip_address = '192.168.1.100';

-- Unblock multiple IPs
UPDATE ip_blacklist
SET is_active = false
WHERE ip_address IN ('192.168.1.100', '192.168.1.101', '192.168.1.102');

-- Unblock all IPs for a specific email
UPDATE ip_blacklist
SET is_active = false
WHERE email = 'user@example.com';

-- Unblock all expired blocks
UPDATE ip_blacklist
SET is_active = false
WHERE expires_at < NOW() AND is_active = true;
```

### Method 3: Admin UI (Future Enhancement)

**Note**: This feature is planned for future implementation.

A dedicated admin interface will allow:
- Viewing all blacklisted IPs in a table
- One-click unblock button for each IP
- Bulk unblock operations
- Whitelist management

## Common Scenarios

### Scenario 1: Legitimate User Locked Out

**Problem**: A legitimate user forgot their password and got blocked.

**Solution**:
1. Verify the user's identity through alternative means
2. Use the API endpoint to unblock their IP
3. Send them a password reset link
4. Consider adding their IP to a whitelist (future feature)

**Example**:
```bash
# Unblock the user's IP
curl -X POST http://localhost:8000/api/security/unblock-ip \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip": "203.0.113.45"}'
```

### Scenario 2: Office/Corporate IP Blocked

**Problem**: Multiple employees share an IP and one person's failed attempts blocked everyone.

**Solution**:
1. Unblock the corporate IP immediately
2. Identify the employee with login issues
3. Help them reset their password
4. Consider implementing IP whitelisting for corporate networks

### Scenario 3: Testing Environment

**Problem**: During testing, developers frequently trigger the auto-block.

**Solution**:
1. Add development IPs to whitelist (requires code modification)
2. Or, temporarily disable auto-blocking in development:

```sql
-- Disable the trigger in development only
DROP TRIGGER IF EXISTS trigger_auto_block ON security_events;

-- Re-enable when needed
CREATE TRIGGER trigger_auto_block
AFTER INSERT ON security_events
FOR EACH ROW
EXECUTE FUNCTION auto_block_attacking_ip();
```

## Monitoring and Alerts

### Check Recent Blocks
```sql
-- IPs blocked in the last 24 hours
SELECT 
    ip_address,
    email,
    blocked_at,
    expires_at
FROM ip_blacklist
WHERE blocked_at > NOW() - INTERVAL '24 hours'
ORDER BY blocked_at DESC;
```

### Check Failed Login Patterns
```sql
-- Failed login attempts by IP in last hour
SELECT 
    ip_address,
    email,
    COUNT(*) as attempt_count,
    MAX(created_at) as last_attempt
FROM failed_login_attempts
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip_address, email
HAVING COUNT(*) >= 2
ORDER BY attempt_count DESC;
```

### Security Event Log
```sql
-- Recent security events related to IP blocking
SELECT 
    type,
    severity,
    description,
    ip_address,
    created_at
FROM security_events
WHERE type IN ('failed_login', 'ip_blocked')
ORDER BY created_at DESC
LIMIT 50;
```

## Best Practices

1. **Verify Before Unblocking**: Always check the security events to understand why an IP was blocked
2. **Document Unblocks**: Keep a log of manually unblocked IPs and reasons
3. **Monitor Patterns**: If the same IP gets blocked repeatedly, investigate further
4. **Communicate**: Inform users about the security measure and provide support contact
5. **Regular Cleanup**: Periodically remove old inactive blocks to keep the table clean

## Troubleshooting

### IP Still Blocked After Unblock

**Check**:
```sql
SELECT * FROM ip_blacklist WHERE ip_address = '192.168.1.100';
```

**Solution**: Ensure `is_active` is set to `false`

### Unblock API Returns 403 Forbidden

**Problem**: User doesn't have admin privileges

**Solution**: Verify the JWT token belongs to an admin user:
```sql
SELECT email, is_admin FROM users WHERE id = <user_id_from_token>;
```

### IP Gets Re-blocked Immediately

**Problem**: User continues to use wrong password

**Solution**: 
1. Reset the user's password
2. Clear failed login attempts:
```sql
DELETE FROM failed_login_attempts 
WHERE ip_address = '192.168.1.100' 
AND created_at > NOW() - INTERVAL '1 hour';
```

## Security Considerations

- **Log All Unblocks**: Every unblock action should be logged for audit purposes
- **Limit Unblock Permissions**: Only trusted admins should have unblock access
- **Monitor Abuse**: If an admin frequently unblocks the same IP, investigate
- **Rate Limiting**: Consider implementing rate limiting on the unblock endpoint itself

## Related Files

- **Trigger Function**: `db/security_setup.sql` (lines 60-96)
- **API Endpoint**: `api/routes/security.py` (lines 180-198)
- **Database Models**: `db/pg_models.py` (IPBlacklist class)
- **Login Handler**: `api/routes/login.py` (lines 304-315)

## Support

For issues or questions about IP blacklist management:
1. Check the security events log
2. Review this documentation
3. Contact the development team
4. Check application logs for detailed error messages
