// PURPOSE: Input validation to prevent injection attacks
// ========================================

import { body, param, query, validationResult } from 'express-validator';
import type { Request, Response, NextFunction } from 'express';
import DOMPurify from 'isomorphic-dompurify';
import logger from '@/monitoring/logger';

// Sanitize HTML to prevent XSS
export function sanitizeHTML(dirty: string): string {
    return DOMPurify.sanitize(dirty, {
        ALLOWED_TAGS: [], // No HTML tags allowed
        ALLOWED_ATTR: []
    });
}

// Email validator
export const validateEmail = body('email')
    .isEmail()
    .normalizeEmail()
    .withMessage('Invalid email address')
    .customSanitizer((value: string) => sanitizeHTML(value));

// Password validator
export const validatePassword = body('password')
    .isLength({ min: 8 })
    .withMessage('Password must be at least 8 characters')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
    .withMessage('Password must contain uppercase, lowercase, number, and special character');

// UUID validator
export const validateUUID = (field: string) =>
    param(field)
        .isUUID()
        .withMessage(`${field} must be a valid UUID`);

// SQL Injection prevention - validate query params
export const validateSearchQuery = query('search')
    .optional()
    .trim()
    .escape()
    .isLength({ max: 100 })
    .withMessage('Search query too long')
    .customSanitizer((value: string) => sanitizeHTML(value));

// Validation error handler
export function handleValidationErrors(req: Request, res: Response, next: NextFunction) {
    const errors = validationResult(req);

    if (!errors.isEmpty()) {
        logger.warn('Validation failed', {
            errors: errors.array(),
            path: req.path,
            ip: req.ip
        });

        return res.status(400).json({
            error: 'Validation failed',
            details: errors.array()
        });
    }

    next();
}

// Login validation
export const validateLogin = [
    validateEmail,
    body('password').notEmpty().withMessage('Password is required'),
    handleValidationErrors
];

// Registration validation
export const validateRegistration = [
    validateEmail,
    validatePassword,
    body('name')
        .trim()
        .isLength({ min: 2, max: 100 })
        .withMessage('Name must be between 2 and 100 characters')
        .customSanitizer((value: string) => sanitizeHTML(value)),
    handleValidationErrors
];