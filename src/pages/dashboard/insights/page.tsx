import { useState, useEffect, useRef } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import axios from 'axios';
import { useCurrentUser  } from '../../../api/user';
import { useAIInsights } from '../../../api/analysis';

const API_BASE_URL = '/api';

interface Insight {
  id: number;
  title: string;
  category: string;
  read_time: string;
  date: string;
  source: string;
  url: string;
  what_changed: string;
  why_it_matters: string;
  action_to_take: string;
  is_read: boolean;
  is_shared: boolean;
  is_pinned: boolean;
}

interface UserStats {
  total_insights: number;
  total_chops: number;
  is_pro: boolean;
  total_insight_chops: number;
  // read_today: number;
  // shared_count: number;
  shared_insight_chops: number;
  viewed_insight_chops: number;
}

const FREE_USER_LIMIT = 3;

export default function DashboardInsights() {
  const { data: user } = useCurrentUser();
  const referral_code = user?.referral_code || ' ';

  // TanStack Query hook for cached insights
  const [currentPage, setCurrentPage] = useState(1);
  const {
    data: cachedInsightsData,
    isLoading: insightsLoading,
    isFetching: insightsFetching
  } = useAIInsights(currentPage, 5);

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [displayInsights, setDisplayInsights] = useState<Insight[]>([]);
  const [userStats, setUserStats] = useState<UserStats>({
    total_chops: 0,
    is_pro: false,
    total_insight_chops: 0,
    total_insights: 0,
    // read_today: 0,
    // shared_count: 0
    shared_insight_chops: 0,
    viewed_insight_chops: 0
  });
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);
  const [visibleInsights, setVisibleInsights] = useState<Set<number>>(new Set());
  const [readingTimers, setReadingTimers] = useState<Record<number, NodeJS.Timeout>>({});

  const insightRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Sync cached insights data to local state
  useEffect(() => {
    if (cachedInsightsData && !insightsLoading) {
      const insightsData = cachedInsightsData.insights || [];
      const isProUser = cachedInsightsData.is_pro || false;

      const insightsToDisplay = isProUser
        ? insightsData
        : insightsData.slice(0, FREE_USER_LIMIT);

      setDisplayInsights(insightsToDisplay);
      setInsights(insightsData);
      setTotalPages(cachedInsightsData.total_pages || 1);
      setUserStats(prev => ({
        ...prev,
        is_pro: cachedInsightsData.is_pro || false,
        total_insights: cachedInsightsData.total_insights || 0
      }));
      setLoading(false);

      console.log('✅ CACHE_SYNC: Insights synced from cache.');
    }
  }, [cachedInsightsData, insightsLoading]);


  // Fetch insights from backend - used as fallback
  const fetchInsights = async (page: number = 1) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/insights`, {
        params: { page, limit: 5 },
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}` // Add your auth token
        }
      });

      console.log('API Response:', response.data); // Debug log

      // Ensure insights is always an array
      const insightsData = response.data.insights || [];
      const isProUser = response.data.is_pro || false;

      const insightsToDisplay = isProUser
        ? insightsData
        : insightsData.slice(0, FREE_USER_LIMIT);

      setDisplayInsights(insightsToDisplay)
      setInsights(insightsData);
      setCurrentPage(response.data.current_page || 1);
      setTotalPages(response.data.total_pages || 1);
      setUserStats(prev => ({
        ...prev,
        is_pro: response.data.is_pro || false,
        total_insights: response.data.total_insights || 0
      }));
    } catch (error: any) {
      console.error('Error fetching insights:', error);
      console.error('Error response:', error.response?.data);
      showToastMessage('Error loading insights: ' + (error.response?.data?.detail || error.message));
      // Set empty array to prevent undefined error
      setInsights([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch user stats
  const fetchUserStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/user/stats`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      setUserStats(response.data);
    } catch (error) {
      console.error('Error fetching user stats:', error);
    }
  };

  // Mark insight as read
  const markAsRead = async (insightId: number) => {
    if (!user?.id) {
      console.error("User ID not available");
      return;
    }

    try {
      const response = await axios.post(
        `${API_BASE_URL}/insights/view`,
        {
          user_id: user.id,      // ← ADD THIS
          insight_id: insightId
        },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
    );

    if (response.data.chops_earned > 0) {
      // Update both insights and displayInsights
      setInsights(prev =>
        prev.map(insight =>
          insight.id === insightId ? { ...insight, is_read: true } : insight
        )
      );

      setDisplayInsights(prev =>
        prev.map(insight =>
          insight.id === insightId ? { ...insight, is_read: true } : insight
        )
      );

      setUserStats(prev => ({
        ...prev,
        total_chops: response.data.total_chops ?? prev.total_chops,
        viewed_insight_chops: response.data.insight_reading_chops ?? prev.viewed_insight_chops,
        shared_insight_chops: response.data.insight_sharing_chops ?? prev.shared_insight_chops,
        total_insight_chops: response.data.total_insight_chops ?? prev.total_insight_chops,
      }));

      showToastMessage(
        `You earned ${response.data.chops_earned} chop${response.data.chops_earned > 1 ? 's' : ''} for reading this insight!`
      );
    } else {
      // Even if no chops earned (already read), update the UI state
      setInsights(prev =>
        prev.map(insight =>
          insight.id === insightId ? { ...insight, is_read: true } : insight
        )
      );

      setDisplayInsights(prev =>
        prev.map(insight =>
          insight.id === insightId ? { ...insight, is_read: true } : insight
        )
      );
    }
  } catch (error: any) {
    console.error('Error marking as read:', error);
    console.error('Error response:', error.response?.data);
  }
};

  // Share insight
  const shareInsight = async (insightId: number, platform: string) => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/insights/share`,
        { insight_id: insightId, platform, user_id: user.id },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );

      if (response.data.chops_earned > 0) {
        // Update local state
        const updatedInsight = {
        ...insights.find(insight => insight.id === insightId),
        is_shared: true
      } as Insight;

        setInsights(prev =>
          prev.map(insight =>
            insight.id === insightId ? { ...insight, is_shared: true } : insight
          )
        );

        setDisplayInsights(prev =>
          prev.map(insight =>
            insight.id === insightId ? { ...insight, is_shared: true} : insight )
          );

        setUserStats(prev => ({
          ...prev,
          total_chops: response.data.total_chops,
          shared_insight_chops: response.data.insight_sharing_chops,
          viewed_insight_chops: response.data.insight_reading_chops,
          total_insight_chops: response.data.total_insight_chops
        }));

        showToastMessage(
          `You earned ${response.data.chops_earned} chops for sharing this insight!`
        );
      }
    } catch (error: any) {
      console.error('Error sharing insight:', error);
      console.error('Error response:', error.response?.data);
    }
  };

  // Pin/Unpin insight
  const togglePin = async (insightId: number) => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/insights/pin`,
        { insight_id: insightId },
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );

      // Update local state
      setInsights(prev =>
        prev.map(insight =>
          insight.id === insightId ? { ...insight, is_pinned: response.data.is_pinned } : insight
        )
      );

      showToastMessage(response.data.message);

      // Refresh to reorder pinned items
      fetchInsights(currentPage);
    } catch (error) {
      console.error('Error toggling pin:', error);
    }
  };


  useEffect(() => {
    if (loading || displayInsights.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const insightId = parseInt(entry.target.getAttribute('data-insight-id') || '0', 10);
          const insight = insights.find(i => i.id === insightId);
          if (!insight || insight.is_read) return;

          if (entry.isIntersecting && entry.intersectionRatio >= 0.8) {
            setVisibleInsights(prev => new Set(prev).add(insightId));

            if (!readingTimers[insightId]) {
              const timer = setTimeout(() => {
                markAsRead(insightId);
                setReadingTimers(prev => {
                  const newTimers = { ...prev };
                  delete newTimers[insightId];
                  return newTimers;
                });
              }, 10000);

              setReadingTimers(prev => ({ ...prev, [insightId]: timer }));
            }
          } else {
            setVisibleInsights(prev => {
              const newSet = new Set(prev);
              newSet.delete(insightId);
              return newSet;
            });

            if (readingTimers[insightId]) {
              clearTimeout(readingTimers[insightId]);
              setReadingTimers(prev => {
                const newTimers = { ...prev };
                delete newTimers[insightId];
                return newTimers;
              });
            }
          }
        });
      },
      {
        threshold: [0, 0.5, 0.8, 1.0],
        rootMargin: '0px 0px -100px 0px', // Optional: trigger a bit earlier
      }
    );

    const insightsToObserve = displayInsights.map(i => insightRefs.current[i.id]).filter(Boolean) as HTMLDivElement[];
    insightsToObserve.forEach(el => {
      if (el) observer.observe(el);
    });

    // Observe all CURRENTLY rendered insight elements
    const currentElements = Object.values(insightRefs.current).filter(Boolean);
    currentElements.forEach(el => {
      if (el) observer.observe(el);
    });

    // Save observer for cleanup
    observerRef.current = observer;

    // Cleanup: unobserve all + clear timers
    return () => {
      insightsToObserve.forEach(el => {
        if (el) observer.unobserve(el);
      });
      // currentElements.forEach(el => {
        // if (el) observer.unobserve(el);
      //  });
      Object.values(readingTimers).forEach(clearTimeout);
    };
  }, [displayInsights, insights, readingTimers]); // Critical: re-run when insights change

  useEffect(() => {
    return () => {
      Object.values(readingTimers).forEach(clearTimeout);
      setReadingTimers({});
    };
  }, []);

  // Initial load
  useEffect(() => {
    fetchInsights(1);
    fetchUserStats();
  }, []);

  const showToastMessage = (message: string) => {
    setToastMessage(message);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const handleShare = (insight: Insight) => {
    setSelectedInsight(insight);
    setShowShareModal(true);
  };

  type Platform = 'twitter' | 'facebook' | 'linkedin' | 'whatsapp';

  const shareToSocialMedia = async (platform: Platform) => {
    if (!selectedInsight) return;
    const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(referral_code)}`;
    const insightUrl = `${referralLink}&insight=${selectedInsight.id}`;
    const text = `Check out this business insight: ${selectedInsight.title}`;

    let shareUrl = '';

    switch (platform) {
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(insightUrl)}`;
        break;
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(insightUrl)}`;
        break;
      case 'linkedin':
        shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(insightUrl)}`;
        break;
      case 'whatsapp':
        shareUrl = `https://wa.me/?text=${encodeURIComponent(text + ' ' + insightUrl)}`;
        break;
    }

    if (shareUrl) {
      window.open(shareUrl, '_blank');
      await shareInsight(selectedInsight.id, platform);
    }

    setShowShareModal(false);
  };

  const copyLink = async () => {
    if (!selectedInsight) return;
    const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(referral_code)}`;
    const insightUrl = `${referralLink}&insight=${selectedInsight.id}`;

    await navigator.clipboard.writeText(insightUrl);
    await shareInsight(selectedInsight.id, 'copy_link');

    setShowShareModal(false);
  };

  const getReadingStatus = (insight: Insight) => {
    if (insight.is_read) return 'read';
    if (readingTimers[insight.id]) return 'reading';
    return 'unread';
  };

  const getButtonText = (insight: Insight) => {
    const status = getReadingStatus(insight);
    const chops = userStats.is_pro ? 5 : 1;

    switch (status) {
      case 'read':
        return 'Insight Read';
      case 'reading':
        return `Reading... (+${chops} chop${chops > 1 ? 's' : ''} in 10s)`;
      case 'unread':
        return 'Scroll to Read';
    }
  };

  const getButtonStyle = (insight: Insight) => {
    const status = getReadingStatus(insight);
    const baseStyle = {padding: '12px 20px', borderRadius: '8px', border: 'none', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.3s ease', minWidth: '200px', whiteSpace: 'nowrap' as const
 };

    switch (status) {
      case 'read':
        return { ...baseStyle, backgroundColor: '#f97316', color: '#ffffff' };
      case 'reading':
        return { ...baseStyle, backgroundColor: '#d68306ff', color: '#ffffff' };
      case 'unread':
        return { ...baseStyle, backgroundColor: '#e5e7eb', color: '#9ca3af', cursor: 'default' };
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex' }}>
      <DashboardSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      <div style={{ flex: 1, marginLeft: '0', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <header style={{ backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button
              style={{
                display: window.innerWidth >= 768 ? 'none' : 'flex', alignItems: 'center', justifyContent: 'center', width: '40px', height: '40px', backgroundColor: 'transparent', border: 'none', borderRadius: '6px', color: '#6b7280', cursor: 'pointer', marginRight: '16px' }}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <i className="ri-menu-line" style={{ fontSize: '20px' }}></i>
            </button>
            <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
              AI Insights Feed
            </h1>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {userStats.is_pro && (
              <div style={{ backgroundColor: '#fef3c7', padding: '6px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600', color: '#92400e', display: 'flex', alignItems: 'center', gap: '4px'
              }}>
                <i className="ri-vip-crown-fill"></i>
                Pro User
              </div>
            )}
          </div>
        </header>

        {/* Content */}
        <div style={{ flex: 1, padding: '24px' }}>
          {/* Stats Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(4, 1fr)' : window.innerWidth >= 640 ? 'repeat(2, 1fr)' : '1fr', gap: '24px', marginBottom: '32px'
          }}>
            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Total Insights Chops</p>
                  <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                    {userStats.total_insight_chops}
                  </p>
                </div>
                <div style={{ width: '48px', height: '48px', backgroundColor: '#dbeafe', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ri-lightbulb-line" style={{ color: '#3b82f6', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Reading</p>
                  <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                    {userStats.viewed_insight_chops}
                  </p>
                </div>
                <div style={{ width: '48px', height: '48px', backgroundColor: '#dcfce7', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ri-check-line" style={{ color: '#16a34a', fontSize: '20px' }}></i>
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
                <div style={{ width: '48px', height: '48px', backgroundColor: '#fef3c7', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ri-star-line" style={{ color: '#f59e0b', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>Sharing</p>
                  <p style={{ fontSize: '24px', fontWeight: 'bold', color: '#111827', margin: 0 }}>
                    {userStats.shared_insight_chops}
                  </p>
                </div>
                <div style={{ width: '48px', height: '48px', backgroundColor: '#f3e8ff', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <i className="ri-share-line" style={{ color: '#8b5cf6', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div style={{ fontSize: '18px', color: '#6b7280' }}>Loading insights...</div>
            </div>
          )}

          {/* Insights List */}
          {!loading && (
            <>
              {insights.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px 24px', backgroundColor: '#ffffff', borderRadius: '16px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
                }}>
                  <i className="ri-lightbulb-line" style={{ fontSize: '64px', color: '#d1d5db', marginBottom: '16px',display: 'block'
               }}></i>
                  <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#111827', marginBottom: '8px'
                 }}>
                    No Insights Available
                  </h3>
                  <p style={{ fontSize: '14px', color: '#6b7280' }}>
                    Check back later for new insights!
                  </p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                  {displayInsights.map((insight) => (
                <div
                  key={insight.id}
                  ref={(el) => {
                                  if (el) insightRefs.current[insight.id] = el;
                                  else delete insightRefs.current[insight.id];
                                }}
                  data-insight-id={insight.id}
                  style={{
                    backgroundColor: '#ffffff', borderRadius: '16px', overflow: 'hidden', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)', transition: 'box-shadow 0.3s ease', position: 'relative', border: insight.is_pinned ? '2px solid #f59e0b' : 'none'
                }}
                >
                  {/* Pinned Badge */}
                  {insight.is_pinned && (
                    <div style={{ position: 'absolute', top: '16px', right: '16px', backgroundColor: '#f59e0b', color: '#ffffff', padding: '6px 12px', borderRadius: '20px', fontSize: '12px', fontWeight: '600', zIndex: 10, display: 'flex', alignItems: 'center', gap: '4px'
                 }}>
                      <i className="ri-pushpin-fill"></i>
                      Pinned
                    </div>
                  )}


                  <div style={{ padding: '32px' }}>
                    {/* Header */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', flexWrap: 'wrap', }}>
                      <span style={{ backgroundColor: '#f3f4f6', color: '#374151', padding: '6px 16px', borderRadius: '20px', fontSize: '14px', fontWeight: '500' }}>
                        {insight.category}
                      </span>
                      <span style={{ fontSize: '14px', color: '#6b7280' }}>{insight.read_time}</span>
                      <span style={{ fontSize: '14px', color: '#6b7280' }}>{insight.date}</span>
                      <span>
                        {/* Pin Button */}
                      <button onClick={() => togglePin(insight.id)}
                        style={{ height: '40px', minWidth: '100px', backgroundColor: insight.is_pinned ? '#fef3c7' : '#f3f4f6', color: insight.is_pinned ? '#92400e' : '#374151', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', transition: 'background-color 0.3s ease', padding: '0 16px'}}
                      >
                        <i className={insight.is_pinned ? 'ri-pushpin-fill' : 'ri-pushpin-line'}></i>
                        {insight.is_pinned ? 'Unpin' : 'Pin'}
                      </button>
                      </span>
                    </div>

                    <h2 style={{  fontSize: window.innerWidth >= 768 ? '24px' : '20px', fontWeight: 'bold',  color: '#111827', marginBottom: '24px',lineHeight: '1.3' }}>
                      {insight.title}
                    </h2>

                    {/* Content Sections */}
                    <div style={{ display: 'flex', flexDirection: window.innerWidth >= 1024 ? 'row' : 'column', gap: '24px', marginBottom: '32px'}}>
                      <div style={{ flex: 1, backgroundColor: '#eff6ff', padding: '20px', borderRadius: '12px', border: '1px solid #3b82f6' }}>
                        <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1d4ed8', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <i className="ri-refresh-line" style={{ fontSize: '18px' }}></i>
                          What Changed
                        </h3>
                        <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>
                          {insight.what_changed}
                        </p>
                      </div>

                      <div style={{ flex: 1, backgroundColor: '#fef7ff', padding: '20px', borderRadius: '12px', border: '1px solid #a855f7' }}>
                        <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#7c3aed', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <i className="ri-question-line" style={{ fontSize: '18px' }}></i>
                          Why it matters
                        </h3>
                        <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>
                          {insight.why_it_matters}
                        </p>
                      </div>

                      <div style={{ flex: 1, backgroundColor: '#f0fdf4', padding: '20px', borderRadius: '12px', border: '1px solid #22c55e' }}>
                        <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#16a34a', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <i className="ri-flashlight-line" style={{ fontSize: '18px' }}></i>
                          Action to take
                        </h3>
                        <p style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6', margin: 0 }}>
                          {insight.action_to_take}
                        </p>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(4, 1fr)' : window.innerWidth >= 640 ? 'repeat(2, 1fr)' : '1fr', gap: '16px', marginTop: '8px'}}>
                      {/* Read Status Button */}
                      <button
                        style={{
                          ...getButtonStyle(insight), height: '52px', display: 'flex', alignItems: 'center', minWidth: '0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', justifyContent: 'center' }}
                        title={getButtonText(insight)} // Tooltip on long text
                      >
                        {getReadingStatus(insight) === 'read' && (
                          <i className="ri-check-line" style={{ marginRight: '8px', fontSize: '16px' }}></i>
                        )}
                        {getReadingStatus(insight) === 'reading' && (
                          <i className="ri-time-line" style={{ marginRight: '8px', fontSize: '16px' }}></i>
                        )}
                        {getButtonText(insight)}
                      </button>

                      {/* Share Button */}
                      <button onClick={() => handleShare(insight)}
                        style={{ height: '52px', backgroundColor: insight.is_shared ? '#f97316' : '#3b82f6', color: '#ffffff', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', whiteSpace: 'nowrap', transition: 'all 0.3s ease'}}
                      >
                        <i className={insight.is_shared ? 'ri-check-line' : 'ri-share-line'}></i>
                        {insight.is_shared ? 'Shared' : `Share (+${userStats.is_pro ? 10 : 5} chops)`}
                      </button>

                      {/* View Source Button - only show if URL exists */}
                      {insight.url && insight.url.startsWith('http') && (
                        <button onClick={() => window.open(insight.url, '_blank')}
                          style={{ height: '52px', backgroundColor: '#f3f4f6', color: '#374151', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', transition: 'background-color 0.3s ease', marginLeft: '20px'}}
                        >
                          <i className="ri-external-link-line"></i>
                          View Details
                        </button>
                      )}
                    </div>
                  </div>
                </div>
                  ))}
                  {!userStats.is_pro && insights.length > FREE_USER_LIMIT && (
          <div style={{ textAlign: 'center', padding: '40px 24px', backgroundColor: '#fff7ed', borderRadius: '16px', border: '2px dashed #fb923c', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)', marginTop: '32px'
       }}>
            <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#c2410c', marginBottom: '12px' }}>
              Unlock More Insights!
            </h3>
            <p style={{ fontSize: '16px', color: '#9a3412', marginBottom: '20px' }}>
              You've viewed your first {FREE_USER_LIMIT} insights. Upgrade to Pro to access the full AI Insights Feed and earn up to 5x more Chops!
            </p>
            <button
              onClick={() =>window.location.href = '/upgrade'} // Replace with actual upgrade link/modal logic
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
              Go Pro Now!
            </button>
          </div>
        )}
                </div>
              )}
            </>
          )}

          {/* Pagination */}
          {userStats.is_pro && totalPages > 1 && (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '12px',
              marginTop: '40px'
            }}>
              <button
                onClick={() => fetchInsights(currentPage - 1)}
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
                    onClick={() => fetchInsights(page)}
                    style={{
                      padding: '10px 14px',
                      backgroundColor: currentPage === page ? '#3b82f6' : '#f3f4f6',
                      color: currentPage === page ? '#ffffff' : '#374151',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: '600',
                      minWidth: '40px'
                    }}
                  >
                    {page}
                  </button>
                ))}
              </div>

              <button
                onClick={() => fetchInsights(currentPage + 1)}
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
      </div>

      {/* Toast Notification */}
      {showToast && (
        <div style={{
          position: 'fixed',
          top: '24px',
          right: '24px',
          backgroundColor: '#f97316',
          color: '#ffffff',
          padding: '16px 20px',
          borderRadius: '8px',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          maxWidth: '400px',
          animation: 'slideIn 0.3s ease-out'
        }}>
          <i className="ri-star-fill" style={{ marginRight: '8px', fontSize: '16px' }}></i>
          {toastMessage}
        </div>
      )}

      {/* Share Modal */}
      {showShareModal && selectedInsight && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 40 }}
            onClick={() => setShowShareModal(false)}
          />
          <div style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            padding: '24px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
            zIndex: 50,
            width: '90%',
            maxWidth: '400px'
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#111827', marginBottom: '16px', textAlign: 'center' }}>
              Share Insight
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px' }}>
              <button
                onClick={() => shareToSocialMedia('twitter')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '12px',
                  backgroundColor: '#1da1f2',
                  color: '#ffffff',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                <i className="ri-twitter-fill" style={{ marginRight: '8px' }}></i>
                Twitter
              </button>

              <button
                onClick={() => shareToSocialMedia('facebook')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '12px',
                  backgroundColor: '#4267b2',
                  color: '#ffffff',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                <i className="ri-facebook-fill" style={{ marginRight: '8px' }}></i>
                Facebook
              </button>

              <button
                onClick={() => shareToSocialMedia('linkedin')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '12px',
                  backgroundColor: '#0077b5',
                  color: '#ffffff',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                <i className="ri-linkedin-fill" style={{ marginRight: '8px' }}></i>
                LinkedIn
              </button>

              <button
                onClick={() => shareToSocialMedia('whatsapp')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '12px',
                  backgroundColor: '#25d366',
                  color: '#ffffff',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                <i className="ri-whatsapp-fill" style={{ marginRight: '8px' }}></i>
                WhatsApp
              </button>
            </div>

            <button
              onClick={copyLink}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '12px',
                backgroundColor: '#f3f4f6',
                color: '#374151',
                borderRadius: '8px',
                border: 'none',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500',
                marginBottom: '16px'
              }}
            >
              <i className="ri-file-copy-line" style={{ marginRight: '8px' }}></i>
              Copy Link
            </button>

            <button
              onClick={() => setShowShareModal(false)}
              style={{
                width: '100%',
                padding: '12px',
                backgroundColor: 'transparent',
                color: '#6b7280',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              Cancel
            </button>
          </div>
        </>
      )}

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
