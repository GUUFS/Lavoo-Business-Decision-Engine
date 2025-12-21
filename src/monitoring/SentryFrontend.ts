
// PURPOSE: Frontend Sentry initialization
// ========================================

import * as Sentry from "@sentry/react";

export function initFrontendSentry() {
    const dsn = import.meta.env.VITE_SENTRY_DSN || (window as any)._env_?.REACT_APP_SENTRY_DSN || "https://c00b037dd5c7945d120ed4c72cdba1d7@o4510550376120320.ingest.us.sentry.io/4510550802169856";

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
            environment: import.meta.env.MODE || "development",
        });
        console.log("Frontend Sentry initialized");
    } else {
        console.log("Frontend Sentry DSN not found");
    }
}
