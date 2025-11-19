
import { useState, useEffect} from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import { useNavigate } from 'react-router-dom';


export default function DashboardInsights() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [readInsights, setReadInsights] = useState<Set<Insight['id']>>(new Set());
  const [sharedInsights, setSharedInsights] = useState(new Set());
  const [earnedPoints, setEarnedPoints] = useState(0);
  const [timers, setTimers] = useState<Record<Insight['id'], ReturnType<typeof setTimeout>>>({});
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null);

  // Mock user data
  const isPremiumUser = false; // Change this to test different user types

  // Load saved data from localStorage
  useEffect(() => {
    const savedReadInsights = localStorage.getItem('readInsights');
    const savedSharedInsights = localStorage.getItem('sharedInsights');
    const savedEarnedPoints = localStorage.getItem('earnedPoints');
    
    if (savedReadInsights) {
      setReadInsights(new Set(JSON.parse(savedReadInsights)));
    }
    if (savedSharedInsights) {
      setSharedInsights(new Set(JSON.parse(savedSharedInsights)));
    }
    if (savedEarnedPoints) {
      setEarnedPoints(parseInt(savedEarnedPoints));
    }
  }, []);

  interface Insight {
    id: string;
    title: string;
    viewed: boolean;
  }

  // Save data to localStorage
  const saveToLocalStorage = (insights: Insight[], shared: Insight[], points: number) => {
    localStorage.setItem('readInsights', JSON.stringify([...insights]));
    localStorage.setItem('sharedInsights', JSON.stringify([...shared]));
    localStorage.setItem('earnedPoints', points.toString());
    
    // Dispatch event to update earnings page
    window.dispatchEvent(new CustomEvent('pointsUpdated', { 
      detail: { points: points } 
    }));
  };

  const insights = [
    {
      id: 1,
      title: "AI-Powered Customer Service Revolution",
      category: "Customer Service",
      readTime: "3 min read",
      date: "2024-01-15",
      source: "https://www.salesforce.com/resources/articles/customer-service/",
      image: "https://readdy.ai/api/search-image?query=modern%20customer%20service%20representative%20using%20AI%20chatbot%20technology%20in%20bright%20office%20environment%20with%20digital%20screens%20showing%20customer%20satisfaction%20metrics&width=400&height=250&seq=cs1&orientation=landscape",
      whatChanged: "New chatbot technology reduces response time by 85% while maintaining 94% customer satisfaction rates. Advanced AI can now handle complex queries that previously required human intervention.",
      whyItMatters: "Customer expectations for instant support are at an all-time high. Companies that don't adapt to AI-powered service will lose customers to competitors who provide faster, more efficient support experiences.",
      actionToTake: "Evaluate your current customer service metrics, research AI chatbot solutions, and implement a pilot program for common customer queries within the next 30 days."
    },
    {
      id: 2,
      title: "Predictive Analytics Transforms Inventory Management",
      category: "Operations",
      readTime: "4 min read",
      date: "2024-01-14",
      source: "https://www.mckinsey.com/capabilities/operations/our-insights",
      image: "https://readdy.ai/api/search-image?query=modern%20warehouse%20with%20automated%20inventory%20management%20systems%20and%20digital%20analytics%20dashboards%20showing%20predictive%20data%20visualization%20in%20clean%20industrial%20setting&width=400&height=250&seq=inv1&orientation=landscape",
      whatChanged: "Machine learning algorithms now help retailers reduce waste by 40% and improve stock availability to 98%. Real-time demand forecasting has become incredibly accurate.",
      whyItMatters: "Inventory costs can make or break a business. Poor inventory management leads to lost sales, excess storage costs, and cash flow problems that can cripple growth.",
      actionToTake: "Audit your current inventory processes, identify pain points, and research predictive analytics tools that integrate with your existing systems."
    },
    {
      id: 3,
      title: "Marketing Automation Drives 300% ROI Increase",
      category: "Marketing",
      readTime: "5 min read",
      date: "2024-01-13",
      source: "https://blog.hubspot.com/marketing/marketing-automation",
      image: "https://readdy.ai/api/search-image?query=digital%20marketing%20professional%20analyzing%20automated%20campaign%20results%20on%20multiple%20monitors%20with%20colorful%20data%20visualizations%20and%20ROI%20charts%20in%20modern%20office&width=400&height=250&seq=mark1&orientation=landscape",
      whatChanged: "Marketing automation platforms now deliver personalized experiences at scale, resulting in 300% ROI improvements for businesses that implement comprehensive automation strategies.",
      whyItMatters: "Manual marketing processes can't compete with automated personalization. Companies using marketing automation see 451% increase in qualified leads and 34% increase in sales-ready leads.",
      actionToTake: "Map your customer journey, identify automation opportunities, select a marketing automation platform, and create personalized nurture campaigns for different customer segments."
    },
    {
      id: 4,
      title: "Financial Forecasting with Machine Learning",
      category: "Finance",
      readTime: "6 min read",
      date: "2024-01-12",
      source: "https://www.jpmorgan.com/insights/technology/artificial-intelligence",
      image: "https://readdy.ai/api/search-image?query=financial%20analyst%20working%20with%20AI-powered%20forecasting%20tools%20showing%20market%20trend%20predictions%20and%20investment%20data%20on%20sleek%20trading%20desk%20setup&width=400&height=250&seq=fin1&orientation=landscape",
      whatChanged: "AI-powered financial forecasting models now achieve 95% accuracy in predicting market trends and cash flow patterns, significantly outperforming traditional forecasting methods.",
      whyItMatters: "Accurate financial forecasting is critical for strategic planning and risk management. Traditional methods often miss subtle patterns that AI can detect, leading to better investment decisions.",
      actionToTake: "Evaluate your current forecasting methods, research AI-powered financial tools, and pilot machine learning models for your most critical financial predictions."
    },
    {
      id: 5,
      title: "Supply Chain Optimization Through AI",
      category: "Logistics",
      readTime: "4 min read",
      date: "2024-01-11",
      source: "https://www.dhl.com/global-en/home/insights-and-innovation/insights/artificial-intelligence.html",
      image: "https://readdy.ai/api/search-image?query=advanced%20supply%20chain%20control%20center%20with%20AI%20optimization%20systems%20tracking%20global%20logistics%20and%20delivery%20routes%20on%20large%20digital%20displays&width=400&height=250&seq=log1&orientation=landscape",
      whatChanged: "AI-driven supply chain optimization reduces costs by 15% and improves delivery times by 25%. Real-time route optimization and demand prediction are revolutionizing logistics.",
      whyItMatters: "Supply chain disruptions cost businesses billions annually. AI optimization provides resilience and efficiency that traditional methods cannot match in today's complex global market.",
      actionToTake: "Assess your supply chain vulnerabilities, implement AI-powered tracking systems, and develop predictive models for demand forecasting and route optimization."
    },
    {
      id: 6,
      title: "HR Analytics Revolutionizes Talent Acquisition",
      category: "Human Resources",
      readTime: "3 min read",
      date: "2024-01-10",
      source: "https://www.workday.com/en-us/applications/human-capital-management/workforce-analytics.html",
      image: "https://readdy.ai/api/search-image?query=HR%20professional%20using%20advanced%20analytics%20dashboard%20for%20talent%20acquisition%20with%20candidate%20profiles%20and%20hiring%20metrics%20in%20modern%20corporate%20office&width=400&height=250&seq=hr1&orientation=landscape",
      whatChanged: "HR analytics platforms now predict employee success with 87% accuracy and reduce time-to-hire by 50%. Data-driven hiring decisions significantly improve retention rates.",
      whyItMatters: "The cost of bad hires can reach 30% of the employee's first-year earnings. HR analytics helps identify the best candidates and predict long-term success and cultural fit.",
      actionToTake: "Implement HR analytics tools, define key performance indicators for hiring success, and create data-driven hiring processes that reduce bias and improve outcomes."
    }
  ];

  const startReadingTimer = (insightId: string) => {
    if (readInsights.has(insightId) || timers[insightId]) return;

    const timer = setTimeout(() => {
      const pointsToAdd = isPremiumUser ? 5 : 1;
      const newEarnedPoints = earnedPoints + pointsToAdd;
      const newReadInsights = new Set(readInsights);
      newReadInsights.add(insightId);
      // const newReadInsights = Array.from(new Set([...readInsights, insightId]));
      
      setReadInsights(newReadInsights);
      setEarnedPoints(newEarnedPoints);
      saveToLocalStorage(Array.from(newReadInsights) as any, Array.from(sharedInsights) as any, newEarnedPoints);
      
      setToastMessage(`You earned ${pointsToAdd} point${pointsToAdd > 1 ? 's' : ''} for reading this insight!`);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 3000);
      
      // Clear the timer
      setTimers(prev => {
        const newTimers = { ...prev };
        delete newTimers[insightId];
        return newTimers;
      });
    }, 15000); // 15 seconds

    setTimers(prev => ({ ...prev, [insightId]: timer }));
  };

  const handleShare = (insight: Insight) => {
    setSelectedInsight(insight);
    setShowShareModal(true);
  };

  type Platform = 'twitter' | 'facebook' | 'linkedin' | 'whatsapp';

  const shareToSocialMedia = (platform: Platform) => {
    if (!selectedInsight) return;
    const userName = 'John Doe'; // This should come from user data
    const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(userName)}`;
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
      awardSharingPoints();
    }
    
    setShowShareModal(false);
  };

  const copyLink = () => {
    if (!selectedInsight) return;
    const userName = 'John Doe'; // This should come from user data
    const referralLink = `${window.location.origin}/signup?ref=${encodeURIComponent(userName)}`;
    const insightUrl = `${referralLink}&insight=${selectedInsight.id}`;
    navigator.clipboard.writeText(insightUrl);
    awardSharingPoints();
    setToastMessage(`Link copied! You earned ${isPremiumUser ? 10 : 5} points for sharing this insight!`);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
    setShowShareModal(false);
  };

  const awardSharingPoints = () => {
    if (!selectedInsight) return;
    // Award points only if not already shared
    if (!sharedInsights.has(selectedInsight.id)) {
      const pointsToAdd = isPremiumUser ? 10 : 5;
      const newEarnedPoints = earnedPoints + pointsToAdd;
      const newSharedInsights = new Set([...sharedInsights, selectedInsight.id]);
      
      setEarnedPoints(newEarnedPoints);
      setSharedInsights(newSharedInsights);
      saveToLocalStorage(Array.from(readInsights) as any , Array.from(newSharedInsights) as any, newEarnedPoints);
      
      if (!showToast) {
        setToastMessage(`You earned ${pointsToAdd} points for sharing this insight!`);
        setShowToast(true);
        setTimeout(() => setShowToast(false), 3000);
      }
    }
  };

  // Start timers for unread insights when component mounts
  useEffect(() => {
    insights.forEach(insight => {
      const insightIdStr = insight.id.toString();
      if (!readInsights.has(insightIdStr) && insight.id <= 2) { // Only for first 2 insights
        startReadingTimer(insightIdStr);
      }
    });

    // Cleanup timers on unmount
    return () => {
      Object.values(timers).forEach(timer => clearTimeout(timer));
    };
  }, [[insights, readInsights]]);

  const getButtonState = (insightId: string) => {
    if (readInsights.has(insightId)) {
      return 'read';
    }
    if (timers[insightId]) {
      return 'reading';
    }
    return 'inactive';
  };

  const getButtonText = (insightId: string) => {
    const state = getButtonState(insightId);
    
    switch (state) {
      case 'read':
        return 'Insight read';
      case 'reading':
        return `Reading... (+${isPremiumUser ? 5 : 1} point${isPremiumUser ? 's' : ''} in 15s)`;
      case 'inactive':
        return 'Mark as Read';
    }
  };

  const getButtonStyle = (insightId: string) => {
    const state = getButtonState(insightId);
    const baseStyle = {
      padding: '12px 20px',
      borderRadius: '8px',
      border: 'none',
      fontSize: '14px',
      fontWeight: '600',
      cursor: state === 'inactive' ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.3s ease',
      minWidth: '200px',
      whiteSpace: 'nowrap'
    };
    
    switch (state) {
      case 'read':
        return {
          ...baseStyle,
          backgroundColor: '#10b981',
          color: '#ffffff'
        };
      case 'reading':
        return {
          ...baseStyle,
          backgroundColor: '#f97316',
          color: '#ffffff'
        };
      case 'inactive':
        return {
          ...baseStyle,
          backgroundColor: '#e5e7eb',
          color: '#9ca3af'
        };
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex' }}>
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />

      {/* Main Content */}
      <div style={{ 
        flex: 1, 
        marginLeft: '0',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <header style={{ 
          backgroundColor: '#ffffff', 
          borderBottom: '1px solid #e5e7eb', 
          padding: '16px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
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
                color: '#6b7280',
                cursor: 'pointer',
                marginRight: '16px'
              }}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              <i className="ri-menu-line" style={{ fontSize: '20px' }}></i>
            </button>
            <h1 style={{ 
              fontSize: '24px', 
              fontWeight: 'bold', 
              color: '#111827',
              margin: 0
            }}>AI Insights Feed</h1>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ 
              backgroundColor: '#f3f4f6', 
              padding: '8px 16px', 
              borderRadius: '20px',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151'
            }}>
              Points: {earnedPoints}
            </div>
            <div style={{ 
              backgroundColor: '#f3f4f6', 
              padding: '8px 16px', 
              borderRadius: '20px',
              fontSize: '14px',
              fontWeight: '500',
              color: '#374151'
            }}>
              {isPremiumUser ? 'Premium' : 'Free'} User
            </div>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              backgroundColor: '#f97316', 
              borderRadius: '50%', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <i className="ri-user-line" style={{ color: '#ffffff', fontSize: '18px' }}></i>
            </div>
          </div>
        </header>

        {/* Content */}
        <div style={{ flex: 1, padding: '24px' }}>
          {/* Stats Cards */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: window.innerWidth >= 1024 ? 'repeat(4, 1fr)' : window.innerWidth >= 640 ? 'repeat(2, 1fr)' : '1fr',
            gap: '24px',
            marginBottom: '32px'
          }}>
            <div style={{ 
              backgroundColor: '#ffffff', 
              padding: '24px', 
              borderRadius: '12px', 
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>Total Insights</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>24</p>
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
                  <i className="ri-lightbulb-line" style={{ color: '#3b82f6', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>

            <div style={{ 
              backgroundColor: '#ffffff', 
              padding: '24px', 
              borderRadius: '12px', 
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>Read Today</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>{readInsights.size}</p>
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
              padding: '24px', 
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
                  }}>{earnedPoints}</p>
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
              padding: '24px', 
              borderRadius: '12px', 
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)' 
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    margin: '0 0 4px 0' 
                  }}>Shared</p>
                  <p style={{ 
                    fontSize: '24px', 
                    fontWeight: 'bold', 
                    color: '#111827',
                    margin: 0
                  }}>{sharedInsights.size}</p>
                </div>
                <div style={{ 
                  width: '48px', 
                  height: '48px', 
                  backgroundColor: '#f3e8ff', 
                  borderRadius: '12px', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <i className="ri-share-line" style={{ color: '#8b5cf6', fontSize: '20px' }}></i>
                </div>
              </div>
            </div>
          </div>

          {/* Insights List */}
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column',
            gap: '32px'
          }}>
            {insights.map((insight, index) => {
              const isLocked = !isPremiumUser && index >= 2;
              
              return (
                <div key={insight.id} style={{ 
                  backgroundColor: '#ffffff', 
                  borderRadius: '16px', 
                  overflow: 'hidden', 
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                  transition: 'box-shadow 0.3s ease',
                  position: 'relative'
                }}>
                  <img 
                    src={insight.image} 
                    alt={insight.title}
                    style={{ 
                      width: '100%', 
                      height: '250px', 
                      objectFit: 'cover',
                      objectPosition: 'top',
                      filter: isLocked ? 'blur(8px)' : 'none'
                    }}
                  />
                  
                  <div style={{ padding: '32px', position: 'relative' }}>
                    {/* Header */}
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '12px', 
                      marginBottom: '16px' 
                    }}>
                      <span style={{ 
                        backgroundColor: '#f3f4f6', 
                        color: '#374151', 
                        padding: '6px 16px', 
                        borderRadius: '20px', 
                        fontSize: '14px', 
                        fontWeight: '500' 
                      }}>
                        {insight.category}
                      </span>
                      <span style={{ 
                        fontSize: '14px', 
                        color: '#6b7280' 
                      }}>
                        {insight.readTime}
                      </span>
                      <span style={{ 
                        fontSize: '14px', 
                        color: '#6b7280' 
                      }}>
                        {insight.date}
                      </span>
                    </div>
                    
                    <h2 style={{ 
                      fontSize: window.innerWidth >= 768 ? '24px' : '20px', 
                      fontWeight: 'bold', 
                      color: '#111827', 
                      marginBottom: '24px',
                      lineHeight: '1.3'
                    }}>
                      {insight.title}
                    </h2>

                    {/* Content Sections - Only for first 2 insights */}
                    {!isLocked && insight.whatChanged && (
                      <div style={{ 
                        display: 'flex', 
                        flexDirection: window.innerWidth >= 1024 ? 'row' : 'column',
                        gap: '24px', 
                        marginBottom: '32px' 
                      }}>
                        {/* What Changed */}
                        <div style={{ 
                          flex: 1,
                          backgroundColor: '#eff6ff', 
                          padding: '20px', 
                          borderRadius: '12px',
                          border: '1px solid #3b82f6'
                        }}>
                          <h3 style={{ 
                            fontSize: '16px', 
                            fontWeight: 'bold', 
                            color: '#1d4ed8', 
                            marginBottom: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                          }}>
                            <i className="ri-refresh-line" style={{ fontSize: '18px' }}></i>
                            What Changed
                          </h3>
                          <p style={{ 
                            fontSize: '14px', 
                            color: '#4b5563', 
                            lineHeight: '1.6',
                            margin: 0
                          }}>
                            {insight.whatChanged}
                          </p>
                        </div>

                        {/* Why it matters */}
                        <div style={{ 
                          flex: 1,
                          backgroundColor: '#fef7ff', 
                          padding: '20px', 
                          borderRadius: '12px',
                          border: '1px solid #a855f7'
                        }}>
                          <h3 style={{ 
                            fontSize: '16px', 
                            fontWeight: 'bold', 
                            color: '#7c3aed', 
                            marginBottom: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                          }}>
                            <i className="ri-question-line" style={{ fontSize: '18px' }}></i>
                            Why it matters
                          </h3>
                          <p style={{ 
                            fontSize: '14px', 
                            color: '#4b5563', 
                            lineHeight: '1.6',
                            margin: 0
                          }}>
                            {insight.whyItMatters}
                          </p>
                        </div>

                        {/* Action to take */}
                        <div style={{ 
                          flex: 1,
                          backgroundColor: '#f0fdf4', 
                          padding: '20px', 
                          borderRadius: '12px',
                          border: '1px solid #22c55e'
                        }}>
                          <h3 style={{ 
                            fontSize: '16px', 
                            fontWeight: 'bold', 
                            color: '#16a34a', 
                            marginBottom: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                          }}>
                            <i className="ri-flashlight-line" style={{ fontSize: '18px' }}></i>
                            Action to take
                          </h3>
                          <p style={{ 
                            fontSize: '14px', 
                            color: '#4b5563', 
                            lineHeight: '1.6',
                            margin: 0
                          }}>
                            {insight.actionToTake}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Premium Overlay for locked content */}
                    {isLocked && (
                      <div style={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        backgroundColor: 'rgba(0, 0, 0, 0.9)',
                        color: '#ffffff',
                        padding: '32px',
                        borderRadius: '16px',
                        textAlign: 'center',
                        zIndex: 10,
                        minWidth: '300px'
                      }}>
                        <i className="ri-vip-crown-line" style={{ fontSize: '48px', color: '#f59e0b', marginBottom: '16px' }}></i>
                        <h3 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '12px', margin: '0 0 12px 0' }}>
                          Upgrade to Pro
                        </h3>
                        <p style={{ fontSize: '14px', color: '#d1d5db', marginBottom: '20px', margin: '0 0 20px 0' }}>
                          Unlock full insights and earn more points
                        </p>
                        <button style={{
                          backgroundColor: '#f97316',
                          color: '#ffffff',
                          padding: '12px 24px',
                          borderRadius: '8px',
                          border: 'none',
                          fontSize: '14px',
                          fontWeight: '600',
                          cursor: 'pointer',
                          whiteSpace: 'nowrap'
                        }}>
                          Upgrade Now
                        </button>
                      </div>
                    )}

                    {/* Blur overlay for locked content */}
                    {isLocked && (
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        backgroundColor: 'rgba(255, 255, 255, 0.8)',
                        backdropFilter: 'blur(4px)',
                        zIndex: 5
                      }} />
                    )}
                    
                    {/* Action Buttons */}
                    <div style={{ 
                      display: 'flex', 
                      flexDirection: window.innerWidth >= 640 ? 'row' : 'column',
                      gap: '16px',
                      position: 'relative',
                      zIndex: isLocked ? 1 : 'auto'
                    }}>
                      {!isLocked ? (
                        <>
                          <button
                            style={getButtonStyle(insight.id.toString())}
                            disabled={getButtonState(insight.id.toString()) === 'inactive'}
                          >
                            {getButtonState(insight.id.toString()) === 'read' && (
                              <i className="ri-check-line" style={{ marginRight: '8px' }}></i>
                            )}
                            {getButtonText(insight.id.toString())}
                          </button>
                          
                          <button
                            onClick={() => handleShare({...insight,
                                                      id: insight.id.toString(),
                                                      viewed: false})}
                            style={{ 
                              flex: 1,
                              backgroundColor: sharedInsights.has(insight.id) ? '#10b981' : '#3b82f6', 
                              color: '#ffffff', 
                              padding: '12px 20px', 
                              borderRadius: '8px', 
                              border: 'none', 
                              fontSize: '14px', 
                              fontWeight: '600', 
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              transition: 'background-color 0.3s ease',
                              whiteSpace: 'nowrap'
                            }}
                            onMouseOver={(e) => e.currentTarget.style.backgroundColor = sharedInsights.has(insight.id) ? '#059669' : '#2563eb'}
                            onMouseOut={(e) => e.currentTarget.style.backgroundColor = sharedInsights.has(insight.id) ? '#10b981' : '#3b82f6'}
                          >
                            <i className={sharedInsights.has(insight.id) ? 'ri-check-line' : 'ri-share-line'} style={{ marginRight: '8px' }}></i>
                            {sharedInsights.has(insight.id) ? 'Shared' : `Share (+${isPremiumUser ? 10 : 5} points)`}
                          </button>
                        </>
                      ) : (
                        <button
                          style={{ 
                            flex: 1,
                            backgroundColor: '#e5e7eb', 
                            color: '#9ca3af', 
                            padding: '12px 20px', 
                            borderRadius: '8px', 
                            border: 'none', 
                            fontSize: '14px', 
                            fontWeight: '600', 
                            cursor: 'not-allowed',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            whiteSpace: 'nowrap'
                          }}
                          disabled
                        >
                          <i className="ri-lock-line" style={{ marginRight: '8px' }}></i>
                          Premium Required
                        </button>
                      )}
                      
                      <button
                        onClick={() => window.open(insight.source, '_blank')}
                        style={{ 
                          flex: 1,
                          backgroundColor: '#f3f4f6', 
                          color: '#374151', 
                          padding: '12px 20px', 
                          borderRadius: '8px', 
                          border: 'none', 
                          fontSize: '14px', 
                          fontWeight: '600', 
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'background-color 0.3s ease',
                          whiteSpace: 'nowrap'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#e5e7eb'}
                        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
                      >
                        <i className="ri-external-link-line" style={{ marginRight: '8px' }}></i>
                        View Details
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
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
          maxWidth: '400px',
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
            style={{ 
              position: 'fixed', 
              inset: 0, 
              backgroundColor: 'rgba(0, 0, 0, 0.5)', 
              zIndex: 40 
            }}
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
              Share Insight
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

      <style jsx>{`
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

