import { useState, useEffect } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import axios from 'axios';
import { useCurrentUser, useUserChops, updateChopsAfterAction } from '../../../api/user';
import { useOpportunityAlerts } from '../../../api/analysis';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-toastify';

const API_BASE_URL = '/api';

interface Alert {
    id: number;
    title: string;
    category: string;
    priority: string;
    date: string;
    score: number;
    why_act_now: string;
    what_changed: string;
    action_required: string;
    potential_reward: string;
    time_remaining: string;
    alert_url: string;
    business_name?: string;
    attended: boolean;
    is_pinned?: boolean;
}

interface UserStats {
    total_alerts: number;
    total_chops: number;
    is_pro: boolean;
    pending_alerts: number;
}

const ALERTS_PER_PAGE = 5;

export default function AlertsPage() {
    const { data: user } = useCurrentUser();
    const { data: chopsData } = useUserChops();
    const queryClient = useQueryClient();
    const referral_code = user?.referral_code || '';

    const [currentPage, setCurrentPage] = useState(1);
    const {
        data: cachedAlertsData,
        isLoading: alertsLoading,
    } = useOpportunityAlerts();

    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [displayAlerts, setDisplayAlerts] = useState<Alert[]>([]);
    const [userStats, setUserStats] = useState<UserStats>({
        total_chops: 0,
        is_pro: false,
        total_alerts: 0,
        pending_alerts: 0
    });
    const [loading, setLoading] = useState(true);

    // Sync cached alerts data to local state
    useEffect(() => {
        if (cachedAlertsData && !alertsLoading) {
            const alertsData = cachedAlertsData as any[];
            const isProUser = user?.subscription_status === 'Active';

            const mappedAlerts = alertsData.map(alert => ({
                ...alert,
                id: alert.id,
                title: alert.title,
                category: alert.category || 'Marketing',
                priority: alert.priority || 'Medium Priority',
                date: alert.created_at ? new Date(alert.created_at).toISOString().split('T')[0] : '2024-01-10',
                score: alert.score || 85,
                why_act_now: alert.why_act_now || '',
                what_changed: alert.what_changed || '',
                action_required: alert.action_required || '',
                potential_reward: alert.potential_reward || 'Increase engagement rates by 25%, and build stronger professional relationships that convert to business opportunities.',
                time_remaining: alert.time_remaining || '2024-01-15',
                alert_url: (alert as any).url || alert.alert_url || '',
                business_name: alert.business_name,
                attended: alert.attended || false,
                is_pinned: alert.is_pinned || false
            }));

            // Sort: pinned first, then by score
            const sortedAlerts = mappedAlerts.sort((a, b) => {
                if (a.is_pinned && !b.is_pinned) return -1;
                if (!a.is_pinned && b.is_pinned) return 1;
                return b.score - a.score;
            });

            setAlerts(sortedAlerts);

            // Pagination for pro users
            const startIndex = (currentPage - 1) * ALERTS_PER_PAGE;
            const endIndex = startIndex + ALERTS_PER_PAGE;
            const paginatedAlerts = isProUser ? sortedAlerts.slice(startIndex, endIndex) : sortedAlerts.slice(0, ALERTS_PER_PAGE);

            setDisplayAlerts(paginatedAlerts);
            setUserStats(prev => ({
                ...prev,
                is_pro: isProUser,
                total_alerts: sortedAlerts.length,
                pending_alerts: sortedAlerts.filter(a => !a.attended).length
            }));
            setLoading(false);
        }
    }, [cachedAlertsData, alertsLoading, user, currentPage]);

    // Sync chops data
    useEffect(() => {
        if (chopsData) {
            setUserStats(prev => ({
                ...prev,
                total_chops: chopsData.total_chops
            }));
        }
    }, [chopsData]);

    // Share modal state
    const [showShareModal, setShowShareModal] = useState(false);
    const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
    const [isCopyHovered, setIsCopyHovered] = useState(false);

    const handleViewDetails = async (alert: Alert) => {
        console.log('Viewing alert details:', alert);
        if (alert.alert_url) {
            // Open the specific alert URL in a new tab
            window.open(alert.alert_url, '_blank');
        } else {
            // If no link, open an independent white page with 404 error
            const newWindow = window.open('', '_blank');
            if (newWindow) {
                newWindow.document.write(`
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>404 - Not Found</title>
                        <style>
                            body {
                                margin: 0;
                                padding: 0;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                height: 100vh;
                                background-color: #ffffff;
                                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                                color: #1a1a1a;
                            }
                            .container {
                                text-align: center;
                            }
                            h1 {
                                font-size: 120px;
                                margin: 0;
                                font-weight: 200;
                                line-height: 1;
                            }
                            p {
                                font-size: 18px;
                                color: #666;
                                margin-top: 10px;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>404</h1>
                            <p>Resource Not Found</p>
                        </div>
                    </body>
                    </html>
                `);
                newWindow.document.close();
            }
        }

        // Track view in background
        try {
            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/alerts/view`, { alert_id: alert.id }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            queryClient.invalidateQueries({ queryKey: ['opportunityAlerts'] });
        } catch (error) {
            console.error('Error tracking alert view:', error);
        }
    };

    const handleShare = (alert: Alert) => {
        setSelectedAlert(alert);
        setShowShareModal(true);
    };

    const shareToSocialMedia = async (platform: string) => {
        if (!selectedAlert) return;

        const shareUrl = `${window.location.origin}/signup?ref=${referral_code}`;
        const alertUrl = `${shareUrl}&alert=${selectedAlert.id}`;
        const text = selectedAlert.title; // Alert headline

        let socialUrl = '';

        switch (platform) {
            case 'twitter':
                socialUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(alertUrl)}`;
                break;
            case 'facebook':
                socialUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(alertUrl)}`;
                break;
            case 'linkedin':
                socialUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(alertUrl)}`;
                break;
            case 'whatsapp':
                socialUrl = `https://wa.me/?text=${encodeURIComponent(text + ' ' + alertUrl)}`;
                break;
        }

        if (socialUrl) {
            window.open(socialUrl, '_blank');
        }

        // Track share in background (no chops awarded)
        try {
            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/alerts/share`,
                { alert_id: selectedAlert.id, platform },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            // Comment out chops system
            // await updateChopsAfterAction(queryClient);
        } catch (error) {
            console.error('Error tracking share:', error);
        }

        setShowShareModal(false);
    };

    const copyLink = async () => {
        if (!selectedAlert) return;

        const shareUrl = `${window.location.origin}/signup?ref=${referral_code}`;

        try {
            await navigator.clipboard.writeText(shareUrl);
            console.log('Referral link copied to clipboard:', shareUrl);
            toast.success("Referral link copied to clipboard!");

            // Track copy in background (no chops awarded)
            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/alerts/share`,
                { alert_id: selectedAlert.id, platform: 'copy_link' },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            // Comment out chops system
            // await updateChopsAfterAction(queryClient);
        } catch (error) {
            console.error('Error copying link:', error);
        }

        setShowShareModal(false);
    };

    const handlePinAlert = async (alertId: number) => {
        // Optimistic UI update - instant feedback
        const updatedAlerts = alerts.map(a =>
            a.id === alertId ? { ...a, is_pinned: !a.is_pinned } : a
        );

        // Re-sort after pinning
        const sortedAlerts = updatedAlerts.sort((a, b) => {
            if (a.is_pinned && !b.is_pinned) return -1;
            if (!a.is_pinned && b.is_pinned) return 1;
            return b.score - a.score;
        });

        // Update state immediately
        setAlerts(sortedAlerts);

        // Update display alerts
        const isProUser = user?.subscription_status === 'Active';
        const startIndex = (currentPage - 1) * ALERTS_PER_PAGE;
        const endIndex = startIndex + ALERTS_PER_PAGE;
        const paginatedAlerts = isProUser ? sortedAlerts.slice(startIndex, endIndex) : sortedAlerts.slice(0, ALERTS_PER_PAGE);
        setDisplayAlerts(paginatedAlerts);

        // Background API call
        try {
            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/alerts/pin`, { alert_id: alertId }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            queryClient.invalidateQueries({ queryKey: ['opportunityAlerts'] });
        } catch (error) {
            console.error('Error pinning alert:', error);
            // Revert on error
            setAlerts(alerts);
            const revertStartIndex = (currentPage - 1) * ALERTS_PER_PAGE;
            const revertEndIndex = revertStartIndex + ALERTS_PER_PAGE;
            const revertPaginated = isProUser ? alerts.slice(revertStartIndex, revertEndIndex) : alerts.slice(0, ALERTS_PER_PAGE);
            setDisplayAlerts(revertPaginated);
        }
    };

    const getPriorityColor = (priority: string) => {
        if (priority.toLowerCase().includes('high')) {
            return { bg: '#fef2f2', text: '#991b1b', border: '#ef4444' };
        } else if (priority.toLowerCase().includes('medium')) {
            return { bg: '#fff7ed', text: '#9a3412', border: '#f97316' };
        } else {
            return { bg: '#eff6ff', text: '#1e40af', border: '#3b82f6' };
        }
    };

    const totalPages = Math.ceil(alerts.length / ALERTS_PER_PAGE);

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex' }}>
            <DashboardSidebar
                isMobileMenuOpen={isMobileMenuOpen}
                setIsMobileMenuOpen={setIsMobileMenuOpen}
            />

            <div className="flex-1 flex flex-col min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
                {/* Header */}
                <header style={{ backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <button
                            style={{
                                display: window.innerWidth >= 768 ? 'none' : 'flex', alignItems: 'center', justifyContent: 'center', width: '40px', height: '40px', backgroundColor: 'transparent', border: 'none', borderRadius: '6px', color: '#6b7280', cursor: 'pointer', marginRight: '16px'
                            }}
                            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                        >
                            <i className="ri-menu-line" style={{ fontSize: '20px' }}></i>
                        </button>
                        <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                            Opportunity Alerts
                        </h1>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        {userStats.is_pro && (
                            <div style={{ backgroundColor: '#fef3c7', padding: '6px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600', color: '#92400e', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <i className="ri-vip-crown-fill"></i>
                                Pro User
                            </div>
                        )}
                    </div>
                </header>

                {/* Content */}
                <div style={{ flex: 1, padding: '24px' }}>
                    {/* Stats Cards */}
                    {/* Stats Cards - Commented out as requested */}
                    {/* <div style={{
                        display: 'grid',
                        gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(4, 1fr)' : window.innerWidth >= 640 ? 'repeat(2, 1fr)' : '1fr', gap: '24px', marginBottom: '32px'
                    }}>
                        <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Total Alerts</p>
                                    <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                                        {userStats.total_alerts}
                                    </p>
                                </div>
                                <div style={{ width: '48px', height: '48px', backgroundColor: '#dbeafe', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-notification-line" style={{ color: '#3b82f6', fontSize: '20px' }}></i>
                                </div>
                            </div>
                        </div>

                        <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Pending</p>
                                    <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                                        {userStats.pending_alerts}
                                    </p>
                                </div>
                                <div style={{ width: '48px', height: '48px', backgroundColor: '#fef3c7', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-time-line" style={{ color: '#f59e0b', fontSize: '20px' }}></i>
                                </div>
                            </div>
                        </div>

                        <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Total Chops</p>
                                    <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                                        {userStats.total_chops}
                                    </p>
                                </div>
                                <div style={{ width: '48px', height: '48px', backgroundColor: '#dcfce7', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-star-line" style={{ color: '#16a34a', fontSize: '20px' }}></i>
                                </div>
                            </div>
                        </div>

                        <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Subscription</p>
                                    <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                                        {userStats.is_pro ? 'Pro' : 'Free'}
                                    </p>
                                </div>
                                <div style={{ width: '48px', height: '48px', backgroundColor: '#f3e8ff', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-vip-crown-line" style={{ color: '#8b5cf6', fontSize: '20px' }}></i>
                                </div>
                            </div>
                        </div>
                    </div> */}

                    {/* Loading State */}
                    {loading && (
                        <div style={{ textAlign: 'center', padding: '40px' }}>
                            <div style={{ fontSize: '18px', color: '#6b7280' }}>Loading alerts...</div>
                        </div>
                    )}

                    {/* Alerts List */}
                    {!loading && (
                        <>
                            {alerts.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '60px 24px', backgroundColor: '#ffffff', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
                                    <i className="ri-notification-line" style={{ fontSize: '64px', color: '#d1d5db', marginBottom: '16px', display: 'block' }}></i>
                                    <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '8px' }}>
                                        No Alerts Available
                                    </h3>
                                    <p style={{ fontSize: '14px', color: '#6b7280' }}>
                                        Check back later for new opportunities!
                                    </p>
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                                    {displayAlerts.map((alert) => {
                                        const priorityColors = getPriorityColor(alert.priority);
                                        return (
                                            <div
                                                key={alert.id}
                                                style={{
                                                    backgroundColor: '#ffffff', borderRadius: '16px', overflow: 'hidden', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', transition: 'box-shadow 0.3s ease', position: 'relative', border: alert.is_pinned ? '2px solid #f59e0b' : 'none'
                                                }}
                                            >
                                                {/* Pinned Badge */}
                                                {alert.is_pinned && (
                                                    <div style={{ position: 'absolute', top: '16px', right: '60px', backgroundColor: '#f59e0b', color: '#ffffff', padding: '6px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600', zIndex: 10, display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                        <i className="ri-pushpin-fill"></i>
                                                        Pinned
                                                    </div>
                                                )}

                                                <div style={{ padding: '32px' }}>
                                                    {/* Header - matching the image format */}
                                                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                                                            {/* Score Badge */}
                                                            <span style={{ backgroundColor: '#fef3c7', color: '#92400e', padding: '6px 12px', borderRadius: '20px', fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                                <i className="ri-star-fill"></i>
                                                                Score: {alert.score}
                                                            </span>
                                                            {/* Priority */}
                                                            <span style={{ backgroundColor: priorityColors.bg, color: priorityColors.text, padding: '6px 12px', borderRadius: '20px', fontSize: '14px', fontWeight: '600' }}>
                                                                {alert.priority}
                                                            </span>
                                                            {/* Category */}
                                                            <span style={{ backgroundColor: '#e0f2fe', color: '#075985', padding: '6px 12px', borderRadius: '20px', fontSize: '14px', fontWeight: '600' }}>
                                                                {alert.category}
                                                            </span>
                                                            {/* Date */}
                                                            <span style={{ fontSize: '14px', color: '#6b7280' }}>{alert.date}</span>
                                                        </div>

                                                        {/* Pin Button */}
                                                        <button
                                                            onClick={() => handlePinAlert(alert.id)}
                                                            style={{
                                                                backgroundColor: alert.is_pinned ? '#fef3c7' : '#f3f4f6',
                                                                color: alert.is_pinned ? '#92400e' : '#374151',
                                                                border: 'none',
                                                                borderRadius: '8px',
                                                                width: '40px',
                                                                height: '40px',
                                                                cursor: 'pointer',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                justifyContent: 'center',
                                                                transition: 'all 0.3s ease'
                                                            }}
                                                        >
                                                            <i className={`ri-pushpin-${alert.is_pinned ? 'fill' : 'line'} text-xl`}></i>
                                                        </button>
                                                    </div>

                                                    <h2 style={{ fontSize: window.innerWidth >= 768 ? '24px' : '20px', fontWeight: 'bold', color: '#111827', marginBottom: '24px', lineHeight: '1.3' }}>
                                                        {alert.title}
                                                    </h2>

                                                    {/* Content Sections - 3 boxes */}
                                                    <div style={{ display: 'flex', flexDirection: window.innerWidth >= 1024 ? 'row' : 'column', gap: '24px', marginBottom: '32px' }}>
                                                        <div style={{ flex: 1, backgroundColor: '#eff6ff', padding: '20px', borderRadius: '12px', border: '1px solid #3b82f6' }}>
                                                            <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1d4ed8', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                                <i className="ri-alert-line" style={{ fontSize: '18px' }}></i>
                                                                Why Act Now
                                                            </h3>
                                                            <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>
                                                                {alert.why_act_now}
                                                            </p>
                                                        </div>

                                                        <div style={{ flex: 1, backgroundColor: '#fef7ff', padding: '20px', borderRadius: '12px', border: '1px solid #a855f7' }}>
                                                            <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#7c3aed', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                                <i className="ri-trophy-line" style={{ fontSize: '18px' }}></i>
                                                                Potential Reward
                                                            </h3>
                                                            <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>
                                                                {alert.potential_reward}
                                                            </p>
                                                        </div>

                                                        <div style={{ flex: 1, backgroundColor: '#f0fdf4', padding: '20px', borderRadius: '12px', border: '1px solid #22c55e' }}>
                                                            <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#16a34a', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                                <i className="ri-flashlight-line" style={{ fontSize: '18px' }}></i>
                                                                Action Required
                                                            </h3>
                                                            <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>
                                                                {alert.action_required || 'Review this alert and take appropriate action based on your business strategy.'}
                                                            </p>
                                                        </div>
                                                    </div>

                                                    {/* Action Buttons */}
                                                    <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(2, 1fr)' : '1fr', gap: '16px', marginTop: '8px' }}>
                                                        <button onClick={() => handleShare(alert)}
                                                            style={{ height: '52px', backgroundColor: '#f97316', color: '#ffffff', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', transition: 'all 0.3s ease', padding: '12px 20px' }}
                                                        >
                                                            <i className="ri-share-line"></i>
                                                            Share
                                                        </button>

                                                        <button onClick={() => handleViewDetails(alert)}
                                                            style={{ height: '52px', backgroundColor: '#3b82f6', color: '#ffffff', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', transition: 'all 0.3s ease', padding: '12px 20px' }}
                                                        >
                                                            <i className="ri-external-link-line"></i>
                                                            View Details
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}

                                    {/* Upgrade Prompt for Free Users Only */}
                                    {!userStats.is_pro && (
                                        <div style={{ textAlign: 'center', padding: '40px 24px', backgroundColor: '#fff7ed', borderRadius: '16px', border: '2px dashed #fb923c', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)', marginTop: '32px' }}>
                                            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#c2410c', marginBottom: '12px' }}>
                                                <i className="ri-vip-crown-line" style={{ marginRight: '8px' }}></i>
                                                Unlock More Opportunities!
                                            </h3>
                                            <p style={{ fontSize: '16px', color: '#9a3412', marginBottom: '20px' }}>
                                                You've viewed your first {ALERTS_PER_PAGE} alerts. Upgrade to Pro to access unlimited alerts, pagination, and earn up to 5x more Chops!
                                            </p>
                                            <button
                                                onClick={() => window.location.href = '/dashboard/upgrade'}
                                                style={{
                                                    backgroundColor: '#f97316',
                                                    color: '#ffffff',
                                                    padding: '12px 24px',
                                                    borderRadius: '8px',
                                                    border: 'none',
                                                    fontSize: '16px',
                                                    fontWeight: '700',
                                                    cursor: 'pointer',
                                                    transition: 'background-color 0.3s ease',
                                                }}
                                            >
                                                <i className="ri-arrow-up-circle-line" style={{ marginRight: '8px' }}></i>
                                                Upgrade to Pro Now!
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    )}

                    {/* Pagination - Only for Pro Users */}
                    {userStats.is_pro && totalPages > 1 && (
                        <div style={{
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            gap: '12px',
                            marginTop: '40px'
                        }}>
                            <button
                                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                                disabled={currentPage === 1}
                                style={{
                                    padding: '10px 16px',
                                    backgroundColor: currentPage === 1 ? '#e5e7eb' : '#3b82f6',
                                    color: currentPage === 1 ? '#9ca3af' : '#ffffff',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}
                            >
                                <i className="ri-arrow-left-s-line"></i>
                                Previous
                            </button>

                            <div style={{ display: 'flex', gap: '8px' }}>
                                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                                    <button
                                        key={page}
                                        onClick={() => setCurrentPage(page)}
                                        style={{
                                            width: '40px',
                                            height: '40px',
                                            backgroundColor: currentPage === page ? '#3b82f6' : '#ffffff',
                                            color: currentPage === page ? '#ffffff' : '#374151',
                                            border: currentPage === page ? 'none' : '1px solid #e5e7eb',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            fontSize: '14px',
                                            fontWeight: '600',
                                            transition: 'all 0.2s ease'
                                        }}
                                    >
                                        {page}
                                    </button>
                                ))}
                            </div>

                            <button
                                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                                disabled={currentPage === totalPages}
                                style={{
                                    padding: '10px 16px',
                                    backgroundColor: currentPage === totalPages ? '#e5e7eb' : '#3b82f6',
                                    color: currentPage === totalPages ? '#9ca3af' : '#ffffff',
                                    border: 'none',
                                    borderRadius: '8px',
                                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px'
                                }}
                            >
                                Next
                                <i className="ri-arrow-right-s-line"></i>
                            </button>
                        </div>
                    )}
                </div>

                {/* Share Modal */}
                {showShareModal && (
                    <div style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(0, 0, 0, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 9999
                    }} onClick={() => setShowShareModal(false)}>
                        <div style={{
                            backgroundColor: '#ffffff',
                            borderRadius: '16px',
                            padding: '24px',
                            maxWidth: '430px',
                            width: '90%',
                            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
                        }} onClick={(e) => e.stopPropagation()}>
                            <h3 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '24px', textAlign: 'center', color: '#111827' }}>
                                Share Alert
                            </h3>

                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '20px' }}>
                                <button onClick={() => shareToSocialMedia('twitter')}
                                    style={{
                                        padding: '14px 16px',
                                        backgroundColor: '#1DA1F2',
                                        color: '#ffffff',
                                        border: 'none',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: '700',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px',
                                        transition: 'opacity 0.2s'
                                    }}>
                                    <i className="ri-twitter-fill" style={{ fontSize: '18px' }}></i>
                                    Twitter
                                </button>

                                <button onClick={() => shareToSocialMedia('facebook')}
                                    style={{
                                        padding: '14px 16px',
                                        backgroundColor: '#4267B2',
                                        color: '#ffffff',
                                        border: 'none',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: '700',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px',
                                        transition: 'opacity 0.2s'
                                    }}>
                                    <i className="ri-facebook-fill" style={{ fontSize: '18px' }}></i>
                                    Facebook
                                </button>

                                <button onClick={() => shareToSocialMedia('linkedin')}
                                    style={{
                                        padding: '14px 16px',
                                        backgroundColor: '#0077B5',
                                        color: '#ffffff',
                                        border: 'none',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: '700',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px',
                                        transition: 'opacity 0.2s'
                                    }}>
                                    <i className="ri-linkedin-fill" style={{ fontSize: '18px' }}></i>
                                    LinkedIn
                                </button>

                                <button onClick={() => shareToSocialMedia('whatsapp')}
                                    style={{
                                        padding: '14px 16px',
                                        backgroundColor: '#25D366',
                                        color: '#ffffff',
                                        border: 'none',
                                        borderRadius: '12px',
                                        fontSize: '14px',
                                        fontWeight: '700',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px',
                                        transition: 'opacity 0.2s'
                                    }}>
                                    <i className="ri-whatsapp-fill" style={{ fontSize: '18px' }}></i>
                                    WhatsApp
                                </button>
                            </div>

                            <button
                                onClick={copyLink}
                                onMouseEnter={() => setIsCopyHovered(true)}
                                onMouseLeave={() => setIsCopyHovered(false)}
                                style={{
                                    width: '100%',
                                    padding: '14px 16px',
                                    backgroundColor: '#f3f4f6',
                                    color: '#374151',
                                    border: 'none',
                                    borderRadius: '12px',
                                    fontSize: '15px',
                                    fontWeight: '700',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '4px',
                                    marginBottom: '16px',
                                    transition: 'background-color 0.2s',
                                    position: 'relative'
                                }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <i className="ri-file-copy-line" style={{ fontSize: '18px' }}></i>
                                    Copy Link
                                </div>
                                {isCopyHovered && (
                                    <div style={{
                                        fontSize: '11px',
                                        color: '#6b7280',
                                        fontWeight: 'normal',
                                        wordBreak: 'break-all',
                                        marginTop: '4px',
                                        padding: '0 8px',
                                        textAlign: 'center'
                                    }}>
                                        {`${window.location.origin}/signup?ref=${referral_code}`}
                                    </div>
                                )}
                            </button>

                            <button onClick={() => setShowShareModal(false)}
                                style={{
                                    width: '100%',
                                    padding: '14px 16px',
                                    backgroundColor: 'transparent',
                                    color: '#6b7280',
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '12px',
                                    fontSize: '15px',
                                    fontWeight: '700',
                                    cursor: 'pointer',
                                    transition: 'background-color 0.2s'
                                }}>
                                Cancel
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

