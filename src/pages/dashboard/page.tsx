import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../../components/base/Button';
import { useCurrentUser } from '../../api/user';
import {
    useDashboardStats,
    useUrgentAlerts,
    useTopInsights,
    useRecentReviews,
    type Alert,
    type Insight,
    type Review,
    type DashboardStats,
} from '../../api/dashboard';

const API_BASE_URL = 'http://localhost:8000';

// --- AUTHENTICATION HELPERS ---
const getAuthToken = (): string | null => {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('authToken');
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

export default function Dashboard() {
    const navigate = useNavigate();

    // Use TanStack Query hooks for all data fetching with caching
    const { data: currentUser, isLoading: isLoadingUser } = useCurrentUser();
    const userId = currentUser?.id || null;

    const { data: stats, isLoading: isLoadingStats } = useDashboardStats(userId);
    const { data: urgentAlerts = [], isLoading: isLoadingAlerts } = useUrgentAlerts(userId);
    const { data: topInsights = [], isLoading: isLoadingInsights } = useTopInsights();
    const { data: recentReviews = [], isLoading: isLoadingReviews } = useRecentReviews();

    // Combined loading state
    const loading = isLoadingUser || isLoadingStats || isLoadingAlerts || isLoadingInsights || isLoadingReviews;

    // Redirect to login if no user
    useEffect(() => {
        if (!isLoadingUser && !currentUser) {
            console.error('❌ No user found, redirecting to login');
            navigate('/login');
        }
    }, [currentUser, isLoadingUser, navigate]);

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
                    {/* Total Revenue */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">Total Chops</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats?.total_chops || 0}</p>
                            </div>
                            <div className="w-10 h-10 md:w-12 md:h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                                <i className="ri-coin-line text-green-600 text-lg md:text-xl"></i>
                            </div>
                        </div>
                        <div className="mt-3 flex items-center">
                            {/* <i className="ri-arrow-up-line text-green-500 text-sm"></i> */}
                            {/* <span className="text-green-500 text-sm font-medium ml-1">+12.5%</span> */}
                            {/* <span className="text-gray-500 text-sm ml-2">vs last month</span> */}
                        </div>
                    </div>

                    {/* Active Alerts */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">Active Alerts</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats?.unattended_alerts || 0}</p>
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

                    {/* AI Insights */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">AI Insights</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats?.total_insights || 0}</p>
                            </div>
                            <div className="w-10 h-10 md:w-12 md:h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                                <i className="ri-brain-line text-purple-600 text-lg md:text-xl"></i>
                            </div>
                        </div>
                        <div className="mt-3 flex items-center">
                            {/* <i className="ri-arrow-up-line text-purple-500 text-sm"></i> */}
                            {/* <span className="text-purple-500 text-sm font-medium ml-1">+{stats.new_insights_today} today</span> */}
                            {/* <span className="text-gray-500 text-sm ml-2">this week</span> */}
                        </div>
                    </div>

                    {/* Average Rating */}
                    <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="flex items-center justify-between">
                            <div className="flex-1">
                                <p className="text-sm text-gray-600 mb-1">Avg Rating</p>
                                <p className="text-xl md:text-2xl font-bold text-gray-900">{stats?.average_rating || 'N/A'}</p>
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
                    {/* AI Insights */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                        <div className="p-4 md:p-6 border-b border-gray-200">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                                <div className="flex items-center space-x-3">
                                    <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                        <i className="ri-brain-line text-purple-600"></i>
                                    </div>
                                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">AI Insights</h3>
                                </div>
                                <Button
                                    onClick={() => navigate('/dashboard/insights')}
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
                                                    {insight.category}
                                                </span>
                                            </div>
                                            <h4 className="font-medium text-gray-900 mb-2 text-sm md:text-base">{insight.title}</h4>
                                            <p className="text-sm text-gray-600 leading-relaxed line-clamp-2">{insight.why_it_matters}</p>
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
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
                                {/* Total Chops */}
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-green-200 hover:bg-green-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Total Chops</h4>
                                        <i className="ri-coin-line text-green-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{stats?.total_chops || 0}</div>
                                    <div className="text-sm text-gray-500">All-time earnings</div>
                                </div>

                                {/* Referral Chops */}
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-purple-200 hover:bg-purple-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Affiliate Commissions</h4>
                                        <i className="ri-user-add-line text-purple-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">$0</div>
                                    <div className="text-sm text-gray-500"></div>
                                </div>

                                {/* Referral Chops */}
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-purple-200 hover:bg-purple-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Chops Earned</h4>
                                        <i className="ri-user-add-line text-purple-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{stats?.referral_chops || 0}</div>
                                    <div className="text-sm text-gray-500">From referrals</div>
                                </div>

                                {/* Total Referrals */}
                                <div className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-blue-200 hover:bg-blue-50/30 transition-all duration-200">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-medium text-gray-900 text-sm md:text-base">Total Referrals</h4>
                                        <i className="ri-group-line text-blue-600 text-xl"></i>
                                    </div>
                                    <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{stats?.total_referrals || 0}</div>
                                    <div className="text-sm text-green-500 font-medium">
                                        {(stats?.referrals_this_month || 0) > 0 && `+${stats?.referrals_this_month} this month`}
                                        {(stats?.referrals_this_month || 0) === 0 && 'Start referring!'}
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
