
// PURPOSE: Manage security alerts and notifications
// ========================================

import logger from './logger';

export const alertManager = {
    async sendAlert(title: string, message: string, severity: 'low' | 'medium' | 'high' | 'critical') {
        const alert = {
            timestamp: new Date().toISOString(),
            title,
            message,
            severity,
        };

        logger.warn(`SECURITY ALERT [${severity.toUpperCase()}]: ${title}`, { message });

        if (severity === 'high' || severity === 'critical') {
            this.triggerEmergencyNotification(alert);
        }
    },

    async createAlert(category: string, message: string, severity: 'info' | 'warning' | 'error', context?: any) {
        const levelMap: Record<string, 'low' | 'medium' | 'high' | 'critical'> = {
            'info': 'low',
            'warning': 'medium',
            'error': 'high'
        };

        await this.sendAlert(category, message, levelMap[severity] || 'medium');
        if (context) {
            logger.debug(`Alert context`, context);
        }
    },

    async triggerEmergencyNotification(alert: any) {
        console.log('EMERGENCY NOTIFICATION TRIGGERED:', JSON.stringify(alert));
    }
};
