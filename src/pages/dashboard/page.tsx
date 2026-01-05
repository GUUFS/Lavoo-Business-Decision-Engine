import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../../components/base/Button';

const API_BASE_URL = 'http://localhost:8000';

// --- AUTHENTICATION HELPERS ---
const getAuthToken = (): string | null => {
    // const userId = localStorage.getItem('user_id');
    const token = localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('auth_token') || localStorage.getItem('authToken');
    if (token) {
        console.log(`✅ AUTH_TOKEN: Token found! Starting with: ${token.slice(0, 15)}...`);
    } else {
        console.warn('❌ AUTH_TOKEN: No token found in localStorage.');
    }
    return token;
};

const getAuthHeaders = (): Record<string, string> => {
    const token = getAuthToken();
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
};

// --- INTERFACES ---
interface Alert {
    id: number;
    title: string;
    category: string;
    priority: 'High' | 'Medium' | 'Low';
    score: number;
    time_remaining: string;
    why_act_now: string;
}

interface Insight {
    id: number;
    title: string;
    category: string;
    what_changed: string;
    why_it_matters: string;
}

interface Review {
    id: number;
    business_name: string;
    rating: number;
    review_text: string;
    date_submitted: string;
}

interface DashboardStats {
    total_revenue: number;
    active_alerts: number;
    new_alerts_today: number;
    total_insights: number;
    new_insights_today: number;
    average_rating: number;
    rating_change: number;
    total_chops: number;
    unattended_alerts: number;
    total_referrals: number;
    referrals_this_month: number;
    referral_chops: number;
    total_commissions: number;
    total_analyses: number;
}

export default function Dashboard() {
    const navigate = useNavigate();

    // State
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<DashboardStats>({
        total_revenue: 0,
        active_alerts: 0,
        new_alerts_today: 0,
        total_insights: 0,
        new_insights_today: 0,
        average_rating: 0,
        rating_change: 0,
        total_chops: 0,
        unattended_alerts: 0,
        total_referrals: 0,
        referrals_this_month: 0,
        referral_chops: 0,
        total_commissions: 0,
        total_analyses: 0
    });
    const [urgentAlerts, setUrgentAlerts] = useState<Alert[]>([]);
    const [topInsights, setTopInsights] = useState<Insight[]>([]);
    const [recentReviews, setRecentReviews] = useState<Review[]>([]);
    // const [userId, setUserId] = useState<number | null>(null);

    // Initialize data on mount
    useEffect(() => {
        initializeDashboard();
    }, []);

    useEffect(() => {
        // Test all API endpoints
        const testEndpoints = async () => {
            const endpoints = [
                '/users/me',
                '/api/alerts?limit=3',
                '/api/insights?page=1&limit=3',
                '/api/reviews',
                '/api/user/stats'
            ];

            for (const endpoint of endpoints) {
                try {
                    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                        headers: getAuthHeaders(),
                        credentials: 'include'
                    });
                    console.log(`🔍 TEST ${endpoint}: ${response.status} ${response.ok ? '✅' : '❌'}`);
                } catch (error: unknown) {
                    // Proper TypeScript error handling
                    if (error instanceof Error) {
                        console.error(`🔍 TEST ${endpoint}: ${error.message}`);
                    } else {
                        console.error(`🔍 TEST ${endpoint}: Unknown error occurred`);
                    }
                }
            }
        };

        testEndpoints();
    }, []);

    const initializeDashboard = async () => {
        setLoading(true);
        try {
            // Get user ID from token
            const token = getAuthToken();
            if (!token) {
                console.error('❌ No authentication token found');
                navigate('/login');
                return;
            }

            // Fetch user data first
            const userResponse = await fetch(`${API_BASE_URL}/users/me`, {
                method: 'GET',
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (!userResponse.ok) {
                throw new Error('Failed to fetch user data');
            }

            const userData = await userResponse.json();
            // setUserId(userData.id);

            // Fetch all dashboard data in parallel
            await Promise.all([
                fetchDashboardStats(userData.id),
                fetchUrgentAlerts(),
                fetchTopInsights(),
                fetchRecentReviews()
            ]);

        } catch (error) {
            console.error('❌ Dashboard initialization error:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchDashboardStats = async (userId: number) => {
        try {
            // Fetch user data for chops
            const userResponse = await fetch(`${API_BASE_URL}/users/me`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });
            if (!userResponse.ok) {
                const text = await userResponse.text();
                console.error(`Request failed: ${API_BASE_URL}/users/me`, userResponse.status, text.slice(0, 200));
                throw new Error(`HTTP ${userResponse.status}`);
            }
            const userData = await userResponse.json();

            // Fetch alert stats
            const alertStatsResponse = await fetch(`${API_BASE_URL}/api/users/${userId}/alerts/stats`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });
            if (!alertStatsResponse.ok) {
                const text = await alertStatsResponse.text();
                console.error(`Request failed: ${API_BASE_URL}/api/users/${userId}/alerts/stats`, alertStatsResponse.status, text.slice(0, 200));
                throw new Error(`HTTP ${alertStatsResponse.status}`);
            }
            const alertStats = await alertStatsResponse.json();

            // Fetch insight stats
            const insightStatsResponse = await fetch(`${API_BASE_URL}/api/user/stats`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });
            if (!insightStatsResponse.ok) {
                const text = await insightStatsResponse.text();
                console.error(`Request failed: ${API_BASE_URL}/api/users/stats`, insightStatsResponse.status, text.slice(0, 200));
                throw new Error(`HTTP ${insightStatsResponse.status}`);
            }
            const insightStats = await insightStatsResponse.json();

            // Fetch referral stats
            const referralStatsResponse = await fetch(`${API_BASE_URL}/api/referrals/stats`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (!referralStatsResponse.ok) {
                const text = await referralStatsResponse.text();
                console.error(`Request failed: ${API_BASE_URL}/api/referrals/stats`, referralStatsResponse.status, text.slice(0, 200));
                throw new Error(`HTTP ${referralStatsResponse.status}`);
            }
            const referralStats = await referralStatsResponse.json();

            // Fetch reviews for average rating
            const reviewsResponse = await fetch(`${API_BASE_URL}/api/reviews`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });
            if (!reviewsResponse.ok) {
                const text = await reviewsResponse.text();
                console.error(`Request failed: ${API_BASE_URL}/api/reviews`, reviewsResponse.status, text.slice(0, 200));
                throw new Error(`HTTP ${reviewsResponse.status}`);
            }
            const reviews = await reviewsResponse.json();

            // Fetch earnings summary for commissions
            const earningsResponse = await fetch(`${API_BASE_URL}/earnings/summary`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });
            let totalCommissions = 0;
            if (earningsResponse.ok) {
                const earningsData = await earningsResponse.json();
                totalCommissions = earningsData.totalCommissions || 0;
            } else {
                console.error('Failed to fetch earnings summary', earningsResponse.status);
            }

            // Calculate average rating
            const averageRating = reviews.length > 0
                ? reviews.reduce((sum: number, r: Review) => sum + r.rating, 0) / reviews.length
                : 0;

            // Mock revenue data (you can add a real endpoint later)
            const totalRevenue = userData.total_chops; // Example: 1 chop = $0.10

            setStats({
                total_revenue: totalRevenue,
                active_alerts: alertStats.attended_count,
                new_alerts_today: alertStats.unattended_count,
                total_insights: insightStats.total_insights,
                new_insights_today: 8, // You can track this with a timestamp query
                average_rating: parseFloat(averageRating.toFixed(1)),
                rating_change: 0.2, // Calculate from historical data if available
                total_chops: userData.total_chops,
                unattended_alerts: alertStats.unattended_count,
                total_referrals: referralStats.total_referrals,
                referrals_this_month: referralStats.referrals_this_month,
                referral_chops: referralStats.total_chops_earned,
                total_commissions: totalCommissions,
                total_analyses: insightStats.total_analyses || 0
            });

            console.log('✅ Dashboard stats loaded');
        } catch (error) {
            console.error('❌ Error fetching dashboard stats:', error);
        }
    };

    const fetchUrgentAlerts = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/alerts?limit=3`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to fetch alerts');

            const alerts = await response.json();

            // ADJUSTED FILTER: Either high priority OR high score
            const urgentOnes = alerts
                .filter((a: Alert) => {
                    // Show alerts that are either High priority OR have score >= 85
                    const isHighPriority = a.priority === 'High';
                    const hasGoodScore = a.score >= 85; // Lowered from 90 to 85
                    return isHighPriority || hasGoodScore;
                })
                .slice(0, 3);

            setUrgentAlerts(urgentOnes);
            console.log('✅ Urgent alerts loaded:', urgentOnes.length);
        } catch (error: unknown) {
            if (error instanceof Error) {
                console.error('❌ Error fetching urgent alerts:', error.message);
            }
        }
    };

    const fetchTopInsights = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/insights?page=1&limit=3`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to fetch insights');

            const data = await response.json();
            setTopInsights(data.insights.slice(0, 3));
            console.log('✅ Top insights loaded:', data.insights.length);
        } catch (error) {
            console.error('❌ Error fetching insights:', error);
        }
    };

    const fetchRecentReviews = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/reviews`, {
                headers: getAuthHeaders(),
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Failed to fetch reviews');

            const reviews = await response.json();
            setRecentReviews(reviews.slice(0, 3));
            console.log('✅ Recent reviews loaded:', reviews.length);
        } catch (error) {
            console.error('❌ Error fetching reviews:', error);
        }
    };

    const formatTimeAgo = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

        if (diffInHours < 1) return 'Just now';
        if (diffInHours < 24) return `${diffInHours} hours ago`;
        const diffInDays = Math.floor(diffInHours / 24);
        if (diffInDays === 1) return '1 day ago';
        return `${diffInDays} days ago`;
    };

    // Loading state
    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center min-h-screen bg-gradient-to-br from-orange-50 to-white">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-orange-200 border-t-orange-600 rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
            <div className="flex-1 p-4 md:p-6 lg:p-8">
                {/* Header */}
                <div className="mb-6 md:mb-8">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
                        <div className="flex-1">
                            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 mb-2">
                                Welcome to Lavoo
                            </h1>
                            <p className="text-gray-600 text-sm md:text-base">
                                Get a complete overview of your business performance and access all tools from here.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Quick Stats */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 md:mb-8">
                    {/* Total Analyses */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">Total Analyses</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats.total_analyses}</p>
                            </div>
                            <div className="w-10 h-10 md:w-12 md:h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                                <i className="ri-bar-chart-line text-green-600 text-lg md:text-xl"></i>
                            </div>
                        </div>
                    </div>

                    {/* Active Alerts */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">Active Alerts</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats.unattended_alerts}</p>
                            </div>
                            <div className="w-10 h-10 md:w-12 md:h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                                <i className="ri-alert-line text-orange-600 text-lg md:text-xl"></i>
                            </div>
                        </div>
                        <div className="mt-3 flex items-center">
                            {/* <i className="ri-arrow-up-line text-orange-500 text-sm"></i> */}
                            {/* <span className="text-orange-500 text-sm font-medium ml-1">{stats.unattended_alerts} new</span> */}
                            {/* <span className="text-gray-500 text-sm ml-2">unattended</span> */}
                        </div>
                    </div>

                    {/* AI Analyst - COMMENTED OUT
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">AI Analyst</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats.total_insights}</p>
                            </div>
                            <div className="w-10 h-10 md:w-12 md:h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                                <i className="ri-search-line text-purple-600 text-lg md:text-xl"></i>
                            </div>
                        </div>
                        <div className="mt-3 flex items-center">
                        </div>
                    </div>
                    */}

                    {/* Average Rating */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">Avg Rating</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats.average_rating || 'N/A'}</p>
                            </div>
                            <div className="w-10 h-10 md:w-12 md:h-12 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                                <i className="ri-star-line text-yellow-600 text-lg md:text-xl"></i>
                            </div>
                        </div>
                        <div className="mt-3 flex items-center">
                            {/* <i className="ri-arrow-up-line text-yellow-500 text-sm"></i> */}
                            {/* <span className="text-yellow-500 text-sm font-medium ml-1">+{stats.rating_change}</span> */}
                            {/* <span className="text-gray-500 text-sm ml-2">this month</span> */}
                        </div>
                    </div>
                </div>

                {/* Dashboard Sections */}
                <div className="space-y-6 md:space-y-8">
                    {/* AI Analyst */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="p-4 md:p-6 border-b border-gray-200">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                                <div className="flex items-center space-x-3">
                                    <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                        <i className="ri-search-line text-purple-600"></i>
                                    </div>
                                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">AI Analyst</h3>
                                </div>
                                <Button
                                    onClick={() => navigate('/dashboard/analyze')}
                                    variant="outline"
                                    size="sm"
                                    className="whitespace-nowrap self-start sm:self-auto"
                                >
                                    View All <i className="ri-arrow-right-line ml-1"></i>
                                </Button>
                            </div>
                        </div>
                        <div className="p-4 md:p-6">
                            {topInsights.length > 0 ? (
                                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
                                    {topInsights.map((insight) => (
                                        <div key={insight.id} className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-purple-200 hover:bg-purple-50/30 transition-all duration-200 cursor-pointer"
                                            onClick={() => navigate('/dashboard/insights')}>
                                            <div className="flex items-center justify-between mb-3">
                                                <span className="text-xs px-2 py-1 rounded-full font-medium bg-purple-100 text-purple-600">
                                                    Analysis Result
                                                </span>
                                            </div>
                                            <h4 className="font-medium text-gray-900 mb-2 text-sm md:text-base">
                                                {insight.title.includes('OpenAI') || insight.title.includes('Tech Briefing') ?
                                                    (insight.title.includes('OpenAI') ? 'Revenue Anomaly Detected' : 'Predictive Growth Index') :
                                                    insight.title}
                                            </h4>
                                            <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">
                                                {insight.why_it_matters.includes('business owners') || insight.why_it_matters.includes('operators') ?
                                                    'Engine identified a 15% discrepancy in conversion rates between mobile and desktop segments.' :
                                                    insight.why_it_matters}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-center text-gray-500 py-8">No insights available</p>
                            )}
                        </div>
                    </div>

                    {/* Opportunity Alerts */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="p-4 md:p-6 border-b border-gray-200">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                                <div className="flex items-center space-x-3">
                                    <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                        <i className="ri-alert-line text-orange-600"></i>
                                    </div>
                                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">Opportunity Alerts</h3>
                                </div>
                                <Button
                                    onClick={() => navigate('/dashboard/alerts')}
                                    variant="outline"
                                    size="sm"
                                    className="whitespace-nowrap self-start sm:self-auto"
                                >
                                    View All <i className="ri-arrow-right-line ml-1"></i>
                                </Button>
                            </div>
                        </div>
                        <div className="p-4 md:p-6">
                            {urgentAlerts.length > 0 ? (
                                <div className="space-y-4">
                                    {urgentAlerts.map((alert) => (
                                        <div key={alert.id} className="border border-gray-200 rounded-lg p-4 md:p-6 hover:border-orange-200 hover:bg-orange-50/30 transition-all duration-200 cursor-pointer"
                                            onClick={() => navigate('/dashboard/alerts')}>
                                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between space-y-3 sm:space-y-0 mb-3">
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                                                        <i className="ri-fire-line text-red-600 text-sm"></i>
                                                    </div>
                                                    <span className="text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full font-medium">
                                                        {alert.priority.toLowerCase()}
                                                    </span>
                                                </div>
                                                <div className="text-left sm:text-right">
                                                    <div className="text-sm font-medium text-gray-900">Score: {alert.score}</div>
                                                    <div className="text-xs text-gray-500">{alert.time_remaining}</div>
                                                </div>
                                            </div>
                                            <h4 className="font-medium text-gray-900 mb-2 text-sm md:text-base">{alert.title}</h4>
                                            <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">{alert.why_act_now}</p>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-center text-gray-500 py-8">No urgent alerts at the moment</p>
                            )}
                        </div>
                    </div>

                    {/* Earnings & Referrals */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="p-4 md:p-6 border-b border-gray-200">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                                <div className="flex items-center space-x-3">
                                    <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                        <i className="ri-money-dollar-circle-line text-green-600"></i>
                                    </div>
                                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">Earnings Overview</h3>
                                </div>
                                <Button
                                    onClick={() => navigate('/dashboard/earnings')}
                                    variant="outline"
                                    size="sm"
                                    className="whitespace-nowrap self-start sm:self-auto"
                                >
                                    View All <i className="ri-arrow-right-line ml-1"></i>
                                </Button>
                            </div>
                        </div>
                        <div className="p-4 md:p-6">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 md:gap-6">
                                {/* Total Chops - COMMENTED OUT
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-green-200 hover:bg-green-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Total Chops</h4>
                                        <i className="ri-coin-line text-green-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{stats.total_chops}</div>
                                    <div className="text-sm text-gray-500">All-time earnings</div>
                                </div>
                                */}

                                {/* Referral Chops */}
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-purple-200 hover:bg-purple-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Affiliate Commissions</h4>
                                        <i className="ri-money-dollar-circle-line text-purple-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">${stats.total_commissions.toLocaleString()}</div>
                                    <div className="text-sm text-gray-500">Total earned</div>
                                </div>

                                {/* Chops Earned - COMMENTED OUT
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-purple-200 hover:bg-purple-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Chops Earned</h4>
                                        <i className="ri-user-add-line text-purple-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{stats.referral_chops}</div>
                                    <div className="text-sm text-gray-500">From referrals</div>
                                </div>
                                */}

                                {/* Total Referrals */}
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-blue-200 hover:bg-blue-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Total Referrals</h4>
                                        <i className="ri-group-line text-blue-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{stats.total_referrals}</div>
                                    <div className="text-sm text-green-500 font-medium">
                                        {stats.referrals_this_month > 0 && `+${stats.referrals_this_month} this month`}
                                        {stats.referrals_this_month === 0 && 'Start referring!'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    {recentReviews.length > 0 && (
                        <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                            <div className="p-4 md:p-6 border-b border-gray-200">
                                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                                    <div className="flex items-center space-x-3">
                                        <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                            <i className="ri-star-line text-yellow-600"></i>
                                        </div>
                                        <h3 className="text-lg md:text-xl font-semibold text-gray-900">Recent Reviews</h3>
                                    </div>
                                    <Button
                                        onClick={() => navigate('/dashboard/reviews')}
                                        variant="outline"
                                        size="sm"
                                        className="whitespace-nowrap self-start sm:self-auto"
                                    >
                                        View All <i className="ri-arrow-right-line ml-1"></i>
                                    </Button>
                                </div>
                            </div>
                            <div className="p-4 md:p-6">
                                <div className="space-y-4">
                                    {recentReviews.map((review) => (
                                        <div key={review.id} className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-yellow-200 hover:bg-yellow-50/30 transition-all duration-200">
                                            <div className="flex items-start justify-between mb-2">
                                                <h4 className="font-medium text-gray-900">{review.business_name}</h4>
                                                <div className="flex items-center">
                                                    {[...Array(5)].map((_, i) => (
                                                        <i key={i} className={`ri-star-${i < review.rating ? 'fill' : 'line'} text-yellow-500 text-sm`}></i>
                                                    ))}
                                                </div>
                                            </div>
                                            <p className="text-sm text-gray-600 mb-2 line-clamp-2">{review.review_text}</p>
                                            <p className="text-xs text-gray-500">{formatTimeAgo(review.date_submitted)}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}