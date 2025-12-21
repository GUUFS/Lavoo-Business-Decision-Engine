// PURPOSE: Security dashboard API (get events, metrics, etc.)
import type { Request, Response } from 'express';
import { Router } from 'express';
import { Pool } from 'pg';
import { authenticateToken, requireAdmin } from '../auth';
import logger from '@/monitoring/logger';

const router = Router();
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// All security routes require admin authentication
router.use(authenticateToken, requireAdmin);

// Get security metrics summary
router.get('/metrics', async (_req: Request, res: Response) => {
    try {
        const metricsResult = await pool.query('SELECT * FROM security_metrics_summary');
        const metrics = metricsResult.rows[0];

        // Get threat level
        let threatLevel = 'Low';
        if (metrics.high_severity_events_24h > 10) {
            threatLevel = 'High';
        } else if (metrics.high_severity_events_24h > 5) {
            threatLevel = 'Medium';
        }

        // Get last security scan
        const lastScan = await pool.query(
            'SELECT completed_at FROM vulnerability_scans ORDER BY completed_at DESC LIMIT 1'
        );

        res.json({
            threatLevel,
            blockedAttacks: metrics.blocked_attacks_24h || 0,
            failedLogins: metrics.failed_logins_24h || 0,
            suspiciousActivity: metrics.high_severity_events_24h || 0,
            activeFirewallRules: metrics.active_firewall_rules || 0,
            lastSecurityScan: lastScan.rows[0]?.completed_at || 'Never'
        });
    } catch (error) {
        logger.error('Failed to get security metrics', { error });
        res.status(500).json({ error: 'Failed to retrieve security metrics' });
    }
});

// Get security events
router.get('/events', async (req: Request, res: Response) => {
    try {
        const limit = parseInt(req.query.limit as string) || 50;
        const offset = parseInt(req.query.offset as string) || 0;

        const result = await pool.query(
            `SELECT * FROM security_events 
                ORDER BY created_at DESC 
                LIMIT $1 OFFSET $2`,
            [limit, offset]
        );

        const countResult = await pool.query('SELECT COUNT(*) FROM security_events');
        const total = parseInt(countResult.rows[0].count);

        res.json({
            events: result.rows,
            total,
            limit,
            offset
        });
    } catch (error) {
        logger.error('Failed to get security events', { error });
        res.status(500).json({ error: 'Failed to retrieve security events' });
    }
});

// Get firewall rules
router.get('/firewall-rules', async (_req: Request, res: Response) => {
    try {
        const result = await pool.query(
            'SELECT * FROM firewall_rules ORDER BY priority DESC, created_at DESC'
        );

        res.json({ rules: result.rows });
    } catch (error) {
        logger.error('Failed to get firewall rules', { error });
        res.status(500).json({ error: 'Failed to retrieve firewall rules' });
    }
});

// Get vulnerability scans
router.get('/vulnerability-scans', async (_req: Request, res: Response) => {
    try {
        const result = await pool.query(
            'SELECT * FROM vulnerability_scans ORDER BY started_at DESC LIMIT 10'
        );

        res.json({ scans: result.rows });
    } catch (error) {
        logger.error('Failed to get vulnerability scans', { error });
        res.status(500).json({ error: 'Failed to retrieve vulnerability scans' });
    }
});

// Get top attacking IPs
router.get('/top-attacking-ips', async (_req: Request, res: Response) => {
    try {
        const result = await pool.query('SELECT * FROM top_attacking_ips');

        res.json({ ips: result.rows });
    } catch (error) {
        logger.error('Failed to get top attacking IPs', { error });
        res.status(500).json({ error: 'Failed to retrieve attacking IPs' });
    }
});

// Block an IP
router.post('/block-ip', async (req: Request, res: Response) => {
    try {
        const { ip, reason } = req.body;

        if (!ip || !reason) {
            return res.status(400).json({ error: 'IP and reason required' });
        }

        await pool.query(
            `INSERT INTO ip_blacklist (ip_address, reason, blocked_by)
       VALUES ($1, $2, $3)`,
            [ip, reason, req.user!.userId]
        );

        // Log audit
        await pool.query(
            `INSERT INTO audit_log (user_id, action, resource_type, resource_id, ip_address)
       VALUES ($1, $2, $3, $4, $5)`,
            [req.user!.userId, 'block_ip', 'ip_blacklist', ip, req.ip]
        );

        logger.info('IP blocked', { ip, reason, blockedBy: req.user!.userId });

        res.json({ message: 'IP blocked successfully' });
    } catch (error) {
        logger.error('Failed to block IP', { error });
        res.status(500).json({ error: 'Failed to block IP' });
    }
});

// Unblock an IP
router.post('/unblock-ip', async (req: Request, res: Response) => {
    try {
        const { ip } = req.body;

        await pool.query(
            'UPDATE ip_blacklist SET is_active = false WHERE ip_address = $1',
            [ip]
        );

        logger.info('IP unblocked', { ip, unblockedBy: req.user!.userId });

        res.json({ message: 'IP unblocked successfully' });
    } catch (error) {
        logger.error('Failed to unblock IP', { error });
        res.status(500).json({ error: 'Failed to unblock IP' });
    }
});

export default router;