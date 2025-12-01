import { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:8000';

// --- AUTHENTICATION HELPERS (START) ---
/**
 * Retrieves the authentication token from local storage.
 */
const getAuthToken = (): string | null => {
    // Check for common token key names in order of preference
    const token = localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('authToken');
    
    if (token) {
        // Log the token (truncated for security, if you want to see the full token, remove slice)
        console.log(`✅ AUTH_TOKEN: Token found! Starting with: ${token.slice(0, 15)}...`);
    } else {
        // Log that no token was found
        console.warn('❌ AUTH_TOKEN: No token found in localStorage (Checked access_token, token, authToken).');
    }

    return token;
};

/**
 * Creates the standard authorization headers object.
 */
const getAuthHeaders = (): Record<string, string> => {
    const token = getAuthToken();
    const result = {
       ' Content-Type': 'application/json', 
        // Note: The backend needs the 'Bearer' prefix for Authorization header
        'Authorization': token ? `Bearer ${token}` : '' 
    };console.log(result);
    return { 
        'Content-Type': 'application/json', 
        // Note: The backend needs the 'Bearer' prefix for Authorization header
        'Authorization': token ? `Bearer ${token}` : '' 
    };
};

const fetchUserIdFromToken = async (): Promise<number | null> => {
    const token = getAuthToken();
    if (!token) {
        console.error('❌ AUTH: No authentication token found.');
        return null;
    }

    try {
        // Use the token to fetch the current user's details
        const response = await fetch(`${API_BASE_URL}/users/me`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            credentials: "include", // <-- REQUIRED when allow_credentials=True
        });

        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                console.error('❌ AUTH: Token expired or invalid. Status:', response.status);
            } else {
                console.error('❌ AUTH: Failed to fetch user details. Status:', response.status);
            }
            return null;
        }

        const userData = await response.json();
        const id = userData.id || userData.user_id; // Use common key names for user ID

        if (typeof id === 'number') {
            console.log(`✅ AUTH: User ID ${id} retrieved successfully from token.`);
            // Store the ID locally after successful retrieval for future initializations
            localStorage.setItem('userId', id.toString()); 
            return id;
        } else {
            console.error('❌ AUTH: User details endpoint did not return a valid ID.');
            return null;
        }

    } catch (error) {
        console.error('❌ AUTH: API call failed during user ID retrieval:', error);
        return null;
    }
};

// --- AUTHENTICATION HELPERS (END) ---

interface Alert {
    id: number;
    title: string;
    source: string;
    score: number;
    priority: 'High' | 'Medium' | 'Low';
    category: string;
    time_remaining: string;
    date: string | Date;
    why_act_now: string;
    potential_reward: string;
    action_required: string;
    has_viewed: boolean;
    has_shared: boolean;
    is_attended: boolean;
    total_views: number;
    total_shares: number; 
    is_pinned: boolean;
}

interface AlertStats {
    total_alerts: number;
    unattended_count: number;
}

type SocialPlatform = 'twitter' | 'facebook' | 'linkedin' | 'whatsapp';
interface SocialButton {
    name: string;
    platform: SocialPlatform;
    icon: string;
    color: string;
}

// --- COMPONENT START ---

export default function AlertsPage() {
    // --- STATE (UNCHANGED) ---
    const [showToast, setShowToast] = useState(false);
    const [toastMessage, setToastMessage] = useState('');
    const [userChops, setUserChops] = useState(0);
    const [sharedAlerts, setSharedAlerts] = useState<Set<string>>(new Set());
    const [viewedAlerts, setViewedAlerts] = useState<Set<string>>(new Set());
    const [attendedAlerts, setAttendedAlerts] = useState<Set<number>>(new Set());
    const [showShareModal, setShowShareModal] = useState(false);
    const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
    const [subscriptionStatus, setSubscriptionStatus] = useState('free');
    const [currentPage, setCurrentPage] = useState(1);
    const [viewportWidth, setViewportWidth] = useState(window.innerWidth);
    const [userId, setUserId] = useState<number | null>(null);
    const [referralCount, setReferralCount] = useState(0);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);
    const [readingChops, setReadingChops] = useState(0);
    const [sharingChops, setSharingChops] = useState(0);
    const [referralChops, setReferralChops] = useState(0);
    const [alertStats, setAlertStats] = useState<AlertStats>({
        total_alerts: 0,
        unattended_count: 0
    });
    const [pinnedAlerts, setPinnedAlerts] = useState<Set<number>>(new Set());

    const ALERTS_PER_PAGE = 5;
    const FREE_USER_ALERT_LIMIT = 3;
    const isPro = subscriptionStatus === 'active';

    // --- USE EFFECTS (UPDATED) ---

    useEffect(() => {
        initializeData();
        const handleResize = () => setViewportWidth(window.innerWidth);
        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, []);

    // --- DATA FETCHING & LOGIC (UPDATED) ---

    const initializeData = async () => {

        let currentUserId: number | null = null;
        let storedUserId = localStorage.getItem('userId');

        if (storedUserId) {
            currentUserId = parseInt(storedUserId);
            console.log(`ℹ️ INIT: Found local userId: ${currentUserId}. Validating...`);
        }
        
        // 1. If no ID (or we need to validate it), use the token to get the ID
        if (!currentUserId || !getAuthToken()) {
            console.log('⚠️ INIT: No local userId or token found. Attempting to fetch ID via token...');
            currentUserId = await fetchUserIdFromToken();
        }

        if (currentUserId === null) {
            console.error('❌ INIT: Failed to establish user session. No token or invalid token.');
            // Do not redirect, just clear local state and stop loading.
            setUserId(null); 
            setLoading(false);
            showToastNotification('Session expired. Please log in.');
            localStorage.removeItem('userId'); // Remove the old invalid ID
            // Optional: If you MUST redirect, do it here, but the user requested avoiding it.
            // window.location.href = '/login';
            return;
        }

        // 2. Set the userId state (important for other components/logic that might read it)
        setUserId(currentUserId); 
        
        try {
            // 3. Fetch user data (including subscription status and chops)
            await fetchUserData(currentUserId);
            
            // 4. Fetch alert data and stats
            await fetchAlerts(currentUserId);
            await fetchAlertStats(currentUserId);
            setLoading(false);
        } catch (error) {
            console.error('❌ INIT: Critical initialization error:', error);
            // On a critical error (like 401 from fetchUserData/fetchAlerts), 
            // clear the session data.
            localStorage.removeItem('userId');
            // Optional: window.location.href = '/login'; 
        } finally {
            setLoading(false); // Stop loading regardless of success/failure
        }
    };

    const fetchUserData = async (id: number) => {
       const token = getAuthToken();
        if (!token) {
            console.error('❌ AUTH: No authentication token found.');
            return null;
        }

        try {
            // Use the token to fetch the current user's details
            const response = await fetch(`${API_BASE_URL}/users/me`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                credentials: "include", // <-- REQUIRED when allow_credentials=True
            });

            if (!response.ok) {
                console.error(`❌ FETCH_USER: Server responded with status ${response.status} for user ${id}.`);
                // If the user's local ID is rejected by the server, handle as broken session
                throw new Error('Invalid user session or network error.');
            }
            const userData = await response.json();
            setUserChops(userData.total_chops);
            setSubscriptionStatus(userData.subscription_status);
            setReferralCount(userData.referral_count);
            setReadingChops(userData.alert_reading_chops);
            setSharingChops(userData.alert_sharing_chops);
            setReferralChops(userData.referral_chops);
            console.log(`✅ FETCH_USER: Data for user ${id} loaded.`);
        } catch (error) {
            console.error('❌ FETCH_USER: Error fetching user data:', error);
            throw error; 
        }
    };

    const fetchAlerts = async (id: number) => {
        const token = getAuthToken();
        if (!token) {
            console.error('❌ AUTH: No authentication token found.');
            return null;
        }
        try {
            setLoading(true);
            // Ensure both query param and auth header are used for security
            const response = await fetch(`${API_BASE_URL}/api/alerts`, {
               method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                credentials: "include", // <-- REQUIRED when allow_credentials=True
            });

            if (!response.ok) {
                 console.error(`❌ FETCH_ALERTS: Server responded with status ${response.status} for user ${id}.`);
                 throw new Error('Failed to fetch alerts.');
            }
            
            const alertsData: Alert[] = await response.json();
            setAlerts(alertsData);
            
            // ... (rest of the logic for setting viewed/shared/attended Sets - UNCHANGED)
            const viewed = new Set<string>();
            const shared = new Set<string>();
            const attended = new Set<number>();
            const pinned = new Set<number>();
            
            alertsData.forEach((alert: Alert) => {
                if (alert.has_viewed) viewed.add(alert.id.toString());
                if (alert.has_shared) shared.add(alert.id.toString());
                if (alert.is_attended) attended.add(alert.id);
                if (alert.is_pinned) pinned.add(alert.id);
            });
            
            setViewedAlerts(viewed);
            setSharedAlerts(shared);
            setAttendedAlerts(attended);
            setPinnedAlerts(pinned);
            console.log(`✅ FETCH_ALERTS: ${alertsData.length} alerts loaded.`);

        } catch (error) {
            console.error('❌ FETCH_ALERTS: Error fetching alerts:', error);
            showToastNotification('Error loading alerts');
            throw error; // Re-throw to be caught by initializeData if critical
        } finally {
             setLoading(false);
        }
    };

    const fetchAlertStats = async (id: number) => {
        const token = getAuthToken();
        if (!token) {
            console.error('❌ AUTH: No authentication token found.');
            return null;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/api/users/${id}/alerts/stats`, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                credentials: "include", // <-- REQUIRED when allow_credentials=True
            });

            if (response.ok) {
                const stats: AlertStats = await response.json();
                setAlertStats(stats);
                console.log(`✅ FETCH_STATS: Stats loaded for user ${id}.`);
            } else {
                 console.error(`❌ FETCH_STATS: Server responded with status ${response.status} for user ${id}.`);
                 throw new Error('Failed to fetch stats.');
            }
        } catch (error) {
            console.error('❌ FETCH_STATS: Error fetching alert stats:', error);
            throw error;
        }
    };

    const handlePinAlert = async (alertId: number) => {
        const currentUserId = userId;
        if (currentUserId === null) {
            console.error('❌ ACTION_PIN: User ID is null. Cannot pin alert.');
            showToastNotification('Error: User session invalid. Please refresh.');
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/alerts/pin`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ alert_id: alertId })
            });

            if (response.ok) {
                const data = await response.json();
                
                // Update local state
                const newPinnedAlerts = new Set(pinnedAlerts);
                if (data.is_pinned) {
                    newPinnedAlerts.add(alertId);
                    showToastNotification('Alert pinned to top!');
                } else {
                    newPinnedAlerts.delete(alertId);
                    showToastNotification('Alert unpinned');
                }
                setPinnedAlerts(newPinnedAlerts);

                // Update the alerts list to reflect pinned status
                setAlerts(prevAlerts => 
                    prevAlerts.map(alert => 
                        alert.id === alertId 
                            ? { ...alert, is_pinned: data.is_pinned }
                            : alert
                    )
                );

                console.log(`✅ ACTION_PIN: Alert ${alertId} ${data.is_pinned ? 'pinned' : 'unpinned'}.`);
            } else {
                console.error(`❌ ACTION_PIN: Failed to toggle pin. Status: ${response.status}`);
                showToastNotification('Error toggling pin status');
            }
        } catch (error) {
            console.error('❌ ACTION_PIN: Error toggling pin:', error);
            showToastNotification('Error toggling pin status');
        }
    };

    // --- ACTION HANDLERS (UPDATED TO USE getAuthHeaders()) ---

    const showToastNotification = (message: string) => {
        setToastMessage(message);
        setShowToast(true);
        setTimeout(() => setShowToast(false), 3000);
    };

    const handleViewDetails = async (alert:Alert) => {
        const alertId = alert.id.toString();
        
        const currentUserId = userId; 
        if (currentUserId === null) {
            console.error('❌ ACTION_VIEW: User ID is null. Cannot record view or fetch data.');
            showToastNotification('Error: User session invalid. Please refresh.');
            return;
        }

        if (!viewedAlerts.has(alertId)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/alerts/view`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ alert_id: alert.id })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    // Update all relevant state immediately
                    setUserChops(data.total_chops);
                    setReadingChops(data.alert_reading_chops);
                    setViewedAlerts(new Set([...viewedAlerts, alertId]));
                    setAttendedAlerts(new Set([...attendedAlerts, alert.id]));
                    
                    // Update alert stats
                    setAlertStats(prev => ({
                        ...prev,
                        unattended_count: Math.max(0, prev.unattended_count - 1)
                    }));
                    
                    // Update the alert in the list to show attended status
                    setAlerts(prevAlerts => 
                        prevAlerts.map(a => 
                            a.id === alert.id 
                                ? { ...a, has_viewed: true, is_attended: true }
                                : a
                        )
                    );
                    
                    if (data.chops_earned > 0) {
                        showToastNotification(`You earned ${data.chops_earned} Chops for viewing this alert!`);
                    }
                    console.log(`✅ ACTION_VIEW: View recorded for alert ${alertId}.`);
                } else {
                    console.error(`❌ ACTION_VIEW: Failed to record view. Status: ${response.status}`);
                    showToastNotification('Error recording alert view');
                }
            } catch (error) {
                console.error('❌ ACTION_VIEW: Error viewing alert:', error);
                showToastNotification('Error recording alert view');
            }
        }
        
        // Open the link
        if (alert.source && alert.source !== '#') {
            window.open(alert.source, '_blank');
        } else {
            window.open('https://www.google.com/search?q=business+opportunities', '_blank');
        }
    };

    const handleShare = (alert: Alert) => {
        setSelectedAlert(alert);
        setShowShareModal(true);
    };


    const shareToSocialMedia = async (platform: SocialPlatform) => {
        if (!selectedAlert) return;

        const currentUserId = userId; 
        if (currentUserId === null) {
            console.error('❌ ACTION_SHARE: User ID is null. Cannot share.');
            showToastNotification('Error: User session invalid. Please refresh.');
            return;
        }

        try {
             // Use token-based headers for user data fetch
            const userResponse = await fetch(`${API_BASE_URL}/users/${currentUserId}`, {
                 headers: getAuthHeaders() }); 
            if (!userResponse.ok) throw new Error('Failed to fetch user data for sharing link.');
            const userData = await userResponse.json();
            const userName = userData.username;
            
            const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(userName)}`;
            const alertUrl = `${referralLink}&alert=${selectedAlert.id}`;
            const text = `Check out this business opportunity: ${selectedAlert.title}`;
            
            let shareUrl = '';
            
            switch (platform) {
                case 'twitter':
                    shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(alertUrl)}`;
                    break;
                case 'facebook':
                    shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(alertUrl)}`;
                    break;
                case 'linkedin':
                    shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(alertUrl)}`;
                    break;
                case 'whatsapp':
                    shareUrl = `https://wa.me/?text=${encodeURIComponent(text + ' ' + alertUrl)}`;
                    break;
            }
            
            if (shareUrl) {
                window.open(shareUrl, '_blank');
                await awardSharingPoints();
                console.log(`✅ ACTION_SHARE: Shared to ${platform} for alert ${selectedAlert.id}.`);
            }
        } catch (error) {
            console.error('❌ ACTION_SHARE: Error during link generation/share:', error);
            showToastNotification('Error preparing share link.');
        }

        setShowShareModal(false);
    };

    const copyLink = async () => {
        if (!selectedAlert) return;
        
        const currentUserId = userId; 
        if (currentUserId === null) {
            console.error('❌ ACTION_COPY: User ID is null. Cannot copy link.');
            showToastNotification('Error: User session invalid. Please refresh.');
            return;
        }
        
        try {
            // Use token-based headers for user data fetch
            const userResponse = await fetch(`${API_BASE_URL}/users/${currentUserId}`, { 
                headers: getAuthHeaders() }); 
             if (!userResponse.ok) throw new Error('Failed to fetch user data for sharing link.');
            const userData = await userResponse.json();
            
            const referralLink = `${window.location.origin}/signup?ref=$${userData.id}-${userData.referral_code}`;
            const alertUrl = `${referralLink}&alert=${selectedAlert.id}`;
            navigator.clipboard.writeText(alertUrl);
            await awardSharingPoints();
            showToastNotification('Link copied to clipboard!');
            console.log(`✅ ACTION_COPY: Link copied for alert ${selectedAlert.id}.`);
        } catch (error) {
            console.error('❌ ACTION_COPY: Error during link copy:', error);
            showToastNotification('Error copying link.');
        }

        setShowShareModal(false);
    };

    const awardSharingPoints = async () => {
    if (!selectedAlert) return;

    const currentUserId = userId;
    if (currentUserId === null) {
        showToastNotification('Error: Session invalid. Please refresh.');
        return;
    }

    const alertId = selectedAlert.id.toString();

    // Prevent double-awarding
    if (sharedAlerts.has(alertId)) {
        console.log(`Already shared alert ${alertId}, skipping API call`);
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/alerts/share`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ alert_id: selectedAlert.id })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Share API failed:', response.status, errorText);
            showToastNotification('Failed to record share');
            return;
        }

        const data = await response.json(); // Expect: { total_chops, alert_reading_chops?, alert_sharing_chops, chops_earned, ... }

        // 1. Update global chops
        setUserChops(data.total_chops || data.user_chops);
        if (data.alert_sharing_chops !== undefined) {
            setSharingChops(data.alert_sharing_chops);
        }

        // 2. Mark as shared locally (optimistic + confirmed)
        setSharedAlerts(prev => new Set(prev).add(alertId));

        // 3. Mark as attended (sharing counts as attending an alert)
        setAttendedAlerts(prev => new Set(prev).add(selectedAlert.id));

        // 4. Decrement unattended count
        setAlertStats(prev => ({
            ...prev,
            unattended_count: Math.max(0, prev.unattended_count - 1)
        }));

        // 5. Update the actual alert in the list so has_shared & is_attended become true
        setAlerts(prevAlerts =>
            prevAlerts.map(a =>
                a.id === selectedAlert.id
                    ? {
                          ...a,
                          has_shared: true,
                          is_attended: true  // sharing = attending
                      }
                    : a
            )
        );

        // 6. Show toast if chops were earned
        if (data.chops_earned > 0) {
            showToastNotification(`You earned ${data.chops_earned} Chops for sharing!`);
        }

        console.log(`Successfully shared alert ${selectedAlert.id}`);

        // Optional: refetch stats only if backend doesn't return updated ones
        // await fetchAlertStats(currentUserId);

    } catch (error) {
        console.error('Error in awardSharingPoints:', error);
        showToastNotification('Network error while sharing');
    }
    };

    // --- HELPER FUNCTIONS (UNCHANGED) ---

    const getScoreBgColor = (score: Alert['score']) => {
        if (score >= 90) return '#dcfce7';
        if (score >= 80) return '#fef3c7';
        if (score >= 70) return '#fed7aa';
        return '#fecaca';
    };

    const getPriorityBgColor = (priority: Alert['priority']) => {
        if (priority === 'High') return '#fef2f2';
        if (priority === 'Medium') return '#fffbeb';
        return '#f0fdf4';
    };

    const getScoreColor = (score: Alert['score']) => {
        if (score >= 90) return '#16a34a';
        if (score >= 80) return '#3b82f6';
        if (score >= 70) return '#f59e0b';
        return '#ef4444';
    };

    const getPriorityColor = (priority: Alert['priority']) => {
        if (priority === 'High') return '#dc2626';
        if (priority === 'Medium') return '#f59e0b';
        return '#16a34a';
    };

    const totalPages = Math.ceil(alerts.length / ALERTS_PER_PAGE);
    const startIndex = (currentPage - 1) * ALERTS_PER_PAGE;
    const endIndex = startIndex + ALERTS_PER_PAGE;
    
    let sortedAlerts = [...alerts];

// Sort: pinned first, then by attended status, then newest first
sortedAlerts.sort((a, b) => {
    // Pinned alerts come first
    if (a.is_pinned !== b.is_pinned) {
        return a.is_pinned ? -1 : 1;
    }
    // Then unattended alerts
    if (a.is_attended !== b.is_attended) {
        return a.is_attended ? 1 : -1;
    }
    // Then by date (newest first)
    return new Date(b.date).getTime() - new Date(a.date).getTime();
});

let displayedAlerts: Alert[] = [];
let hasMoreAlerts = false;

if (isPro) {
    displayedAlerts = sortedAlerts.slice(startIndex, endIndex);
} else {
    displayedAlerts = sortedAlerts.slice(0, FREE_USER_ALERT_LIMIT);
    hasMoreAlerts = sortedAlerts.length > FREE_USER_ALERT_LIMIT;
}


    // --- RENDERING (UNCHANGED) ---

    if (loading) {
        return (
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(to bottom right, #fff7ed, #ffffff)' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ 
                        width: '48px', height: '48px', border: '4px solid #fed7aa', borderTop: '4px solid #f97316',
                        borderRadius: '50%', margin: '0 auto 16px', animation: 'spin 1s linear infinite'
                    }}></div>
                    <p style={{ color: '#6b7280', fontSize: '16px' }}>Loading alerts...</p>
                </div>
                <style>{`
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        );
    }

    // If not logged in (userId is null after initialization) show an error message instead of the page content
    if (userId === null) {
         return (
            <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(to bottom right, #fff7ed, #ffffff)' }}>
                <div style={{ textAlign: 'center', padding: '32px', backgroundColor: '#fff', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)' }}>
                    <i className="ri-error-warning-line" style={{ color: '#ef4444', fontSize: '48px', marginBottom: '16px' }}></i>
                    <h2 style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', marginBottom: '8px' }}>Access Denied</h2>
                    <p style={{ color: '#6b7280', marginBottom: '24px' }}>You must be logged in to view opportunity alerts. Check console for details.</p>
                    <button onClick={() => window.location.href = '/login'} style={{ backgroundColor: '#f97316', color: '#fff', padding: '12px 20px', borderRadius: '8px', border: 'none', fontSize: '16px', fontWeight: '600', cursor: 'pointer' }}>
                        Go to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ background: 'linear-gradient(to bottom right, #fff7ed, #ffffff)', minHeight: '100vh', padding: '16px' }}>
            <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
                {/* Header */}
                <header style={{ 
                    backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '16px 24px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    borderRadius: '12px', marginBottom: '24px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                }}>
                    <h1 style={{ fontSize: viewportWidth >= 640 ? '24px' : '20px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                        Opportunity Alerts
                    </h1>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ 
                            backgroundColor: '#fff7ed', padding: '8px 16px', borderRadius: '20px',
                            fontSize: '14px', fontWeight: '600', color: '#ea580c', display: 'flex', alignItems: 'center', gap: '6px'
                        }}>
                            <i className="ri-coin-line" style={{ fontSize: '16px' }}></i>
                            {userChops} Chops
                        </div>
                        {/* {viewportWidth >= 640 && ( */}
                            {/* <div style={{  */}
                                {/* backgroundColor: '#f3f4f6', padding: '8px 16px', borderRadius: '20px', */}
                                {/* fontSize: '14px', fontWeight: '500', color: '#374151' */}
                            {/* }}> */}
                                {/* {alertStats.unattended_count} unattended */}
                            {/* </div> */}
                        {/* )} */}
                    </div>
                </header>

                {/* Summary Cards */}
                <div style={{ 
                    display: 'grid',
                    gridTemplateColumns: viewportWidth >= 1024 ? 'repeat(5, 1fr)' : viewportWidth >= 640 ? 'repeat(2, 1fr)' : '1fr',
                    gap: '16px', marginBottom: '32px'
                }}>
                    {[
                        { label: 'New Alerts', value: alertStats.unattended_count, icon: 'ri-notification-line', bg: '#dbeafe', color: '#3b82f6',sub: undefined },
                        { label: 'Total Chops', value: userChops, icon: 'ri-coin-line', bg: '#fef3c7', color: '#f59e0b', sub: undefined },
                        { label: 'Reading', value: readingChops, icon: 'ri-book-open-line', bg: '#e0e7ff', color: '#6366f1',sub: undefined },
                        { label: 'Sharing', value: sharingChops, icon: 'ri-share-line', bg: '#dcfce7', color: '#16a34a', sub: undefined },
                        // { label: 'Referrals', value: referralCount, icon: 'ri-user-add-line', bg: subscriptionStatus === 'active' ? '#f3e8ff' : '#f3f4f6', color: subscriptionStatus === 'active' ? '#8b5cf6' : '#6b7280', sub: `+${referralChops} Chops` }
                    ].map((card, idx) => (
                        <div key={idx} style={{ backgroundColor: '#ffffff', padding: '20px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>{card.label}</p>
                                    <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>{card.value}</p>
                                    {card.sub && <p style={{ fontSize: '12px', color: '#10b981', margin: '4px 0 0 0', fontWeight: '500' }}>{card.sub}</p>}
                                </div>
                                <div style={{ width: '48px', height: '48px', backgroundColor: card.bg, borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className={card.icon} style={{ color: card.color, fontSize: '20px' }}></i>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Alerts List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '32px' }}>
                    {displayedAlerts.map((alert: Alert) => (
                        <div key={alert.id} style={{ 
                            backgroundColor: '#ffffff', borderRadius: '16px', padding: viewportWidth >= 768 ? '32px' : '20px',
                            boxShadow: alert.is_pinned ?'0 8px 16px -1px rgba(249, 115, 22, 0.3)' : '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                            border: alert.is_pinned ? '2px solid #f97316' : attendedAlerts.has(alert.id) ? '2px solid #10b981' : '1px solid #e5e7eb', position: 'relative'
                        }}>
                            {/* Pin indicator badge */}
                            {alert.is_pinned && (
                                <div style={{ position: 'absolute', top: '16px', right: '16px', backgroundColor: '#fff7ed', color: '#ea580c', padding: '6px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px', boxShadow: '0 2px 4px rgba(249, 115, 22, 0.2)'
                            }}>
                                    <i className="ri-pushpin-fill" style={{ fontSize: '14px' }}></i>
                                    Pinned
                                </div>
                            )}
                            {/* Header */}
                            <div style={{ display: 'flex', flexDirection: viewportWidth >= 768 ? 'row' : 'column', justifyContent: 'space-between', marginBottom: '20px', gap: '16px', paddingRight: alert.is_pinned ? '90px' : '0' }}>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', gap: '12px', marginBottom: '12px', flexWrap: 'wrap' }}>
                                        <span style={{ backgroundColor: getScoreBgColor(alert.score), color: getScoreColor(alert.score), padding: '6px 16px', borderRadius: '20px', fontSize: '14px', fontWeight: '700' }}>
                                            <i className="ri-star-fill" style={{ fontSize: '12px', marginRight: '4px' }}></i>{alert.score}
                                        </span>
                                        <span style={{ backgroundColor: getPriorityBgColor(alert.priority), color: getPriorityColor(alert.priority), padding: '6px 16px', borderRadius: '20px', fontSize: '14px', fontWeight: '600' }}>
                                            {alert.priority}
                                        </span>
                                        <span style={{ backgroundColor: '#f3f4f6', color: '#374151', padding: '6px 16px', borderRadius: '20px', fontSize: '14px', fontWeight: '500' }}>
                                            {alert.category}
                                        </span>
                                    </div>
                                    <h2 style={{ fontSize: viewportWidth >= 768 ? '22px' : '18px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                                        {alert.title}
                                    </h2>
                                </div>
                                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                
                                {attendedAlerts.has(alert.id) && (
                                    <div style={{ backgroundColor: '#dcfce7', color: '#16a34a', padding: '10px 18px', borderRadius: '24px', fontSize: '14px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}>
                                        {/* <i className="ri-check-line"></i>Attended */}
                                    </div>
                                )}
                                {/* Pin Button */}
                                <button 
                    onClick={() => handlePinAlert(alert.id)}
                    style={{ 
                        backgroundColor: alert.is_pinned ? '#fff7ed' : '#f9fafb', padding: '10px', borderRadius: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '44px', height: '44px', transition: 'all 0.2s', fontSize: '18px',
                        color: alert.is_pinned ? '#ea580c' : '#6b7280',
                        border: alert.is_pinned ? '2px solid #f97316' : '1px solid #d1d5db',}}
                    title={alert.is_pinned ? 'Unpin alert' : 'Pin alert to top'}
                >
                    <i className={alert.is_pinned ? 'ri-pushpin-fill' : 'ri-pushpin-line'}></i>
                </button>
                </div>
                            </div>

                            {/* Content */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '20px', marginBottom: '24px' }}>
                                {[
                                    { title: 'Why Act Now', content: alert.why_act_now, bg: '#fef7ff', border: '#e879f9', color: '#a21caf', icon: 'ri-time-line' },
                                    { title: 'Potential Reward', content: alert.potential_reward, bg: '#f0fdf4', border: '#22c55e', color: '#16a34a', icon: 'ri-trophy-line' },
                                    { title: 'Action Required', content: alert.action_required, bg: '#fff7ed', border: '#f97316', color: '#ea580c', icon: 'ri-flashlight-line' }
                                ].map((section, idx) => (
                                    <div key={idx} style={{ backgroundColor: section.bg, padding: '18px', borderRadius: '12px', border: `1px solid ${section.border}`, flex: viewportWidth >= 1024 ? '1 1 calc(33.33% - 20px)' : '1 1 100%',minWidth: viewportWidth >= 1024 ? '270px' : '100%', }}>
                                        <h3 style={{ fontSize: '15px', fontWeight: 'bold', color: section.color, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            <i className={section.icon}></i>{section.title}
                                        </h3>
                                        <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>{section.content}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Buttons */}
                            <div style={{ display: 'flex', flexDirection: viewportWidth >= 640 ? 'row' : 'column', gap: '16px', paddingTop: '24px', borderTop: '1px solid #e5e7eb' }}>
                                <button onClick={() => handleShare(alert)} style={{ flex: 1, backgroundColor: sharedAlerts.has(alert.id.toString()) ? '#f97316' : '#10b981', color: '#fff', padding: '14px 20px', borderRadius: '10px', border: 'none', fontSize: '15px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className={sharedAlerts.has(alert.id.toString()) ? 'ri-check-line' : 'ri-share-line'} style={{ marginRight: '8px' }}></i>
                                    {sharedAlerts.has(alert.id.toString()) ? 'Shared' : `Share (+${isPro ? 10 : 5} Chops)`}
                                </button>
                                <button onClick={() => handleViewDetails(alert)} style={{ flex: 1, backgroundColor: viewedAlerts.has(alert.id.toString()) ? '#f97316' : 'transparent', color: viewedAlerts.has(alert.id.toString()) ? '#fff' : '#6b7280', padding: '14px 20px', borderRadius: '10px', border: viewedAlerts.has(alert.id.toString()) ? 'none' : '2px solid #d1d5db', fontSize: '15px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className={viewedAlerts.has(alert.id.toString()) ? 'ri-check-line' : 'ri-external-link-line'} style={{ marginRight: '8px' }}></i>
                                    {viewedAlerts.has(alert.id.toString()) ? 'Viewed' : `View Details (+${isPro ? 5 : 1} Chops)`}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Pagination for Premium Users */}
                {isPro && totalPages > 1 && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '32px' }}>
                        <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} style={{ padding: '8px 16px', backgroundColor: currentPage === 1 ? '#f3f4f6' : '#fff', color: currentPage === 1 ? '#9ca3af' : '#374151', border: '1px solid #e5e7eb', borderRadius: '8px', cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}>
                            Previous
                        </button>
                        {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                            <button key={page} onClick={() => setCurrentPage(page)} style={{ width: '40px', height: '40px', backgroundColor: currentPage === page ? '#f97316' : '#fff', color: currentPage === page ? '#fff' : '#374151', border: '1px solid #e5e7eb', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}>
                                {page}
                            </button>
                        ))}
                        <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} style={{ padding: '8px 16px', backgroundColor: currentPage === totalPages ? '#f3f4f6' : '#fff', color: currentPage === totalPages ? '#9ca3af' : '#374151', border: '1px solid #e5e7eb', borderRadius: '8px', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}>
                            Next
                        </button>
                    </div>
                )}

                {/* Upgrade Prompt for Free Users */}
                {hasMoreAlerts && (
                    <div style={{ backgroundColor: '#fff', borderRadius: '16px', border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)', overflow: 'hidden', marginBottom: '32px' }}>
                        <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb' }}>
                            <div style={{ display: 'flex', gap: '16px' }}>
                                <div style={{ width: '48px', height: '48px', background: 'linear-gradient(135deg, #fb923c, #ea580c)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-vip-crown-line" style={{ color: '#fff', fontSize: '24px' }}></i>
                                </div>
                                <div>
                                    <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '8px' }}>
                                        {alerts.length - FREE_USER_ALERT_LIMIT} More Pro Opportunities
                                    </h3>
                                    <p style={{ color: '#6b7280', margin: 0 }}>Upgrade to Pro to unlock all alerts</p>
                                </div>
                            </div>
                        </div>
                        <div style={{ padding: '32px', textAlign: 'center' }}>
                            <div style={{ width: '80px', height: '80px', background: 'linear-gradient(135deg, #fb923c, #ea580c)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px' }}>
                                <i className="ri-vip-crown-line" style={{ color: '#fff', fontSize: '40px' }}></i>
                            </div>
                            <h3 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '12px' }}>Unlock Pro Opportunities</h3>
                            <p style={{ color: '#6b7280', marginBottom: '32px' }}>Get 10x more opportunities with Pro</p>
                            <button onClick={() => window.location.href = '/upgrade'} style={{ backgroundColor: '#f97316', color: '#fff', padding: '14px 24px', borderRadius: '10px', border: 'none', fontSize: '16px', fontWeight: '600', cursor: 'pointer', transition: 'background-color 0.3s' }}>
                                Upgrade Now
                            </button>
                        </div>
                    </div>
                )}

                {/* Share Modal & Toast (UNCHANGED) */}
                
                 {showShareModal && selectedAlert && (
                    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                        <div style={{ backgroundColor: '#fff', borderRadius: '12px', padding: '32px', maxWidth: '450px', width: '90%', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}>
                            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '16px', textAlign: 'center' }}>
                                Share Opportunity: <span style={{ color: '#f97316' }}>{selectedAlert.title.substring(0, 30)}...</span>
                            </h3>
                            <p style={{ color: '#6b7280', textAlign: 'center', marginBottom: '24px' }}>
                                Share and earn **+{isPro ? 10 : 5} Chops**!
                            </p>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
                                {[
                                    { name: 'Twitter', platform: 'twitter', icon: 'ri-twitter-x-line', color: '#111827' },
                                    { name: 'Facebook', platform: 'facebook', icon: 'ri-facebook-fill', color: '#1877f2' },
                                    { name: 'LinkedIn', platform: 'linkedin', icon: 'ri-linkedin-fill', color: '#0a66c2' },
                                    { name: 'WhatsApp', platform: 'whatsapp', icon: 'ri-whatsapp-fill', color: '#25d366' },
                                ].map(({ name, platform, icon, color }) => (
                                    <button key={platform} onClick={() => shareToSocialMedia(platform as SocialPlatform)} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', borderRadius: '8px', border: `1px solid ${color}`, backgroundColor: '#fff', color: color, fontSize: '15px', fontWeight: '600', cursor: 'pointer' }}>
                                        <i className={icon} style={{ fontSize: '18px' }}></i> {name}
                                    </button>
                                ))}
                                <button onClick={copyLink} style={{ gridColumn: 'span 2', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '12px', borderRadius: '8px', border: '2px dashed #d1d5db', backgroundColor: '#f9fafb', color: '#4b5563', fontSize: '15px', fontWeight: '600', cursor: 'pointer' }}>
                                    <i className="ri-link"></i> Copy Referral Link
                                </button>
                            </div>
                            <button onClick={() => setShowShareModal(false)} style={{ marginTop: '24px', width: '100%', padding: '12px', borderRadius: '8px', border: 'none', backgroundColor: '#f3f4f6', color: '#4b5563', fontWeight: '600', cursor: 'pointer' }}>
                                Close
                            </button>
                        </div>
                    </div>
                )}
                
                {showToast && (
                    <div style={{ position: 'fixed', bottom: '20px', left: '50%', transform: 'translateX(-50%)', backgroundColor: '#333', color: '#fff', padding: '12px 20px', borderRadius: '8px', fontSize: '14px', zIndex: 1000 }}>
                        {toastMessage}
                    </div>
                )}
            </div>
        </div>
    );
}