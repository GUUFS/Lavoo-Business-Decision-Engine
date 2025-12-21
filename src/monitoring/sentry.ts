
// PURPOSE: Sentry initialization and configuration
// ========================================

import * as Sentry from '@sentry/node';
import type { Express } from 'express';

export function initSentry(_app: Express) {
    const dsn = process.env.BACKEND_SENTRY_DSN || process.env.SENTRY_DSN;
    if (dsn) {
        Sentry.init({
            dsn: dsn,
            tracesSampleRate: 1.0,
            environment: process.env.NODE_ENV || 'development',
            // Note: v8 automatically instruments many things via default integrations
        });
        console.log('Sentry initialized');
    } else {
        console.log('Sentry DSN not found, skipping initialization');
    }
}
