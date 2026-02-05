
import axios, { type AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class EmailService {
    private client: AxiosInstance;

    constructor() {
        this.client = axios.create({
            baseURL: `${API_BASE_URL}/api/emails`,
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: 10000,
        });

        // Add auth token to requests
        this.client.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('authToken');
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => {
                console.error('Request interceptor error:', error);
                return Promise.reject(error);
            }
        );

        // Handle errors
        this.client.interceptors.response.use(
            (response) => response,
            (error) => {
                console.error('Email service response error:', error.response?.data || error.message);
                return Promise.reject(error);
            }
        );
    }

    // Transactional Emails
    async sendWelcomeEmail(userEmail: string, name: string) {
        console.log(`Attempting to send welcome email to ${userEmail}`);
        try {
            const response = await this.client.post('/welcome', {
                user_email: userEmail,
                name: name,
            });
            console.log('Welcome email sent successfully');
            return response.data;
        } catch (error: any) {
            console.error('Failed to send welcome email:', error.response?.data || error.message);
            throw new Error(error.response?.data?.detail || 'Failed to send welcome email');
        }
    }

    async sendPayoutEmail(userEmail: string, name: string, amount: string | number, commissionFrom: string, transactionId: string) {
        console.log(`Attempting to send payout email to ${userEmail}`);
        try {
            const response = await this.client.post('/payout', {
                user_email: userEmail,
                name: name,
                amount: parseFloat(amount.toString()),
                commission_from: commissionFrom,
                transaction_id: transactionId,
            });
            console.log('Payout email sent successfully');
            return response.data;
        } catch (error: any) {
            console.error('Failed to send payout email:', error.response?.data || error.message);
            throw new Error(error.response?.data?.detail || 'Failed to send payout email');
        }
    }

    async sendPaymentSuccessEmail(userEmail: string, name: string, amount: string | number, planName: string, nextBillingDate: string) {
        console.log(`Attempting to send payment success email to ${userEmail}`);
        try {
            const response = await this.client.post('/payment-success', {
                user_email: userEmail,
                name: name,
                amount: parseFloat(amount.toString()),
                plan_name: planName,
                next_billing_date: nextBillingDate,
            });
            console.log('Payment success email sent successfully');
            return response.data;
        } catch (error: any) {
            console.error('Failed to send payment success email:', error.response?.data || error.message);
            throw new Error(error.response?.data?.detail || 'Failed to send payment success email');
        }
    }

    async sendPaymentFailedEmail(userEmail: string, name: string, amount: string | number, reason: string) {
        console.log(`Attempting to send payment failed email to ${userEmail}`);
        try {
            const response = await this.client.post('/payment-failed', {
                user_email: userEmail,
                name: name,
                amount: parseFloat(amount.toString()),
                reason: reason,
            });
            console.log('Payment failed email sent successfully');
            return response.data;
        } catch (error: any) {
            console.error('Failed to send payment failed email:', error.response?.data || error.message);
            throw new Error(error.response?.data?.detail || 'Failed to send payment failed email');
        }
    }

    async sendReportDownloadEmail(userEmail: string, name: string, reportName: string, analysisType: string, downloadUrl: string) {
        console.log(`Attempting to send report download email to ${userEmail}`);
        try {
            const response = await this.client.post('/report-download', {
                user_email: userEmail,
                name: name,
                report_name: reportName,
                analysis_type: analysisType,
                download_url: downloadUrl,
            });
            console.log('Report download email sent successfully');
            return response.data;
        } catch (error: any) {
            console.error('Failed to send report email:', error.response?.data || error.message);
            throw new Error(error.response?.data?.detail || 'Failed to send report email');
        }
    }
}

export default new EmailService();
