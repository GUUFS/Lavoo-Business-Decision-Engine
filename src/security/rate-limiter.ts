
// PURPOSE: Rate limiting for API protection
import rateLimit from 'express-rate-limit';
import logger from '../monitoring/logger';

// General API rate limiter
export const apiLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    standardHeaders: true,
    legacyHeaders: false,
    message: {
        error: 'Too many requests, please try again later.'
    },
    handler: (req: any, res: any, _next: any, options: any) => {
        logger.warn('Rate limit exceeded', { ip: req.ip, path: req.path });
        res.status(options.statusCode).send(options.message);
    }
});

// Authentication rate limiter (stricter)
export const authLimiter = rateLimit({
    windowMs: 60 * 60 * 1000, // 1 hour
    max: 10, // Limit each IP to 10 login/register attempts per hour
    standardHeaders: true,
    legacyHeaders: false,
    message: {
        error: 'Too many authentication attempts, please try again in an hour.'
    },
    handler: (req: any, res: any, _next: any, options: any) => {
        logger.warn('Auth rate limit exceeded', { ip: req.ip, email: req.body.email });
        res.status(options.statusCode).send(options.message);
    }
});
