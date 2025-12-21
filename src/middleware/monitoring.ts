
// PURPOSE: Request tracking and error handling middleware
// ========================================

import type { Request, Response, NextFunction } from 'express';
import logger from '../monitoring/logger';

export const requestTracker = (req: Request, res: Response, next: NextFunction) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        logger.info(`${req.method} ${req.url}`, {
            method: req.method,
            url: req.url,
            status: res.statusCode,
            duration: `${duration}ms`,
            ip: req.ip,
            userAgent: req.get('user-agent')
        });
    });
    next();
};

export const errorHandler = (err: any, req: Request, res: Response, _next: NextFunction) => {
    logger.error('Unhandled Exception', {
        error: err.message,
        stack: err.stack,
        url: req.url,
        method: req.method,
    });

    res.status(err.status || 500).json({
        error: process.env.NODE_ENV === 'production' ? 'Internal Server Error' : err.message
    });
};
