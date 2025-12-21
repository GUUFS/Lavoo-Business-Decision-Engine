// PURPOSE: Authentication routes (login, register, refresh token)
import type { Request, Response } from 'express';
import { Router } from 'express';
import { Pool } from 'pg';
import {
    hashPassword,
    comparePassword,
    generateAccessToken,
    generateRefreshToken,
    verifyRefreshToken,
    createSession,
    revokeSession,
    authenticateToken
} from '../auth';
import { authLimiter } from '../rate-limiter';
import { validateLogin, validateRegistration } from '../validators';
import logger from '@/monitoring/logger';

const router = Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// Register
router.post('/register', authLimiter, validateRegistration, async (req: Request, res: Response) => {
    try {
        const { email, password, name } = req.body;

        // Check if user exists
        const existingUser = await pool.query('SELECT id FROM users WHERE email = $1', [email]);
        if (existingUser.rows.length > 0) {
            return res.status(400).json({ error: 'Email already registered' });
        }

        // Hash password
        const passwordHash = await hashPassword(password);

        // Create user
        const result = await pool.query(
            `INSERT INTO users (email, password_hash, name, role, created_at)
       VALUES ($1, $2, $3, $4, NOW())
       RETURNING id, email, name, role`,
            [email, passwordHash, name, 'user']
        );

        const user = result.rows[0];

        logger.info('User registered', { userId: user.id, email });

        res.status(201).json({
            message: 'Registration successful',
            user: { id: user.id, email: user.email, name: user.name }
        });
    } catch (error) {
        logger.error('Registration failed', { error });
        res.status(500).json({ error: 'Registration failed' });
    }
});

// Login
router.post('/login', authLimiter, validateLogin, async (req: Request, res: Response) => {
    try {
        const { email, password } = req.body;
        const ipAddress = req.ip || req.socket.remoteAddress || 'unknown';
        const userAgent = req.get('user-agent') || 'unknown';

        // Get user
        const userResult = await pool.query(
            'SELECT id, email, password_hash, name, role FROM users WHERE email = $1',
            [email]
        );

        if (userResult.rows.length === 0) {
            // Log failed attempt
            await pool.query(
                'INSERT INTO failed_login_attempts (email, ip_address, user_agent) VALUES ($1, $2, $3)',
                [email, ipAddress, userAgent]
            );

            return res.status(401).json({ error: 'Invalid credentials' });
        }

        const user = userResult.rows[0];

        // Verify password
        const validPassword = await comparePassword(password, user.password_hash);
        if (!validPassword) {
            // Log failed attempt
            await pool.query(
                'INSERT INTO failed_login_attempts (email, ip_address, user_agent) VALUES ($1, $2, $3)',
                [email, ipAddress, userAgent]
            );

            await pool.query(
                `INSERT INTO security_events (type, severity, user_id, ip_address, description, status)
         VALUES ($1, $2, $3, $4, $5, $6)`,
                ['failed_login', 'medium', user.id, ipAddress, 'Invalid password attempt', 'logged']
            );

            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Create session
        const sessionId = await createSession(user.id, ipAddress, userAgent);

        // Generate tokens
        const payload = {
            userId: user.id,
            email: user.email,
            role: user.role,
            sessionId
        };

        const accessToken = generateAccessToken(payload);
        const refreshToken = generateRefreshToken(payload);

        // Log successful login
        await pool.query(
            `INSERT INTO security_events (type, severity, user_id, ip_address, description, status)
       VALUES ($1, $2, $3, $4, $5, $6)`,
            ['login', 'low', user.id, ipAddress, 'Successful login', 'completed']
        );

        logger.info('User logged in', { userId: user.id, email: user.email });

        res.json({
            message: 'Login successful',
            accessToken,
            refreshToken,
            user: {
                id: user.id,
                email: user.email,
                name: user.name,
                role: user.role
            }
        });
    } catch (error) {
        logger.error('Login failed', { error });
        res.status(500).json({ error: 'Login failed' });
    }
});

// Refresh token
router.post('/refresh', async (req: Request, res: Response) => {
    try {
        const { refreshToken } = req.body;

        if (!refreshToken) {
            return res.status(401).json({ error: 'Refresh token required' });
        }

        const payload = verifyRefreshToken(refreshToken);
        if (!payload) {
            return res.status(403).json({ error: 'Invalid refresh token' });
        }

        // Verify session still active
        const sessionCheck = await pool.query(
            'SELECT * FROM user_sessions WHERE id = $1 AND is_active = true',
            [payload.sessionId]
        );

        if (sessionCheck.rows.length === 0) {
            return res.status(403).json({ error: 'Session expired' });
        }

        // Generate new access token
        const newAccessToken = generateAccessToken(payload);

        res.json({ accessToken: newAccessToken });
    } catch (error) {
        logger.error('Token refresh failed', { error });
        res.status(500).json({ error: 'Token refresh failed' });
    }
});

// Logout
router.post('/logout', authenticateToken, async (req: Request, res: Response) => {
    try {
        if (req.user?.sessionId) {
            await revokeSession(req.user.sessionId);
        }

        logger.info('User logged out', { userId: req.user?.userId });

        res.json({ message: 'Logout successful' });
    } catch (error) {
        logger.error('Logout failed', { error });
        res.status(500).json({ error: 'Logout failed' });
    }
});

export default router;
