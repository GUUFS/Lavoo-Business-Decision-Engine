
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminReviews() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [selectedRating, setSelectedRating] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [dropdownOpen, setDropdownOpen] = useState<number | null>(null);
  const [responseText, setResponseText] = useState('');
  const [showResponseForm, setShowResponseForm] = useState<number | null>(null);
  const [showConversation, setShowConversation] = useState<number | null>(null);
  const [conversations, setConversations] = useState<{[key: number]: Array<{id: number, message: string, sender: 'admin' | 'user', timestamp: string, isRead: boolean}>}>({});
  const [readStatus, setReadStatus] = useState<{[key: number]: boolean}>({});

  const reviewsPerPage = 10;

  // Mock data for conversations
  const mockConversations: {[key: number]: Array<{id: number, message: string, sender: 'admin' | 'user', timestamp: string, isRead: boolean}>} = {
    1: [
      {
        id: 1,
        message: "Thank you for your detailed feedback! We're thrilled to hear that our AI analysis platform has transformed your data analysis process.",
        sender: 'admin',
        timestamp: '2024-02-26T10:30:00Z',
        isRead: true
      },
      {
        id: 2,
        message: "You're welcome! The insights have been incredibly valuable for our decision-making process. Keep up the great work!",
        sender: 'user',
        timestamp: '2024-02-26T14:15:00Z',
        isRead: false
      },
      {
        id: 3,
        message: "I have a question about the export functionality. Is there a way to export the analysis in Excel format?",
        sender: 'user',
        timestamp: '2024-02-27T09:20:00Z',
        isRead: false
      },
      {
        id: 4,
        message: "Also, would it be possible to schedule automated reports? That would be really helpful for our weekly meetings.",
        sender: 'user',
        timestamp: '2024-02-27T09:25:00Z',
        isRead: false
      }
    ],
    3: [
      {
        id: 5,
        message: "We appreciate your positive feedback about our AI analysis and integration support. Your success is our priority!",
        sender: 'admin',
        timestamp: '2024-02-24T09:45:00Z',
        isRead: true
      },
      {
        id: 6,
        message: "The integration process was seamless thanks to your team's expertise. Looking forward to continued partnership!",
        sender: 'user',
        timestamp: '2024-02-24T16:20:00Z',
        isRead: true
      },
      {
        id: 7,
        message: "That's wonderful to hear! If you need any additional features or support, please don't hesitate to reach out.",
        sender: 'admin',
        timestamp: '2024-02-25T08:30:00Z',
        isRead: true
      },
      {
        id: 8,
        message: "Actually, I do have a feature request. Could you add support for real-time data streaming?",
        sender: 'user',
        timestamp: '2024-02-27T11:15:00Z',
        isRead: false
      }
    ]
  };

  useEffect(() => {
    setConversations(mockConversations);
    
    // Load read status from localStorage
    const savedReadStatus = localStorage.getItem('reviewReadStatus');
    if (savedReadStatus) {
      setReadStatus(JSON.parse(savedReadStatus));
    }
  }, []);

  // Save read status to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('reviewReadStatus', JSON.stringify(readStatus));
  }, [readStatus]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedFilter, selectedRating]);

  // Listen for messages being read from conversation page
  useEffect(() => {
    const handleConversationRead = (event: CustomEvent) => {
      const { reviewId } = event.detail;
      setReadStatus(prev => {
        const newStatus = {
          ...prev,
          [reviewId]: true
        };
        localStorage.setItem('reviewReadStatus', JSON.stringify(newStatus));
        return newStatus;
      });
    };

    // Also listen for page visibility changes to reload read status
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Page became visible, reload read status from localStorage
        const savedReadStatus = localStorage.getItem('reviewReadStatus');
        if (savedReadStatus) {
          setReadStatus(JSON.parse(savedReadStatus));
        }
      }
    };

    window.addEventListener('conversationRead', handleConversationRead as EventListener);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('conversationRead', handleConversationRead as EventListener);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // Mock reviews data
  const mockReviews = [
    {
      id: 1,
      user: 'Sarah Johnson',
      email: 'sarah.j@techstart.com',
      company: 'TechStart Solutions',
      rating: 5,
      title: 'Exceptional AI Analysis Platform',
      content: 'This AI business intelligence tool has completely transformed how we analyze our data. The insights are incredibly accurate and actionable.',
      date: '2024-02-26',
      status: 'published'
    },
    {
      id: 2,
      user: 'Michael Chen',
      email: 'michael.c@dataflow.com',
      company: 'DataFlow Analytics',
      rating: 4,
      title: 'Solid Performance with Room for Growth',
      content: 'Great tool overall. The AI recommendations are helpful, though I\'d love to see more customization options for industry-specific analysis.',
      date: '2024-02-25',
      status: 'published'
    },
    {
      id: 3,
      user: 'Emily Rodriguez',
      email: 'emily.r@startup.io',
      rating: 5,
      title: 'Game Changer for Our Business',
      content: 'As a startup, we needed data-driven insights without hiring a full analytics team. This AI analyst provides exactly what we need.',
      date: '2024-02-24',
      status: 'published'
    },
    {
      id: 4,
      user: 'David Park',
      email: 'david.p@enterprise.com',
      company: 'Enterprise Solutions Inc.',
      rating: 3,
      title: 'Good but Needs Improvement',
      content: 'The basic functionality works well, but we encountered some issues with large dataset processing. Customer support was responsive though.',
      date: '2024-02-23',
      status: 'published'
    },
    {
      id: 5,
      user: 'Lisa Thompson',
      email: 'lisa.t@marketing.co',
      company: 'Marketing Dynamics',
      rating: 5,
      title: 'Outstanding Customer Insights',
      content: 'The customer behavior analysis features are phenomenal. We\'ve increased our conversion rates by 40% using these insights.',
      date: '2024-02-22',
      status: 'published'
    },
    {
      id: 6,
      user: 'James Wilson',
      email: 'james.w@retail.com',
      company: 'Retail Chain Corp',
      rating: 2,
      title: 'Disappointing Experience',
      content: 'The interface is confusing and the results don\'t seem accurate for our retail data. Expected much better for the price point.',
      date: '2024-02-21',
      status: 'rejected'
    },
    {
      id: 7,
      user: 'Anna Martinez',
      email: 'anna.m@consulting.org',
      company: 'Strategic Consulting Group',
      rating: 4,
      title: 'Valuable for Client Projects',
      content: 'We use this for client consulting projects. The visualizations are impressive and help communicate insights effectively.',
      date: '2024-02-20',
      status: 'published'
    },
    {
      id: 8,
      user: 'Robert Kim',
      email: 'robert.k@finance.net',
      company: 'Financial Services Ltd',
      rating: 5,
      title: 'Perfect for Financial Analysis',
      content: 'Excellent tool for financial data analysis. The risk assessment features are particularly valuable for our investment decisions.',
      date: '2024-02-19',
      status: 'published'
    },
    {
      id: 9,
      user: 'Sophie Brown',
      email: 'sophie.b@healthcare.org',
      company: 'Healthcare Analytics',
      rating: 4,
      title: 'Great for Healthcare Data',
      content: 'Very useful for analyzing patient data trends. HIPAA compliance features give us confidence in data security.',
      date: '2024-02-18',
      status: 'published'
    },
    {
      id: 10,
      user: 'Mark Davis',
      email: 'mark.d@logistics.com',
      company: 'Global Logistics',
      rating: 3,
      title: 'Mixed Results',
      content: 'Works well for some types of analysis but struggles with our complex supply chain data. Still evaluating.',
      date: '2024-02-17',
      status: 'pending'
    },
    {
      id: 11,
      user: 'Jennifer Lee',
      email: 'jennifer.l@ecommerce.shop',
      company: 'E-commerce Solutions',
      rating: 5,
      title: 'Boosted Our Sales Analytics',
      content: 'Amazing insights into customer purchasing patterns. Helped us optimize our product recommendations significantly.',
      date: '2024-02-16',
      status: 'published'
    },
    {
      id: 12,
      user: 'Alex Turner',
      email: 'alex.t@manufacturing.co',
      company: 'Manufacturing Corp',
      rating: 4,
      title: 'Solid Manufacturing Analytics',
      content: 'Good for production efficiency analysis. The predictive maintenance features have saved us significant downtime.',
      date: '2024-02-15',
      status: 'published'
    }
  ];

  // Filter reviews
  const filteredReviews = mockReviews.filter(review => {
    const statusMatch = selectedFilter === 'all' || review.status === selectedFilter;
    const ratingMatch = selectedRating === 'all' || review.rating.toString() === selectedRating;
    return statusMatch && ratingMatch;
  }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  // Pagination
  const totalPages = Math.ceil(filteredReviews.length / reviewsPerPage);
  const startIndex = (currentPage - 1) * reviewsPerPage;
  const endIndex = startIndex + reviewsPerPage;
  const currentReviews = filteredReviews.slice(startIndex, endIndex);

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <i 
        key={i} 
        className={`ri-star-${i < rating ? 'fill' : 'line'} text-yellow-400`}
      ></i>
    ));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const sendResponse = (reviewId: number) => {
    if (!responseText.trim()) return;

    const newMessage = {
      id: Date.now(),
      message: responseText,
      sender: 'admin' as const,
      timestamp: new Date().toISOString(),
      isRead: true
    };

    setConversations(prev => ({
      ...prev,
      [reviewId]: [...(prev[reviewId] || []), newMessage]
    }));

    setResponseText('');
    setShowResponseForm(null);
    setDropdownOpen(null);
  };

  const getUnreadCount = (reviewId: number) => {
    if (readStatus[reviewId]) return 0;
    const reviewConversations = conversations[reviewId] || [];
    return reviewConversations.filter(msg => msg.sender === 'user' && !msg.isRead).length;
  };

  const markAsRead = (reviewId: number) => {
    const unreadCount = getUnreadCount(reviewId);
    
    if (unreadCount > 0) {
      // Mark as read locally
      setReadStatus(prev => {
        const newStatus = {
          ...prev,
          [reviewId]: true
        };
        // Save to localStorage immediately
        localStorage.setItem('reviewReadStatus', JSON.stringify(newStatus));
        return newStatus;
      });

      // Update conversations to mark messages as read
      setConversations(prev => ({
        ...prev,
        [reviewId]: (prev[reviewId] || []).map(msg => ({
          ...msg,
          isRead: true
        }))
      }));

      // Dispatch event to update sidebar badge
      window.dispatchEvent(new CustomEvent('reviewMessageRead', {
        detail: { reviewId, count: unreadCount }
      }));
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />
      
      <div className="flex-1 ml-0 flex flex-col">
        {/* Admin Header */}
        <div className="bg-white border-b border-gray-200 px-4 md:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100"
            >
              <i className="ri-menu-line text-xl"></i>
            </button>
            <div className="flex-1"></div>
            <div className="relative">
              <button 
                onClick={() => setIsProfileDropdownOpen(!isProfileDropdownOpen)}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-red-600"></i>
                </div>
                <span className="font-medium text-gray-900">Admin User</span>
                <i className="ri-arrow-down-s-line text-gray-400"></i>
              </button>
              
              {/* Profile Dropdown */}
              {isProfileDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3">
                    <i className="ri-user-line text-gray-500"></i>
                    Profile
                  </button>
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3">
                    <i className="ri-logout-box-line text-gray-500"></i>
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Customer Reviews</h1>
              <p className="text-gray-600">Manage and respond to customer feedback</p>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Status</label>
                  <select 
                    value={selectedFilter}
                    onChange={(e) => setSelectedFilter(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="all">All Reviews</option>
                    <option value="published">Published</option>
                    <option value="pending">Pending</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Rating</label>
                  <select 
                    value={selectedRating}
                    onChange={(e) => setSelectedRating(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="all">All Ratings</option>
                    <option value="5">5 Stars</option>
                    <option value="4">4 Stars</option>
                    <option value="3">3 Stars</option>
                    <option value="2">2 Stars</option>
                    <option value="1">1 Star</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Reviews List */}
            <div className="space-y-4">
              {currentReviews.map((review) => {
                const unreadCount = getUnreadCount(review.id);
                const hasConversations = conversations[review.id] && conversations[review.id].length > 0;
                
                return (
                  <div key={review.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                            <i className="ri-user-line text-red-600"></i>
                          </div>
                          <div>
                            <h3 className="font-semibold text-gray-900">{review.user}</h3>
                            <p className="text-sm text-gray-500">{review.email}</p>
                            {review.company && <p className="text-sm text-gray-500">{review.company}</p>}
                          </div>
                          <div className="flex">
                            {renderStars(review.rating)}
                          </div>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(review.status)}`}>
                            {review.status}
                          </span>
                        </div>
                        
                        <h4 className="font-medium text-gray-900 mb-2">{review.title}</h4>
                        <p className="text-gray-700 mb-4">{review.content}</p>
                        
                        <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                          <span>{review.date}</span>
                          {hasConversations && (
                            <span className="text-purple-600 font-medium">
                              {conversations[review.id].length} conversation{conversations[review.id].length !== 1 ? 's' : ''}
                            </span>
                          )}
                          {unreadCount > 0 && (
                            <span className="text-red-600 font-medium">
                              {unreadCount} unread message{unreadCount !== 1 ? 's' : ''}
                            </span>
                          )}
                        </div>

                        {/* Response Form */}
                        {showResponseForm === review.id && (
                          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                            <h5 className="font-medium text-gray-900 mb-3">Respond to Review</h5>
                            <textarea
                              value={responseText}
                              onChange={(e) => setResponseText(e.target.value)}
                              placeholder="Type your response..."
                              className="w-full min-h-20 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 resize-vertical mb-3"
                              rows={3}
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => sendResponse(review.id)}
                                disabled={!responseText.trim()}
                                className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              >
                                Send Response
                              </button>
                              <button
                                onClick={() => {
                                  setShowResponseForm(null);
                                  setResponseText('');
                                }}
                                className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Conversation View */}
                        {showConversation === review.id && hasConversations && (
                          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                            <h5 className="font-medium text-gray-900 mb-3">Conversation History</h5>
                            <div className="space-y-3 max-h-60 overflow-y-auto">
                              {conversations[review.id].map((message) => (
                                <div
                                  key={message.id}
                                  className={`flex ${message.sender === 'admin' ? 'justify-end' : 'justify-start'}`}
                                >
                                  <div
                                    className={`max-w-xs px-3 py-2 rounded-lg ${
                                      message.sender === 'admin'
                                        ? 'bg-red-600 text-white'
                                        : 'bg-white text-gray-900 border border-gray-200'
                                    }`}
                                  >
                                    <p className="text-sm">{message.message}</p>
                                    <p className={`text-xs mt-1 ${
                                      message.sender === 'admin' ? 'text-red-100' : 'text-gray-500'
                                    }`}>
                                      {message.sender === 'admin' ? 'Admin' : review.user} • {formatTimestamp(message.timestamp)}
                                    </p>
                                  </div>
                                </div>
                              ))}
                            </div>
                            <button
                              onClick={() => setShowConversation(null)}
                              className="mt-3 px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                            >
                              Close
                            </button>
                          </div>
                        )}
                      </div>
                      
                      {/* Actions */}
                      {review.status !== 'rejected' && (
                        <div className="relative ml-4">
                          <button
                            onClick={() => setDropdownOpen(dropdownOpen === review.id ? null : review.id)}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                          >
                            <i className="ri-more-2-line text-lg"></i>
                          </button>
                          
                          {dropdownOpen === review.id && (
                            <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-10">
                              <button
                                onClick={() => {
                                  setShowResponseForm(review.id);
                                  setDropdownOpen(null);
                                }}
                                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
                              >
                                <i className="ri-reply-line text-gray-500"></i>
                                Respond
                              </button>
                              {hasConversations && (
                                <Link
                                  to={`/admin/conversations/${review.id}`}
                                  onClick={() => {
                                    markAsRead(review.id);
                                    setDropdownOpen(null);
                                  }}
                                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
                                >
                                  <i className="ri-chat-3-line text-gray-500"></i>
                                  View Conversations
                                </Link>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  
                  <div className="flex gap-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`px-3 py-2 text-sm font-medium rounded-lg ${
                            currentPage === pageNum
                              ? 'bg-red-600 text-white'
                              : 'text-gray-500 bg-white border border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}

            {/* Pagination Info */}
            <div className="mt-4 text-center text-sm text-gray-600">
              Showing {startIndex + 1} to {Math.min(endIndex, filteredReviews.length)} of {filteredReviews.length} reviews
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}