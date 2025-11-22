
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function AlertsPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [userPoints, setUserPoints] = useState(0);
  const [sharedAlerts, setSharedAlerts] = useState(new Set());
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [isPremium] = useState(false); // This would come from user's subscription statuss
  const navigate = useNavigate()

  const [viewedAlerts, setViewedAlerts] = useState<Set<string>>(new Set());
  const [viewportWidth, setViewportWidth] = useState(0);
  
  // Load saved data from localStorage
  useEffect(() => {
    setViewportWidth(window.innerWidth);

    const savedViewedAlerts = localStorage.getItem('viewedAlerts');
    const savedSharedAlerts = localStorage.getItem('sharedAlerts');
    const savedUserPoints = localStorage.getItem('userPoints');
    
    if (savedViewedAlerts) {
      setViewedAlerts(new Set(JSON.parse(savedViewedAlerts)));
    }
    if (savedSharedAlerts) {
      setSharedAlerts(new Set(JSON.parse(savedSharedAlerts)));
    }
    if (savedUserPoints) {
      setUserPoints(parseInt(savedUserPoints));
    }

    const handleResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Save data to localStorage
  const saveToLocalStorage = (viewed: Set<string>, shared: Set<string>, points: number) => {
    localStorage.setItem('viewedAlerts', JSON.stringify([...viewed]));
    localStorage.setItem('sharedAlerts', JSON.stringify([...shared]));
    localStorage.setItem('userPoints', points.toString());
    
    // Update earnings page progress
    const currentEarningsPoints = parseInt(localStorage.getItem('earnedPoints') || '0');
    const totalPoints = currentEarningsPoints + points;
    localStorage.setItem('earnedPoints', totalPoints.toString());
    
    // Dispatch event to update earnings page
    window.dispatchEvent(new CustomEvent('pointsUpdated', { 
      detail: { points: totalPoints } 
    }));
  };

  const alerts = [
    {
      id: 1,
      title: "LinkedIn Algorithm Update Opportunity",
      category: "Market",
      priority: "High",
      score: 92,
      timeRemaining: "2 days",
      whyActNow: "LinkedIn's new algorithm favors video content and carousel posts. Early adopters are seeing 3x higher engagement rates. This window typically lasts 2-3 weeks before competition catches up.",
      potentialReward: "Increase LinkedIn engagement by 300%, generate 50+ qualified leads monthly, establish thought leadership in your industry. Estimated revenue impact: $15,000-25,000 monthly.",
      actionRequired: "Create 5 video posts and 3 carousel posts this week. Focus on industry insights and behind-the-scenes content. Use trending hashtags #IndustryInsights #Leadership #Innovation.",
      date: new Date().toISOString().split('T')[0]
    },
    {
      id: 2,
      title: "Content Gap in AI Strategy Market",
      category: "Content",
      priority: "High",
      score: 88,
      timeRemaining: "5 days",
      whyActNow: "Competitor analysis shows 73% of businesses lack AI implementation guides. Search volume for 'AI strategy for small business' increased 340% this month with low competition.",
      potentialReward: "Capture 15-20% market share in AI consulting niche. Potential for $50,000+ in consulting revenue. Build authority as AI strategy expert in your industry.",
      actionRequired: "Publish comprehensive AI strategy guide within 5 days. Include case studies, implementation timeline, and ROI calculator. Optimize for keywords: 'AI strategy', 'business automation', 'AI implementation'.",
      date: new Date().toISOString().split('T')[0]
    },
    {
      id: 3,
      title: "Customer Churn Risk Alert",
      category: "Customer",
      priority: "Medium",
      score: 76,
      timeRemaining: "1 week",
      whyActNow: "15 high-value customers showing decreased engagement (40% drop in platform usage). Historical data shows 78% churn probability within 30 days without intervention.",
      potentialReward: "Retain $45,000 in annual recurring revenue. Improve customer lifetime value by 25%. Strengthen customer relationships and reduce acquisition costs.",
      actionRequired: "Launch personalized re-engagement campaign. Schedule 1-on-1 calls with at-risk customers. Offer exclusive training session or premium feature access. Send within 48 hours.",
      date: new Date().toISOString().split('T')[0]
    },
    {
      id: 4,
      title: "New AI Tool Early Access Program",
      category: "Technology",
      priority: "Medium",
      score: 84,
      timeRemaining: "3 days",
      whyActNow: "OpenAI's new business API offers 50% discount for early adopters. Limited to first 1,000 businesses. Tool can automate 60% of customer service tasks.",
      potentialReward: "Save $8,000 monthly on customer service costs. Improve response time by 75%. Access premium features at 50% discount for 12 months.",
      actionRequired: "Apply for early access program immediately. Prepare integration plan for customer service automation. Allocate 2 developers for 1-week implementation sprint.",
      date: new Date().toISOString().split('T')[0]
    },
    {
      id: 5,
      title: "Competitor Pricing Strategy Shift",
      category: "Competitive",
      priority: "High",
      score: 90,
      timeRemaining: "4 days",
      whyActNow: "Main competitor increased prices by 35% effective next week. Market research shows 40% of their customers are actively seeking alternatives. Perfect timing to capture market share.",
      potentialReward: "Acquire 200-300 new customers within 60 days. Increase market share by 12%. Generate additional $180,000 in quarterly revenue.",
      actionRequired: "Launch competitive pricing campaign highlighting value proposition. Create comparison chart showing cost savings. Offer limited-time migration incentive with 3 months free service.",
      date: new Date().toISOString().split('T')[0]
    }
  ];

  const MyComponent = () => {
  // Declare state for attended alerts
  const [attendedAlerts, setAttendedAlerts] = useState<Set<number>>(new Set());

  // Function to mark an alert as attended
  const markAsAttended = (alertId: number) => {
    setAttendedAlerts(prev => new Set([...prev, alertId]));
  };


  const handleShare = (alert: any) => {
    setSelectedAlert(alert);
    setShowShareModal(true);
  };

  
  const [sharedAlerts, setSharedAlerts] = useState<Set<string>>(new Set());
  const [userPoints, setUserPoints] = useState<number>(0);

  interface Alert {
    id: number | string;
    title: string;
    category: string;
    priority: string;
    score: number;
    timeRemaining: string;
    whyActNow: string;
    potentialReward: string;
    actionRequired: string;
    date: string;
  }

  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

    // Award points only if not already viewed
  const handleViewDetails = (alert: any) => {
    markAsAttended(alert.id.toString());
    if (!viewedAlerts.has(alert.id)) {
      const pointsToAdd = isPremium ? 10 : 5;
      const newUserPoints = userPoints + pointsToAdd;
      const newViewedAlerts = new Set([...viewedAlerts, alert.id]);
      
      
      setUserPoints(newUserPoints);
      setViewedAlerts(newViewedAlerts);
      saveToLocalStorage(newViewedAlerts, sharedAlerts, newUserPoints);
      
      setToastMessage(`You earned ${pointsToAdd} Chops for viewing this alert!`);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
    }
    
    if (alert.source && alert.source !== '#') {
      window.open(alert.source, '_blank');
    } else {
      window.open('https://www.google.com/search?q=business+opportunities', '_blank');
    }
  };

  type Platform = 'twitter' | 'facebook' | 'linkedin' | 'whatsapp';

  const shareToSocialMedia = (platform: Platform) => {
    if (!selectedAlert) return;

    const userName = 'John Doe'; // This should come from user data
    const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(userName)}`;
    const alertUrl = `${referralLink}&alert=${selectedAlert!.id}`;
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
      awardSharingPoints();
    }
    
    setShowShareModal(false);
  };

  const copyLink = () => {
    if (!selectedAlert) return;
    const userName = 'John Doe'; // This should come from user data
    const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(userName)}`;
    const alertUrl = `${referralLink}&alert=${selectedAlert.id}`;
    navigator.clipboard.writeText(alertUrl);
    awardSharingPoints();
    setToastMessage('Link copied to clipboard!');
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
    setShowShareModal(false);
  };

  const awardSharingPoints = () => {
    if (!selectedAlert) return;
    const alertId = selectedAlert.id.toString();
    // Award points only if not already shared
    if (!sharedAlerts.has(alertId)) {
      const pointsToAdd = isPremium ? 10 : 5;
      const newUserPoints = userPoints + pointsToAdd;
      const newSharedAlerts = new Set([...sharedAlerts, alertId]);
      
      setUserPoints(newUserPoints);
      setSharedAlerts(newSharedAlerts);
      saveToLocalStorage(viewedAlerts, newSharedAlerts, newUserPoints);
      
      if (!showToast) {
        setToastMessage(`You earned ${pointsToAdd} points for sharing this alert!`);
        setShowToast(true);
        setTimeout(() => setShowToast(false), 3000);
      }
    }
  };

  const unattendedCount = alerts.length - attendedAlerts.size;


  const getScoreBgColor = (score: any) => {
    if (score >= 90) return '#dcfce7'; // Green bg
    if (score >= 80) return '#fef3c7'; // Yellow bg
    if (score >= 70) return '#fed7aa'; // Orange bg
    return '#fecaca'; // Red bg
  };


  const getPriorityBgColor = (priority: any) => {
    switch (priority) {
      case 'High':
        return '#fef2f2';
      case 'Medium':
        return '#fffbeb';
      case 'Low':
        return '#f0fdf4';
      default:
        return '#f9fafb';
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    const categoryMatch = selectedCategory === 'all' || alert.category.toLowerCase() === selectedCategory;
    const priorityMatch = selectedPriority === 'all' || alert.priority.toLowerCase() === selectedPriority;
    return categoryMatch && priorityMatch;
  });

  // Show only first 2 alerts + premium upgrade alert if not premium
  const displayedAlerts = isPremium ? filteredAlerts : filteredAlerts.slice(0, 2);
  const hasMoreAlerts = !isPremium && filteredAlerts.length > 2;

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 80) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (score >= 70) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  
  const getPriorityColor = (priority: string) => {
    if (priority === 'High') return 'bg-red-100 text-red-800 border-red-200';
    if (priority === 'Medium') return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-green-100 text-green-800 border-green-200';
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Market': return 'ri-line-chart-line';
      case 'Content': return 'ri-article-line';
      case 'Customer': return 'ri-user-heart-line';
      case 'Technology': return 'ri-robot-line';
      case 'Competitive': return 'ri-sword-line';
      default: return 'ri-notification-line';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Opportunity Alerts</h1>
          <p className="text-sm sm:text-base text-gray-600">AI-powered opportunities to grow your business</p>
        </div>

        {/* Stats Overview */}
        {/* Main Content */}
        <div style={{  flex: 1, marginLeft: '0', display: 'flex', flexDirection: 'column'}}>
        
        {/* Header */}
        <header style={{ backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '16px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <button
              style={{ 
                display: window.innerWidth >= 768 ? 'none' : 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '40px',
                height: '40px',
                backgroundColor: 'transparent',
                border: 'none',
                borderRadius: '6px',
                color: '#6b7280', cursor: 'pointer', marginRight: '16px' }}    
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <i className="ri-menu-line" style={{ fontSize: '20px' }}></i>
            </button>
            <h1 style={{ 
              fontSize: window.innerWidth >= 640 ? '24px' : '20px', fontWeight: 'bold', color: '#111827', margin: 0  
            }}>Opportunity Alerts</h1>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ 
              backgroundColor: '#f3f4f6', 
              padding: '8px 16px', 
              borderRadius: '20px',
              fontSize: '14px',
              fontWeight: '500', color: '#374151', display: window.innerWidth >= 640 ? 'block' : 'none'
            }}>
              Chops: {userPoints}
            </div>
            <div style={{ backgroundColor: '#f3f4f6', padding: '8px 16px', borderRadius: '20px', fontSize: '14px',
              fontWeight: '500', color: '#374151', display: window.innerWidth >= 640 ? 'block' : 'none'  
            }}>
              {unattendedCount} unattended
            </div>
          </div>
        </header>

        {/* Content */}
        <div style={{ flex: 1, padding: window.innerWidth >= 768 ? '24px' : '16px' }}>
          {/* Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(4, 1fr)' : window.innerWidth >= 640 ? 'repeat(2, 1fr)' : '1fr', gap: '16px',
            marginBottom: '32px'}}>
            <div style={{ backgroundColor: '#ffffff', padding: '20px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>Total Alerts</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>{alerts.length}</p>
                </div>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  backgroundColor: '#dbeafe', 
                  borderRadius: '12px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <i className="ri-notification-line" style={{ color: '#3b82f6', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#ffffff', 
              padding: '20px', 
              borderRadius: '12px', 
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>Points Earned</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>{userPoints}</p>
                </div>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  backgroundColor: '#fef3c7', 
                  borderRadius: '12px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <i className="ri-star-line" style={{ color: '#f59e0b', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#ffffff', 
              padding: '20px', 
              borderRadius: '12px', 
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>Attended</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>{attendedAlerts.size}</p>
                </div>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  backgroundColor: '#dcfce7', 
                  borderRadius: '12px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <i className="ri-check-line" style={{ color: '#16a34a', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#ffffff', 
              padding: '20px', 
              borderRadius: '12px', 
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>User Type</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>{isPremium ? 'Premium' : 'Free'}</p>
                </div>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  backgroundColor: isPremium ? '#f3e8ff' : '#f3f4f6', 
                  borderRadius: '12px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <i className={isPremium ? 'ri-vip-crown-line' : 'ri-user-line'} style={{ color: isPremium ? '#8b5cf6' : '#6b7280', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>
          </div>

          {/* Alerts List */}
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', gap: '32px' }}>
            {alerts.map((alert) => (
              <div key={alert.id} style={{ 
                backgroundColor: '#ffffff', 
                borderRadius: '16px', 
                padding: '32px', 
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                border: attendedAlerts.has(alert.id) ? '2px solid #10b981' : '1px solid #e5e7eb',
                transition: 'all 0.3s ease'}}>
                {/* Header Section */}
                <div style={{ 
                  display: 'flex', flexDirection: window.innerWidth >= 768 ? 'row' : 'column', alignItems: window.innerWidth >= 768 ? 'flex-start' : 'stretch',
                  justifyContent: 'space-between', marginBottom: '24px',
                  gap: '16px'}}>
                  <div style={{ flex: 1 }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '12px', 
                      marginBottom: '12px',
                      flexWrap: 'wrap'}}>
                      <span style={{ 
                        backgroundColor: getScoreBgColor(alert.score),
                        color: getScoreColor(alert.score),
                        padding: '6px 16px', 
                        borderRadius: '20px', 
                        fontSize: '14px', 
                        fontWeight: '700',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        <i className="ri-star-fill" style={{ fontSize: '12px' }}></i>
                        Score: {alert.score}
                      </span>
                      <span style={{ 
                        backgroundColor: getPriorityBgColor(alert.priority),
                        color: getPriorityColor(alert.priority),
                        padding: '6px 16px', 
                        borderRadius: '20px', 
                        fontSize: '14px', 
                        fontWeight: '600' 
                      }}>
                        {alert.priority} Priority
                      </span>
                      <span style={{ 
                        backgroundColor: '#f3f4f6', 
                        color: '#374151', 
                        padding: '6px 16px', 
                        borderRadius: '20px', 
                        fontSize: '14px', 
                        fontWeight: '500' 
                      }}>
                        {alert.category}
                      </span>
                      <span style={{ 
                        fontSize: '14px', 
                        color: '#6b7280',
                        fontWeight: '500'
                      }}>
                        {alert.date}
                      </span>
                    </div>
                    <h2 style={{ 
                      fontSize: window.innerWidth >= 768 ? '24px' : '20px', 
                      fontWeight: 'bold', 
                      color: '#111827', 
                      marginBottom: '0',
                      lineHeight: '1.3'
                    }}>
                      {alert.title}
                    </h2>
                  </div>
                  
                  {attendedAlerts.has(alert.id) && (
                    <div style={{ 
                      backgroundColor: '#dcfce7', 
                      color: '#16a34a', 
                      padding: '12px 20px', 
                      borderRadius: '24px', 
                      fontSize: '14px', 
                      fontWeight: '600',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      alignSelf: window.innerWidth >= 768 ? 'flex-start' : 'center'}}>
                      <i className="ri-check-line" style={{ fontSize: '16px' }}></i>
                      Attended
                    </div>
                  )}
                </div>

                {/* Content Sections */}
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(3, 1fr)' : '1fr',
                  gap: '24px', 
                  marginBottom: '32px' }}>
                  {/* Why Act Now */}
                  <div style={{ 
                    backgroundColor: '#fef7ff', 
                    padding: '20px', 
                    borderRadius: '12px',
                    border: '1px solid #e879f9'}}>
                    <h3 style={{ 
                      fontSize: '16px', 
                      fontWeight: 'bold', 
                      color: '#a21caf', 
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <i className="ri-time-line" style={{ fontSize: '18px' }}></i>
                      Why Act Now
                    </h3>
                    <p style={{ 
                      fontSize: '14px', 
                      color: '#4b5563', 
                      lineHeight: '1.6',
                      margin: 0
                    }}>
                      {alert.whyActNow}
                    </p>
                  </div>

                  {/* Potential Reward */}
                  <div style={{ 
                    backgroundColor: '#f0fdf4', 
                    padding: '20px', 
                    borderRadius: '12px',
                    border: '1px solid #22c55e'}}>
                    <h3 style={{ 
                      fontSize: '16px', 
                      fontWeight: 'bold', 
                      color: '#16a34a', 
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <i className="ri-trophy-line" style={{ fontSize: '18px' }}></i>
                      Potential Reward
                    </h3>
                    <p style={{ 
                      fontSize: '14px', 
                      color: '#4b5563', 
                      lineHeight: '1.6',
                      margin: 0
                    }}>
                      {alert.potentialReward}
                    </p>
                  </div>

                  {/* Action Required */}
                  <div style={{ 
                    backgroundColor: '#fff7ed', 
                    padding: '20px', 
                    borderRadius: '12px',
                    border: '1px solid #f97316',
                    gridColumn: window.innerWidth >= 1024 ? 'auto' : '1 / -1'}}>
                    <h3 style={{ 
                      fontSize: '16px', 
                      fontWeight: 'bold', 
                      color: '#ea580c', 
                      marginBottom: '12px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <i className="ri-flashlight-line" style={{ fontSize: '18px' }}></i>
                      Action Required
                    </h3>
                    <p style={{ 
                      fontSize: '14px', 
                      color: '#4b5563', 
                      lineHeight: '1.6',
                      margin: 0
                    }}>
                      {alert.actionRequired}
                    </p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div style={{ 
                  display: 'flex', 
                  flexDirection: window.innerWidth >= 640 ? 'row' : 'column',
                  gap: '16px', 
                  paddingTop: '24px', 
                  borderTop: '1px solid #e5e7eb' }}>
                  <button 
                    onClick={() => handleShare(alert)}
                    style={{ 
                      flex: 1,
                      backgroundColor: sharedAlerts.has(alert.id.toString()) ? '#10b981' : '#f97316', 
                      color: '#ffffff', padding: '14px 20px', borderRadius: '10px',  border: 'none', fontSize: '15px',
                      fontWeight: '600', cursor: 'pointer', display: 'flex',alignItems: 'center',  justifyContent: 'center', transition: 'background-color 0.3s ease', whiteSpace: 'nowrap' }}        
                    onMouseOver={(e : React.MouseEvent<HTMLButtonElement>) => 
                      e.currentTarget.style.backgroundColor = sharedAlerts.has(alert.id.toString()) ? '#059669' : '#ea580c'}
                    onMouseOut={(e : React.MouseEvent<HTMLButtonElement>) => 
                      e.currentTarget.style.backgroundColor = sharedAlerts.has(alert.id.toString()) ? '#10b981' : '#f97316'}
                  >
                    <i className={sharedAlerts.has(alert.id.toString()) ? 'ri-check-line' : 'ri-share-line'} style={{ marginRight: '8px', fontSize: '16px' }}></i>
                    {sharedAlerts.has(alert.id.toString()) ? 'Shared' : `Share (+${isPremium ? 10 : 5} points)`}
                  </button>
                  <button 
                    onClick={() => handleViewDetails(alert)}
                    style={{ 
                      flex: 1,
                      backgroundColor: viewedAlerts.has(alert.id.toString()) ? '#10b981' : 'transparent', 
                      color: viewedAlerts.has(alert.id.toString()) ? '#ffffff' : '#6b7280',  padding: '14px 20px', 
                      borderRadius: '10px', fontSize: '15px', fontWeight: '600',cursor: 'pointer', alignItems: 'center',
                      justifyContent: 'center', transition: 'all 0.3s ease', whiteSpace: 'nowrap',
                      display: 'flex', border: viewedAlerts.has(alert.id.toString()) ? 'none' : '2px solid #d1d5db',}}
                    onMouseOver={(e) => {
                      if (!viewedAlerts.has(alert.id.toString())) {
                        e.currentTarget.style.backgroundColor = '#f9fafb';
                        e.currentTarget.style.borderColor = '#9ca3af';
                        e.currentTarget.style.color = '#374151';
                      }
                    }}
                    onMouseOut={(e) => {
                      if (!viewedAlerts.has(alert.id.toString())) {
                        e.currentTarget.style.backgroundColor = 'transparent';
                        e.currentTarget.style.borderColor = '#d1d5db';
                        e.currentTarget.style.color = '#6b7280';
                      }
                    }}
                  >
                    <i className={viewedAlerts.has(alert.id.toString()) ? 'ri-check-line' : 'ri-external-link-line'} style={{ marginRight: '8px', fontSize: '16px' }}></i>
                    {viewedAlerts.has(alert.id.toString()) ? 'Viewed' : `View Details (+${isPremium ? 10 : 5} points)`}
                  </button>
                  <button style={{ 
                    flex: 1, backgroundColor: 'transparent', color: '#6b7280',padding: '14px 20px', borderRadius: '10px', border: '2px solid #d1d5db', fontSize: '15px', fontWeight: '600',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.3s ease', whiteSpace: 'nowrap'}}
                  onMouseOver={(e) => {
                    e.currentTarget.style.backgroundColor = '#f9fafb';
                    e.currentTarget.style.borderColor = '#9ca3af';
                    e.currentTarget.style.color = '#374151';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.borderColor = '#d1d5db';
                    e.currentTarget.style.color = '#6b7280';
                  }}>
                    <i className="ri-time-line" style={{ marginRight: '8px', fontSize: '16px' }}></i>
                    Remind Later
                  </button>
              </div>
              </div>
            ))}
          </div>
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
          maxWidth: window.innerWidth >= 640 ? '400px' : '90%',
          animation: 'slideIn 0.3s ease-out'
        }}>
          <i className="ri-star-fill" style={{ marginRight: '8px', fontSize: '16px' }}></i>
          {toastMessage}
        </div>
        )}

        {/* Share Modal */}
        {showShareModal && (
        <>
          <div 
            style={{ position: 'fixed', inset: 0,backgroundColor: 'rgba(0, 0, 0, 0.5)',  zIndex: 40 }}
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
            <h3 style={{ 
              fontSize: '18px', 
              fontWeight: 'bold', 
              color: '#111827', 
              marginBottom: '16px',
              textAlign: 'center'
            }}>
              Share Alert
            </h3>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(2, 1fr)', 
              gap: '12px', 
              marginBottom: '16px' 
            }}>
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
        
        {/* Premium Upgrade Alert */}
        {hasMoreAlerts && (
        <div className="bg-white rounded-lg sm:rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Alert Header */}
              <div className="p-4 sm:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-3 sm:gap-4">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-orange-400 to-orange-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-vip-crown-line text-white text-lg sm:text-xl"></i>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-2">
                        {filteredAlerts.length - 2} More Pro Opportunities Available
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-orange-100 to-orange-200 text-orange-800 border border-orange-300">
                          Pro Content
                        </span>
                        <span className="text-xs sm:text-sm text-gray-500">
                          <i className="ri-lock-line mr-1"></i>
                          Unlock with Pro
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <div className="px-3 py-2 rounded-lg border bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200 text-center">
                      <div className="text-lg sm:text-xl font-bold text-orange-600">★</div>
                      <div className="text-xs font-medium text-orange-600">Pro</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Premium Content */}
              <div className="p-4 sm:p-6">
                <div className="text-center py-8 sm:py-12">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <i className="ri-vip-crown-line text-white text-2xl sm:text-3xl"></i>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-3">Unlock Pro Opportunities</h3>
                  <p className="text-sm sm:text-base text-gray-600 mb-2 max-w-md mx-auto">
                    Get access to high-value opportunities with detailed insights and action plans
                  </p>
                  <p className="text-xs sm:text-sm text-orange-600 font-medium mb-8">
                    Pro members see 10x more opportunities on average
                  </p>
                  
                  {/* Premium Features */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 max-w-2xl mx-auto">
                    <div className="text-center">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center mx-auto mb-2 shadow-sm">
                        <i className="ri-eye-line text-orange-600"></i>
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-gray-700">Full Alert Details</p>
                    </div>
                    <div className="text-center">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center mx-auto mb-2 shadow-sm">
                        <i className="ri-lightbulb-line text-orange-600"></i>
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-gray-700">AI Insights</p>
                    </div>
                    <div className="text-center">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center mx-auto mb-2 shadow-sm">
                        <i className="ri-rocket-line text-orange-600"></i>
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-gray-700">Action Plans</p>
                    </div>
                  </div>

                  <button 
                    onClick={() => navigate('/dashboard/upgrade')}
                    className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-8 py-3 rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all font-medium text-sm sm:text-base whitespace-nowrap shadow-lg cursor-pointer transform hover:scale-105"
                  >
                    Upgrade to Pro
                  </button>
                  <p className="text-xs text-gray-5	00 mt-3">Starting at $29.95/month • Cancel anytime</p>
                </div>
              </div>
        </div>
        )}
      </div>

      {/* Show message if no alerts match filters */}
      {displayedAlerts.length === 0 && !hasMoreAlerts && (
      <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="ri-notification-off-line text-gray-400 text-2xl"></i>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No alerts found</h3>
            <p className="text-gray-600">Try adjusting your filters to see more opportunities.</p>
      </div>
      )}
    </div>
  
  );
}
  
  return <MyComponent />;
}
