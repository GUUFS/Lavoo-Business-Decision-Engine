
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import type { Request, Response, NextFunction } from 'express';
import { Pool } from 'pg';
import { randomBytes } from 'crypto';
import logger from '@/monitoring/logger';

declare global {
    namespace Express {
        interface Request {
            user?: JWTPayload;
        }
    }
}

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const JWT_SECRET = process.env.JWT_SECRET || 'change-this-to-random-secret';
const JWT_REFRESH_SECRET = process.env.JWT_REFRESH_SECRET || 'change-refresh-secret';
const JWT_EXPIRES_IN = '15m'; // Access token expires in 15 minutes
const REFRESH_TOKEN_EXPIRES_IN = '7d'; // Refresh token expires in 7 days

interface JWTPayload {
    userId: string;
    email: string;
    role: string;
    sessionId: string;
}

// Generate access token
export function generateAccessToken(payload: JWTPayload): string {
    return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });
}

// Generate refresh token
export function generateRefreshToken(payload: JWTPayload): string {
    return jwt.sign(payload, JWT_REFRESH_SECRET, { expiresIn: REFRESH_TOKEN_EXPIRES_IN });
}

// Verify access token
export function verifyAccessToken(token: string): JWTPayload | null {
    try {
        return jwt.verify(token, JWT_SECRET) as JWTPayload;
    } catch (_error) {
        return null;
    }
}

// Verify refresh token
export function verifyRefreshToken(token: string): JWTPayload | null {
    try {
        return jwt.verify(token, JWT_REFRESH_SECRET) as JWTPayload;
    } catch (_error) {
        return null;
    }
}

// Hash password
export async function hashPassword(password: string): Promise<string> {
    return bcrypt.hash(password, 12);
}

// Compare password
export async function comparePassword(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
}

// Authentication middleware
export async function authenticateToken(req: Request, res: Response, next: NextFunction) {
    try {
        const authHeader = req.headers['authorization'];
        const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

        if (!token) {
            return res.status(401).json({ error: 'Access token required' });
        }

        const payload = verifyAccessToken(token);
        if (!payload) {
            return res.status(403).json({ error: 'Invalid or expired token' });
        }

        // Check if session is still valid
        const sessionCheck = await pool.query(
            'SELECT * FROM user_sessions WHERE id = $1 AND user_id = $2 AND is_active = true',
            [payload.sessionId, payload.userId]
        );

        if (sessionCheck.rows.length === 0) {
            return res.status(403).json({ error: 'Session expired or invalid' });
        }

        // Update last activity
        await pool.query(
            'UPDATE user_sessions SET last_activity = NOW() WHERE id = $1',
            [payload.sessionId]
        );

        // Add user info to request
        req.user = payload;
        next();
    } catch (error) {
        logger.error('Authentication error', { error });
        res.status(500).json({ error: 'Authentication failed' });
    }
}

// Admin-only middleware
export function requireAdmin(req: Request, res: Response, next: NextFunction) {
    if (!req.user || req.user.role !== 'admin') {
        logger.warn('Unauthorized admin access attempt', {
            userId: req.user?.userId,
            ip: req.ip
        });
        return res.status(403).json({ error: 'Admin access required' });
    }
    next();
}

// Create session
export async function createSession(userId: string, ipAddress: string, userAgent: string): Promise<string> {
    const sessionId = randomBytes(32).toString('hex');

    await pool.query(
        `INSERT INTO user_sessions (id, user_id, ip_address, user_agent, is_active, last_activity)
     VALUES ($1, $2, $3, $4, true, NOW())`,
        [sessionId, userId, ipAddress, userAgent]
    );

    return sessionId;
}

// Revoke session
export async function revokeSession(sessionId: string): Promise<void> {
    await pool.query(
        'UPDATE user_sessions SET is_active = false, revoked_at = NOW() WHERE id = $1',
        [sessionId]
    );
}

// Revoke all user sessions (useful when password changes)
export async function revokeAllUserSessions(userId: string): Promise<void> {
    await pool.query(
        'UPDATE user_sessions SET is_active = false, revoked_at = NOW() WHERE user_id = $1',
        [userId]
    );
}