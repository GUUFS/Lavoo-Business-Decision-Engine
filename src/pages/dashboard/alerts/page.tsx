import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@/components/base/Button';
import { useCurrentUser, useUserChops, updateChopsAfterAction } from '@/api/user';
import { useOpportunityAlerts } from '@/api/analysis';
import { useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'react-hot-toast';

const API_BASE_URL = 'http://localhost:8000';

export default function AlertsPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [searchTerm, setSearchTerm] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [priorityFilter, setPriorityFilter] = useState('all');
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage] = useState(6);

    const { data: user, isLoading: userLoading } = useCurrentUser();
    const { data: chopsData, invalidateChops } = useUserChops();
    const { data: cachedAlerts = [], isLoading: alertsLoading } = useOpportunityAlerts();

    const mappedAlerts = useMemo(() => {
        return cachedAlerts.map(alert => ({
            ...alert,
            id: alert.id.toString(),
            score: alert.score || 0,
            priority: alert.priority || 'Medium',
            status: alert.attended ? 'Attended' : 'Pending',
            isPinned: false // Pins are handled via the backend
        }));
    }, [cachedAlerts]);

    const filteredAlerts = useMemo(() => {
        return mappedAlerts.filter(alert => {
            const matchesSearch = alert.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                (alert.business_name && alert.business_name.toLowerCase().includes(searchTerm.toLowerCase()));
            const matchesStatus = statusFilter === 'all' || alert.status.toLowerCase() === statusFilter.toLowerCase();
            const matchesPriority = priorityFilter === 'all' || alert.priority.toLowerCase() === priorityFilter.toLowerCase();
            return matchesSearch && matchesStatus && matchesPriority;
        });
    }, [mappedAlerts, searchTerm, statusFilter, priorityFilter]);

    const sortedAlerts = useMemo(() => {
        return [...filteredAlerts].sort((a, b) => {
            if (a.isPinned && !b.isPinned) return -1;
            if (!a.isPinned && b.isPinned) return 1;
            if (a.status === 'Pending' && b.status !== 'Pending') return -1;
            if (a.status !== 'Pending' && b.status === 'Pending') return 1;
            return b.score - a.score;
        });
    }, [filteredAlerts]);

    const totalPages = Math.ceil(sortedAlerts.length / itemsPerPage);
    const displayedAlerts = useMemo(() => {
        const start = (currentPage - 1) * itemsPerPage;
        return sortedAlerts.slice(start, start + itemsPerPage);
    }, [sortedAlerts, currentPage, itemsPerPage]);

    const handlePinAlert = async (alertId: string) => {
        try {
            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/api/alerts/pin`, { alert_id: alertId }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            queryClient.invalidateQueries({ queryKey: ['opportunityAlerts'] });
            toast.success('Alert pinned successfully');
        } catch (error) {
            toast.error('Failed to pin alert');
        }
    };

    const handleViewDetails = async (alert: any) => {
        // Open URL immediately for better UX
        if (alert.alert_url) {
            window.open(alert.alert_url, '_blank');
        }

        try {
            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/api/alerts/view`, { alert_id: alert.id }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            // Re-fetch data to reflect point earnings
            await updateChopsAfterAction(queryClient);
            invalidateChops();
            queryClient.invalidateQueries({ queryKey: ['opportunityAlerts'] });

            toast.success('You earned Chops for viewing this alert!');
        } catch (error) {
            console.error('Error tracking alert view:', error);
        }
    };

    const handleShare = async (alert: any) => {
        const shareUrl = `${window.location.origin}/share/alert/${alert.id}?ref=${user?.referral_code}`;

        try {
            if (navigator.share) {
                await navigator.share({
                    title: alert.title,
                    text: alert.why_act_now,
                    url: shareUrl
                });
            } else {
                await navigator.clipboard.writeText(shareUrl);
                toast.success('Link copied to clipboard!');
            }

            const token = localStorage.getItem('access_token');
            await axios.post(`${API_BASE_URL}/api/alerts/share`, { alert_id: alert.id }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            await updateChopsAfterAction(queryClient);
            invalidateChops();
            toast.success('You earned Chops for sharing!');
        } catch (error) {
            console.error('Error sharing alert:', error);
        }
    };

    if (alertsLoading || userLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen px-4 text-center">
                <i className="ri-lock-line text-6xl text-gray-300 mb-4"></i>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Restricted</h2>
                <p className="text-gray-600 mb-6">Please log in to view opportunity alerts.</p>
                <Button onClick={() => navigate('/login')}>Login</Button>
            </div>
        );
    }

    return (
        <div className="flex-1 p-4 md:p-8 bg-gray-50 min-h-screen">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Opportunity Alerts</h1>
                    <p className="text-gray-600">Actionable insights to grow your business.</p>
                </div>

                {/* Stats Bar */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
                    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                        <p className="text-sm text-gray-500 mb-1">Total Chops</p>
                        <p className="text-2xl font-bold text-orange-600">{chopsData?.total_chops || 0}</p>
                    </div>
                    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                        <p className="text-sm text-gray-500 mb-1">Pending Alerts</p>
                        <p className="text-2xl font-bold text-blue-600">{mappedAlerts.filter(a => a.status === 'Pending').length}</p>
                    </div>
                    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                        <p className="text-sm text-gray-500 mb-1">Subscription</p>
                        <p className="text-2xl font-bold text-green-600">{user?.subscription_status || 'Free'}</p>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex flex-col md:flex-row gap-4 mb-8 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                    <div className="flex-1 relative">
                        <i className="ri-search-line absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"></i>
                        <input
                            type="text"
                            placeholder="Search alerts..."
                            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500/20"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div className="flex gap-4">
                        <select
                            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500/20"
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                        >
                            <option value="all">All Status</option>
                            <option value="pending">Pending</option>
                            <option value="attended">Attended</option>
                        </select>
                        <select
                            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500/20"
                            value={priorityFilter}
                            onChange={(e) => setPriorityFilter(e.target.value)}
                        >
                            <option value="all">All Priority</option>
                            <option value="high">High</option>
                            <option value="medium">Medium</option>
                            <option value="low">Low</option>
                        </select>
                    </div>
                </div>

                {/* Alerts Grid */}
                {displayedAlerts.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
                        {displayedAlerts.map((alert) => (
                            <div key={alert.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-200 overflow-hidden flex flex-col">
                                <div className="p-6 flex-1">
                                    <div className="flex items-start justify-between mb-4">
                                        <div className="flex gap-2">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${alert.priority === 'High' ? 'bg-red-50 text-red-600' :
                                                alert.priority === 'Medium' ? 'bg-orange-50 text-orange-600' :
                                                    'bg-blue-50 text-blue-600'
                                                }`}>
                                                {alert.priority}
                                            </span>
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${alert.status === 'Attended' ? 'bg-green-50 text-green-600' : 'bg-gray-50 text-gray-600'
                                                }`}>
                                                {alert.status}
                                            </span>
                                        </div>
                                        <button onClick={() => handlePinAlert(alert.id)} className="text-gray-400 hover:text-orange-500 transition-colors">
                                            <i className={`ri-pushpin-${alert.isPinned ? 'fill' : 'line'} text-xl`}></i>
                                        </button>
                                    </div>
                                    <h3 className="text-lg font-bold text-gray-900 mb-2 line-clamp-2">{alert.title}</h3>
                                    <p className="text-gray-600 text-sm mb-4 line-clamp-3">{alert.why_act_now}</p>
                                    <div className="flex items-center justify-between text-sm text-gray-500">
                                        <span>Score: {alert.score}</span>
                                        <span>{alert.time_remaining}</span>
                                    </div>
                                </div>
                                <div className="p-4 bg-gray-50 border-t border-gray-100 flex gap-2">
                                    <Button className="flex-1" onClick={() => handleViewDetails(alert)}>View Details</Button>
                                    <Button variant="outline" onClick={() => handleShare(alert)}>
                                        <i className="ri-share-line"></i>
                                    </Button>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-20 bg-white rounded-2xl border border-dashed border-gray-300">
                        <i className="ri-search-eye-line text-6xl text-gray-300 mb-4 block"></i>
                        <h3 className="text-lg font-medium text-gray-900">No alerts found</h3>
                        <p className="text-gray-500">Try adjusting your filters or search term.</p>
                    </div>
                )}

                {/* Pagination */}
                {totalPages > 1 && (
                    <div className="flex justify-center gap-2">
                        {Array.from({ length: totalPages }, (_, i) => (
                            <button
                                key={i + 1}
                                onClick={() => setCurrentPage(i + 1)}
                                className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${currentPage === i + 1 ? 'bg-orange-600 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                {i + 1}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
