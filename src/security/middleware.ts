
// PURPOSE: Global security middleware for protection
import type { Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import cors from 'cors';
//@ts-ignore
const corsMiddleware = cors as any;
import { Pool } from 'pg';
import logger from '../monitoring/logger';
import { alertManager } from '../monitoring/alerts';
import DOMPurify from 'isomorphic-dompurify';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// 1. Helmet Configuration
export const helmetConfig = helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'", "'unsafe-inline'"],
            styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "cdn.jsdelivr.net"],
            imgSrc: ["'self'", "data:", "https:"],
            connectSrc: ["'self'", "https://api.stripe.com"],
            fontSrc: ["'self'", "https://fonts.gstatic.com", "cdn.jsdelivr.net"],
            objectSrc: ["'none'"],
            mediaSrc: ["'self'"],
            frameSrc: ["'self'", "https://checkout.stripe.com"],
        },
    },
});

// 2. CORS Configuration
export const corsConfig = corsMiddleware({
    origin: process.env.FRONTEND_URL || '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true,
});

// 3. IP Blacklist Middleware
let blacklistedIPs: Set<string> = new Set();

export const loadBlacklistedIPs = async () => {
    try {
        const result = await pool.query('SELECT ip_address FROM ip_blacklist WHERE expires_at > NOW() OR expires_at IS NULL');
        blacklistedIPs = new Set(result.rows.map(row => row.ip_address));
        logger.info('IP Blacklist loaded', { count: blacklistedIPs.size });
    } catch (error) {
        logger.error('Failed to load IP blacklist', { error });
    }
};

export const ipBlacklist = (req: Request, _res: Response, next: NextFunction) => {
    const clientIP = req.ip || req.socket.remoteAddress;
    if (clientIP && blacklistedIPs.has(clientIP)) {
        logger.warn('Blocked blacklisted IP attempt', { ip: clientIP });
        return _res.status(403).json({ error: 'Access denied: IP blocked' });
    }
    next();
};

// 4. SQL Injection Detector
export const sqlInjectionDetector = (req: Request, _res: Response, next: NextFunction) => {
    const sqlKeywords = /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|EXEC|UNION)\b)|(['"])/i;
    const values = Object.values(req.body).concat(Object.values(req.query));

    for (const value of values) {
        if (typeof value === 'string' && sqlKeywords.test(value)) {
            logger.warn('Potential SQL injection detected', {
                ip: req.ip,
                path: req.path,
                payload: value
            });
            alertManager.sendAlert('SQL Injection Attempt', `Potential SQL injection from ${req.ip}`, 'high');
            // return _res.status(403).json({ error: 'Security violation detected' });
        }
    }
    next();
};

// 5. XSS Detector & Sanitizer
export const xssDetector = (req: Request, _res: Response, next: NextFunction) => {
    if (req.body) {
        for (const key in req.body) {
            if (typeof req.body[key] === 'string') {
                const original = req.body[key];
                const sanitized = DOMPurify.sanitize(original);
                if (original !== sanitized) {
                    logger.warn('XSS attempt sanitized', {
                        key,
                        original,
                        sanitized
                    });
                    req.body[key] = sanitized;
                }
            }
        }
    }
    next();
};

// 6. Security Logger
export const securityLogger = (req: Request, _res: Response, next: NextFunction) => {
    // Log security-sensitive events
    if (req.path.includes('auth') || req.path.includes('security')) {
        logger.info('Security-sensitive path accessed', {
            path: req.path,
            method: req.method,
            ip: req.ip
        });
    }
    next();
};
