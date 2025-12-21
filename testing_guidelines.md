
# Security Testing Guidelines

This document provides step-by-step instructions to verify the security features implemented in the application.

## 1. JWT Authentication & Session Management
- **Test**: Attempt to access `/api/security/metrics` without an `Authorization` header.
- **Expected Result**: `401 Unauthorized` or `403 Forbidden`.
- **Test**: Log in, then manually delete the `user_sessions` entry from the database. Refresh the dashboard.
- **Expected Result**: Should be redirected to login as the session is no longer valid.

## 2. Rate Limiting
- **Test**: Use a tool like Postman or `curl` to send 11+ login requests within 1 minute.
- **Expected Result**: The server should return `429 Too Many Requests`.
- **Alert**: Check the `security_events` table or the Security Dashboard for a "brute_force" event.

## 3. SQL Injection Protection
- **Test**: Send a request to any authenticated endpoint with a payload containing `' OR '1'='1`.
  - Example: `POST /api/auth/register` with `{"email": "test' OR '1'='1", ...}`
- **Expected Result**: The server should log a "Potential SQL injection detected" warning and trigger a medium/high severity alert.

## 4. XSS Protection
- **Test**: Profile update with `<script>alert('XSS')</script>` in the Bio field.
- **Expected Result**: The input should be sanitized before being saved or displayed. Check the database to see if the script tags were removed.

## 5. IP Blacklisting
- **Test**: Manually add your IP address to the `ip_blacklist` table in the database.
- **Expected Result**: Any subsequent requests should return `403 Access denied: IP blocked`.
- **Verification**: Ensure the "IP Blacklist" count on the Security Dashboard updates.

## 6. Real-time Security Dashboard
- **Verification**: Open the Admin Security page (`/admin/security`).
- **Test**: Perform a failed login attempt from a different browser or tab.
- **Expected Result**: The "Recent Security Events" list should update within 30 seconds (or upon manual refresh).

## 7. Automatic Threat Detection
- **Test**: Trigger 5 failed login attempts for the same IP within 15 minutes.
- **Expected Result**: The IP should be automatically added to the `ip_blacklist` table, and an "ip_blocked" event should appear in the logs.

---

### Critical Security Checklist
- [ ] JWT secrets generated and stored in `.env`.
- [ ] SSL/TLS enabled in production (HTTPS).
- [ ] All sensitive routes wrapped with `authenticateToken` and `requireAdmin`.
- [ ] Database user has minimum required permissions (principle of least privilege).
- [ ] Redis is secured (if used for rate limiting).
