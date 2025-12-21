// PURPOSE: Secure Express app with all security middleware
// ========================================

import express from 'express';
import type { Request, Response } from 'express';
import * as Sentry from '@sentry/node';
import { initSentry } from '@/monitoring/sentry';
import { requestTracker, errorHandler } from '@/middleware/monitoring';
import {
  helmetConfig,
  corsConfig,
  ipBlacklist,
  sqlInjectionDetector,
  xssDetector,
  securityLogger,
  loadBlacklistedIPs
} from '@/security/middleware';
import { apiLimiter } from '@/security/rate-limiter';

// Routes
import healthRoutes from '@/routes/health';
import monitoringRoutes from '@/routes/monitoring';
import authRoutes from '@/pages/admin/security/routes/auth';
import securityRoutes from '@/pages/admin/security/routes/security';
// Your existing routes
// import userRoutes from './routes/users';
// import alertRoutes from './routes/alerts';

import logger from '@/monitoring/logger';

const app = express();

logger.info('Initializing secure Express application...');

// ========================================
// 1. SECURITY HEADERS (FIRST)
// ========================================
app.use(helmetConfig);

// ========================================
// 2. CORS CONFIGURATION
// ========================================
app.use(corsConfig);

// ========================================
// 3. SENTRY INITIALIZATION
// ========================================
const SENTRY_DSN = process.env.BACKEND_SENTRY_DSN || process.env.SENTRY_DSN;
if (SENTRY_DSN) {
  initSentry(app);
}

// ========================================
// 4. BODY PARSERS (with size limits)
// ========================================
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// ========================================
// 5. SECURITY MIDDLEWARE
// ========================================
app.use(securityLogger);
app.use(ipBlacklist);
app.use(sqlInjectionDetector);
app.use(xssDetector);

// Load blacklisted IPs on startup
loadBlacklistedIPs();

// ========================================
// 6. MONITORING
// ========================================
app.use(requestTracker);

// ========================================
// 7. PUBLIC ROUTES (no auth required)
// ========================================

// Health checks (Railway needs this)
app.use('/api', healthRoutes);

// Authentication routes (with rate limiting built-in)
app.use('/api/auth', authRoutes);

// ========================================
// 8. RATE LIMITED ROUTES
// ========================================
app.use('/api', apiLimiter);

// ========================================
// 9. PROTECTED ROUTES (require authentication)
// ========================================

// Monitoring routes
app.use('/api/monitoring', monitoringRoutes);

// Security dashboard (admin only)
app.use('/api/security', securityRoutes);

// YOUR EXISTING ROUTES
import usersRoutes from '@/pages/admin/security/routes/users';
app.use('/api/users', usersRoutes);
// ... etc

// ========================================
// 10. ERROR HANDLERS (MUST BE LAST)
// ========================================

// Sentry error handler
if (SENTRY_DSN) {
  Sentry.setupExpressErrorHandler(app);
}

// Custom error handler
app.use(errorHandler);

// 404 handler
app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: 'Route not found' });
});

export default app;


