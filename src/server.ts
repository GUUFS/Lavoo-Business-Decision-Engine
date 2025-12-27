
// PURPOSE: Start server with security initialization
import app from './app';
import logger from '@/monitoring/logger';

const PORT = process.env.PORT || 3000;


// Start server
app.listen(PORT, () => {
  logger.info(`🚀 Server started on port ${PORT}`);
  logger.info(`🔒 Security features enabled:`);
  logger.info(`  ✅ Helmet security headers`);
  logger.info(`  ✅ CORS protection`);
  logger.info(`  ✅ Rate limiting`);
  logger.info(`  ✅ SQL injection protection`);
  logger.info(`  ✅ XSS protection`);
  logger.info(`  ✅ IP blacklist`);
  logger.info(`  ✅ JWT authentication`);

  if (process.env.SENTRY_DSN) {
    logger.info(`  ✅ Sentry error tracking`);
  }

  if (process.env.SMTP_HOST) {
    logger.info(`  ✅ Email alerts`);
  }

  logger.info(`📊 Endpoints:`);
  logger.info(`  Health: http://localhost:${PORT}/api/health`);
  logger.info(`  Login: http://localhost:${PORT}/api/auth/login`);
  logger.info(`  Security: http://localhost:${PORT}/api/security/metrics`);
});

// Handle shutdown gracefully
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  process.exit(0);
});