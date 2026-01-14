
import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import DashboardSidebar from '../../../../components/feature/DashboardSidebar';
import axios from 'axios';
import { toast } from 'react-toastify';

const API_BASE_URL = '/api';

interface Alert {
    id: number;
    title: string;
    category: string;
    priority: string;
    created_at: string;
    score: number;
    why_act_now: string;
    what_changed: string;
    action_required: string;
    potential_reward: string;
    time_remaining: string;
    alert_url: string;
    business_name?: string;
}

export default function AlertDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [alert, setAlert] = useState<Alert | null>(null);
    const [loading, setLoading] = useState(true);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const [is404, setIs404] = useState(false);

    useEffect(() => {
        const fetchAlert = async () => {
            try {
                const token = localStorage.getItem('access_token');
                const response = await axios.get(`${API_BASE_URL}/alerts/${id}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (response.data) {
                    // If error=404 is passed or alert_url is missing, show 404 as requested
                    if (searchParams.get('error') === '404' || !response.data.alert_url) {
                        setIs404(true);
                    } else {
                        setAlert(response.data);
                    }
                } else {
                    setIs404(true);
                }
            } catch (error: any) {
                console.error('Error fetching alert:', error);
                if (error.response?.status === 404) {
                    setIs404(true);
                } else {
                    toast.error('Failed to load alert details');
                }
            } finally {
                setLoading(false);
            }
        };

        if (id) {
            fetchAlert();
        }
    }, [id]);

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    if (is404 || !alert) {
        return (
            <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex' }}>
                <DashboardSidebar
                    isMobileMenuOpen={isMobileMenuOpen}
                    setIsMobileMenuOpen={setIsMobileMenuOpen}
                />
                <div className="flex-1 flex flex-col items-center justify-center p-4">
                    <div className="text-center">
                        <div className="text-9xl font-black text-gray-200 mb-4">404</div>
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">Alert Not Found</h1>
                        <p className="text-gray-600 mb-8">The alert you're looking for doesn't exist or has been removed.</p>
                        <button
                            onClick={() => navigate('/dashboard/alerts')}
                            className="bg-orange-500 text-white px-8 py-3 rounded-lg font-bold hover:bg-orange-600 transition-all shadow-lg"
                        >
                            Back to Alerts
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const getPriorityColor = (priority: string) => {
        if (priority?.toLowerCase().includes('high')) return '#ef4444';
        if (priority?.toLowerCase().includes('medium')) return '#f97316';
        return '#3b82f6';
    };

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex' }}>
            <DashboardSidebar
                isMobileMenuOpen={isMobileMenuOpen}
                setIsMobileMenuOpen={setIsMobileMenuOpen}
            />

            <div className="flex-1 flex flex-col min-h-screen bg-gradient-to-br from-orange-50 to-white">
                <header className="bg-white border-b border-gray-200 p-6 flex items-center justify-between sticky top-0 z-10 shadow-sm">
                    <div className="flex items-center gap-4">
                        <button onClick={() => navigate('/dashboard/alerts')} className="text-gray-500 hover:text-gray-900 transition-colors">
                            <i className="ri-arrow-left-line text-xl"></i>
                        </button>
                        <h1 className="text-xl font-bold text-gray-900">Alert Details</h1>
                    </div>
                    {alert.alert_url && (
                        <button
                            onClick={() => window.open(alert.alert_url, '_blank')}
                            className="bg-orange-500 text-white px-6 py-2 rounded-lg font-bold hover:bg-orange-600 transition-all shadow-md flex items-center gap-2"
                        >
                            <i className="ri-external-link-line"></i>
                            Visit Link
                        </button>
                    )}
                </header>

                <main className="flex-1 p-6 md:p-12 max-w-4xl mx-auto w-full">
                    <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100 mb-8">
                        <div className="h-2 w-full" style={{ backgroundColor: getPriorityColor(alert.priority) }}></div>
                        <div className="p-8 md:p-12">
                            <div className="flex flex-wrap items-center gap-4 mb-8">
                                <span className="bg-orange-100 text-orange-700 px-4 py-1.5 rounded-full text-sm font-black uppercase tracking-wider">
                                    Score: {alert.score}
                                </span>
                                <span className="bg-gray-100 text-gray-700 px-4 py-1.5 rounded-full text-sm font-bold">
                                    {alert.category}
                                </span>
                                <span className="text-xs text-gray-400 font-bold uppercase tracking-widest">
                                    {new Date(alert.created_at).toLocaleDateString()}
                                </span>
                            </div>

                            <h2 className="text-3xl md:text-4xl font-black text-gray-900 mb-10 leading-tight">
                                {alert.title}
                            </h2>

                            <div className="space-y-12">
                                <section>
                                    <div className="flex items-center gap-3 text-orange-600 font-bold uppercase tracking-[0.2em] text-xs mb-4">
                                        <i className="ri-error-warning-line text-lg"></i>
                                        Why Act Now
                                    </div>
                                    <p className="text-gray-700 leading-relaxed text-lg font-medium">
                                        {alert.why_act_now}
                                    </p>
                                </section>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-12 pt-8 border-t border-gray-100">
                                    <section>
                                        <div className="flex items-center gap-3 text-purple-600 font-bold uppercase tracking-[0.2em] text-xs mb-4">
                                            <i className="ri-trophy-line text-lg"></i>
                                            Potential Reward
                                        </div>
                                        <p className="text-gray-600 leading-relaxed">
                                            {alert.potential_reward}
                                        </p>
                                    </section>

                                    <section>
                                        <div className="flex items-center gap-3 text-green-600 font-bold uppercase tracking-[0.2em] text-xs mb-4">
                                            <i className="ri-flashlight-line text-lg"></i>
                                            Action Required
                                        </div>
                                        <p className="text-gray-600 leading-relaxed">
                                            {alert.action_required}
                                        </p>
                                    </section>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white border border-gray-200 rounded-2xl p-8 shadow-sm flex items-center justify-between">
                        <div>
                            <h4 className="font-bold text-gray-900 mb-1">Found something interesting?</h4>
                            <p className="text-sm text-gray-500">Share this alert with your colleagues or on social media.</p>
                        </div>
                        <button className="bg-gray-100 text-gray-700 px-6 py-2.5 rounded-xl font-bold hover:bg-gray-200 transition-all flex items-center gap-2">
                            <i className="ri-share-line"></i>
                            Share
                        </button>
                    </div>
                </main>
            </div>
        </div>
    );
}
