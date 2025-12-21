import { Router } from 'express';
import { authenticateToken } from '../auth';

const router = Router();

// Protect all routes in this file
router.use(authenticateToken);

export default router;

