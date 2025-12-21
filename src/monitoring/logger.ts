
// PURPOSE: Centralized logging for the security module
// ========================================

type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogContext {
    [key: string]: any;
}

const logger = {
    log(level: LogLevel, message: string, context: LogContext = {}) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            level: level.toUpperCase(),
            message,
            ...context
        };

        if (process.env.NODE_ENV === 'development') {
            const color = level === 'error' ? '\x1b[31m' : level === 'warn' ? '\x1b[33m' : '\x1b[32m';
            console.log(`${color}[${timestamp}] ${level.toUpperCase()}: ${message}\x1b[0m`, context);
        } else {
            // In production, we'd send this to a logging service or structured stdout
            console.log(JSON.stringify(logEntry));
        }
    },

    info(message: string, context?: LogContext) {
        this.log('info', message, context);
    },

    warn(message: string, context?: LogContext) {
        this.log('warn', message, context);
    },

    error(message: string, context?: LogContext) {
        this.log('error', message, context);
    },

    debug(message: string, context?: LogContext) {
        this.log('debug', message, context);
    }
};

export default logger;
