
// PURPOSE: Frontend Sentry initialization
// ========================================

import * as Sentry from "@sentry/react";

export function initFrontendSentry() {
    // Only initialize Sentry in production to avoid 403 errors
    const environment = import.meta.env.MODE || "development";

    if (environment === "development") {
        console.log("Sentry disabled in development mode");
        return;
    }

    const dsn = import.meta.env.VITE_SENTRY_DSN || (window as any)._env_?.REACT_APP_SENTRY_DSN;

    if (dsn) {
        Sentry.init({
            dsn: dsn,
            integrations: [
                Sentry.browserTracingIntegration(),
                Sentry.replayIntegration(),
            ],
            // Performance Monitoring
            tracesSampleRate: 1.0,
            // Session Replay
            replaysSessionSampleRate: 0.1,
            replaysOnErrorSampleRate: 1.0,
            environment: environment,
        });
        console.log("Frontend Sentry initialized");
    } else {
        console.log("Frontend Sentry DSN not found");
    }
}
