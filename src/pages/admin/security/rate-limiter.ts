
// PURPOSE: Rate limiting to prevent brute force attacks
import type { Request, Response } from 'express';
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import { createClient } from 'redis';
import { Pool } from 'pg';
import logger from '@/monitoring/logger';
import { alertManager } from '@/monitoring/alerts';

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// Create Redis client for distributed rate limiting (optional)
let redisClient: any = null;
if (process.env.REDIS_URL) {
    redisClient = createClient({ url: process.env.REDIS_URL });
    redisClient.connect().catch((err: Error) => {
        logger.error('Redis connection failed', { err });
    });
}

// General API rate limiter - 100 requests per 15 minutes
export const apiLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    message: 'Too many requests, please try again later',
    standardHeaders: true,
    legacyHeaders: false,
    store: redisClient ? new RedisStore({
        client: redisClient,
        prefix: 'rl:api:'
    }) : undefined,
    handler: (req: Request, res: Response) => {
        logger.warn('Rate limit exceeded', {
            ip: req.ip,
            path: req.path,
            method: req.method
        });

        alertManager.createAlert(
            'Security',
            `Rate limit exceeded from IP: ${req.ip}`,
            'warning',
            { ip: req.ip, path: req.path }
        );

        res.status(429).json({
            error: 'Too many requests',
            message: 'Please try again later',
            retryAfter: 900 // 15 minutes in seconds
        });
    }
});

// Strict rate limiter for auth endpoints - 5 attempts per 15 minutes
export const authLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 5,
    skipSuccessfulRequests: true, // Don't count successful logins
    message: 'Too many login attempts, please try again later',
    standardHeaders: true,
    legacyHeaders: false,
    store: redisClient ? new RedisStore({
        client: redisClient,
        prefix: 'rl:auth:'
    }) : undefined,
    handler: (req: Request, res: Response) => {
        logger.error('Auth rate limit exceeded - possible brute force', {
            ip: req.ip,
            path: req.path,
            body: { email: req.body.email }
        });

        // Create high-priority alert
        alertManager.createAlert(
            'Security',
            `Brute force attack detected from IP: ${req.ip}`,
            'error',
            { ip: req.ip, email: req.body.email }
        );

        // Log to security events table
        pool.query(
            `INSERT INTO security_events (type, severity, ip_address, description, status)
                VALUES ($1, $2, $3, $4, $5)`,
            ['brute_force', 'high', req.ip, 'Multiple failed login attempts', 'blocked']
        ).catch((err: Error) => logger.error('Failed to log security event', { err }));

        res.status(429).json({
            error: 'Too many login attempts',
            message: 'Your account has been temporarily locked. Please try again in 15 minutes.',
            retryAfter: 900
        });
    }
});

// Admin panel rate limiter - 50 requests per 15 minutes
export const adminLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 50,
    message: 'Too many admin requests',
    store: redisClient ? new RedisStore({
        client: redisClient,
        prefix: 'rl:admin:'
    }) : undefined
});