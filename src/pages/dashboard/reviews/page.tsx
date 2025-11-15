
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';

export default function ReviewsPage() {
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('form');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);
  const [readStatus, setReadStatus] = useState<{[key: number]: boolean}>({});

  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  // Review form state
  const [reviewForm, setReviewForm] = useState({
    reviewTitle: '',
    rating: 0,
    reviewText: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Listen for messages being read from conversation page and page visibility changes
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

    // Listen for focus events to reload read status when returning to page
    const handleFocus = () => {
      const savedReadStatus = localStorage.getItem('reviewReadStatus');
      if (savedReadStatus) {
        setReadStatus(JSON.parse(savedReadStatus));
      }
    };

    window.addEventListener('conversationRead', handleConversationRead as EventListener);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      window.removeEventListener('conversationRead', handleConversationRead as EventListener);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  // Reload read status when component mounts or when returning from other pages
  useEffect(() => {
    const savedReadStatus = localStorage.getItem('reviewReadStatus');
    if (savedReadStatus) {
      setReadStatus(JSON.parse(savedReadStatus));
    }
  }, [activeTab]); // Reload when switching tabs

  const isMobile = windowWidth < 640;
  const isTablet = windowWidth >= 640 && windowWidth < 1024;

  const userReviews = [
    {
      id: 1,
      businessName: 'TechFlow Solutions',
      reviewTitle: 'Excellent SaaS Platform',
      rating: 5,
      reviewText: 'This platform has revolutionized our workflow. The AI features are incredibly intuitive and have saved us countless hours.',
      dateSubmitted: '2024-01-15',
      status: 'published',
      adminResponse: true,
      conversationCount: 3,
      category: 'Software',
      helpful: 24,
      verified: true,
      hasConversation: true,
      unreadMessages: readStatus[1] ? 0 : 2
    },
    {
      id: 2,
      businessName: 'GreenLeaf Organics',
      reviewTitle: 'Great Products, Slow Delivery',
      rating: 4,
      reviewText: 'Love the quality of organic products, but delivery took longer than expected. Customer service was helpful though.',
      dateSubmitted: '2024-01-10',
      status: 'published',
      adminResponse: true,
      conversationCount: 2,
      category: 'E-commerce',
      helpful: 18,
      verified: true,
      hasConversation: true,
      unreadMessages: 0
    },
    {
      id: 3,
      businessName: 'HealthFirst Clinic',
      reviewTitle: 'Outstanding Medical Care',
      rating: 5,
      reviewText: 'Dr. Smith and the entire team provided exceptional care. The new telemedicine features are very convenient.',
      dateSubmitted: '2024-01-08',
      status: 'published',
      adminResponse: false,
      conversationCount: 0,
      category: 'Healthcare',
      helpful: 31,
      verified: true,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 4,
      businessName: 'EduBright Academy',
      reviewTitle: 'Mixed Experience',
      rating: 3,
      reviewText: 'The course content is good but the platform can be buggy sometimes. Hope they fix the technical issues soon.',
      dateSubmitted: '2024-01-05',
      status: 'under-review',
      adminResponse: true,
      conversationCount: 5,
      category: 'Education',
      helpful: 12,
      verified: false,
      hasConversation: true,
      unreadMessages: readStatus[4] ? 0 : 1
    },
    {
      id: 5,
      businessName: 'AutoCare Express',
      reviewTitle: 'Quick and Professional Service',
      rating: 4,
      reviewText: 'Got my car serviced quickly and professionally. Pricing was fair and staff was knowledgeable.',
      dateSubmitted: '2024-01-03',
      status: 'published',
      adminResponse: false,
      conversationCount: 0,
      category: 'Automotive',
      helpful: 15,
      verified: true,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 6,
      businessName: 'FitLife Gym Network',
      reviewTitle: 'Amazing Facilities',
      rating: 5,
      reviewText: 'State-of-the-art equipment and excellent trainers. The AI workout recommendations are spot on!',
      dateSubmitted: '2024-01-01',
      status: 'published',
      adminResponse: true,
      conversationCount: 1,
      category: 'Fitness',
      helpful: 28,
      verified: true,
      hasConversation: true,
      unreadMessages: 0
    }
  ];

  // Filter reviews for conversations tab (only those with conversations)
  const reviewsWithConversations = userReviews.filter(review => review.hasConversation);

  // Calculate total unread messages for sidebar
  const totalUnreadMessages = userReviews.reduce((sum, review) => sum + review.unreadMessages, 0);

  // Store unread count in localStorage for sidebar access
  useEffect(() => {
    localStorage.setItem('reviewsUnreadCount', totalUnreadMessages.toString());
    // Dispatch custom event to notify sidebar of count change
    window.dispatchEvent(new CustomEvent('reviewsUnreadCountChanged', { 
      detail: { count: totalUnreadMessages } 
    }));
  }, [totalUnreadMessages]);

  const filteredReviews = userReviews.filter(review => {
    const matchesSearch = review.businessName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         review.reviewTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         review.reviewText.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || review.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const filteredConversations = reviewsWithConversations.filter(review => {
    const matchesSearch = review.businessName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         review.reviewTitle.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewForm.reviewTitle || !reviewForm.rating || !reviewForm.reviewText) {
      alert('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    
    // Simulate API call
    setTimeout(() => {
    console.log('Submitting review:', reviewForm);

      setToastMessage('🎉 Review submitted successfully!');
      setShowToast(true);

      setTimeout(() => setShowToast(false), 3000);

      setReviewForm({
        reviewTitle: '',
        rating: 0,
        reviewText: ''
      });
      setIsSubmitting(false);
    }, 1000);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-green-100 text-green-600';
      case 'under-review':
        return 'bg-yellow-100 text-yellow-600';
      case 'rejected':
        return 'bg-red-100 text-red-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const renderStars = (rating: number, interactive = false) => {
    return Array.from({ length: 5 }, (_, index) => (
      <i
        key={index}
        className={`${interactive ? 'cursor-pointer hover:text-yellow-500' : ''} ri-star-${index < rating ? 'fill' : 'line'} text-yellow-400`}
        onClick={interactive ? () => setReviewForm({...reviewForm, rating: index + 1}) : undefined}
      ></i>
    ));
  };

  const handleViewConversation = (reviewId: number) => {
    // Mark messages as read when viewing conversation
    setReadStatus(prev => {
      const newStatus = {
        ...prev,
        [reviewId]: true
      };
      localStorage.setItem('reviewReadStatus', JSON.stringify(newStatus));
      return newStatus;
    });
    
    navigate(`/dashboard/conversations/${reviewId}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />
      
      {/* Main Content */}
      <div className={`flex-1 ${isMobile ? 'ml-0' : '0'} flex flex-col`}>
        <div className={`flex-1 ${isMobile ? 'p-4' : isTablet ? 'p-6' : 'p-8'}`}>
          <div className="max-w-7xl mx-auto">
            {/* Tabs at the top */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6">
              <div className="border-b border-gray-200">
                <nav className="flex">
                  <button
                    onClick={() => setActiveTab('form')}
                    className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'form'
                        ? 'border-orange-500 text-orange-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <i className="ri-edit-line mr-2"></i>
                    Submit Review
                  </button>
                  <button
                    onClick={() => setActiveTab('my-reviews')}
                    className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'my-reviews'
                        ? 'border-orange-500 text-orange-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <i className="ri-star-line mr-2"></i>
                    My Reviews ({userReviews.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('conversations')}
                    className={`px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === 'conversations'
                        ? 'border-orange-500 text-orange-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <i className="ri-message-3-line mr-2"></i>
                    Conversations ({reviewsWithConversations.length})
                    {totalUnreadMessages > 0 && (
                      <span className="ml-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                        {totalUnreadMessages}
                      </span>
                    )}
                  </button>
                </nav>
              </div>
            </div>

            {/* Header */}
            <div className={`${isMobile ? 'mb-6' : 'mb-8'}`}>
              <h1 className={`${isMobile ? 'text-2xl' : isTablet ? 'text-3xl' : 'text-4xl'} font-bold text-gray-900 mb-2`}>
                Reviews
              </h1>
              <p className={`text-gray-600 ${isMobile ? 'text-sm' : 'text-base'}`}>
                Submit new reviews and manage your existing reviews and conversations
              </p>
            </div>

            {/* Review Submission Form - Default view */}
            {activeTab === 'form' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Submit a New Review</h3>
                  <p className="text-sm text-gray-600 mt-1">Share your experience with a business or service</p>
                </div>
                
                <form onSubmit={handleReviewSubmit} className="p-6">
                  {/* Review Title */}
                  <div className="mb-6">
                    <label htmlFor="reviewTitle" className="block text-sm font-medium text-gray-700 mb-2">
                      Review Title *
                    </label>
                    <input
                      type="text"
                      id="reviewTitle"
                      value={reviewForm.reviewTitle}
                      onChange={(e) => setReviewForm({...reviewForm, reviewTitle: e.target.value})}
                      placeholder="Give your review a title"
                      className="w-full px-3 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none"
                      required
                    />
                  </div>

                  {/* Rating */}
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rating *
                    </label>
                    <div className="flex items-center gap-2">
                      <div className="flex">
                        {renderStars(reviewForm.rating, true)}
                      </div>
                      <span className="text-sm text-gray-600">
                        {reviewForm.rating > 0 ? `${reviewForm.rating}/5` : 'Click to rate'}
                      </span>
                    </div>
                  </div>

                  {/* Review Text */}
                  <div className="mb-6">
                    <label htmlFor="reviewText" className="block text-sm font-medium text-gray-700 mb-2">
                      Your Review *
                    </label>
                    <textarea
                      id="reviewText"
                      rows={4}
                      value={reviewForm.reviewText}
                      onChange={(e) => setReviewForm({...reviewForm, reviewText: e.target.value})}
                      placeholder="Share your experience..."
                      className="w-full px-3 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none resize-none"
                      maxLength={500}
                      required
                    />
                    <div className="mt-2 text-xs text-gray-500">
                      {reviewForm.reviewText.length}/500 characters
                    </div>
                  </div>

                  {/* Submit Button */}
                  <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} gap-3 justify-end`}>
                    <button
                      type="button"
                      onClick={() => setReviewForm({
                        reviewTitle: '',
                        rating: 0,
                        reviewText: ''
                      })}
                      className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg text-sm font-medium bg-white hover:bg-gray-50 transition-colors cursor-pointer whitespace-nowrap"
                    >
                      Clear Form
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="bg-orange-500 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors cursor-pointer whitespace-nowrap"
                    >
                      {isSubmitting ? (
                        <>
                          <i className="ri-loader-4-line animate-spin mr-2"></i>
                          Submitting...
                        </>
                      ) : (
                        <>
                          <i className="ri-send-plane-line mr-2"></i>
                          Submit Review
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* My Reviews Tab */}
            {activeTab === 'my-reviews' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                {/* Search and Filters */}
                <div className="p-6 border-b border-gray-200">
                  <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} gap-4`}>
                    {/* Search */}
                    <div className="flex-1">
                      <div className="relative">
                        <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                        <input
                          type="text"
                          placeholder="Search reviews..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none"
                        />
                      </div>
                    </div>

                    {/* Status Filter */}
                    <select
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value)}
                      className="border border-gray-300 text-gray-700 py-3 px-4 pr-8 rounded-lg text-sm font-medium bg-white hover:bg-gray-50 focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none"
                    >
                      <option value="all">All Status</option>
                      <option value="published">Published</option>
                      <option value="under-review">Under Review</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                </div>

                {/* Reviews List */}
                <div className="p-6">
                  <div className="space-y-6">
                    {filteredReviews.map((review) => (
                      <div key={review.id} className="bg-gray-50 rounded-lg p-6 border border-gray-200">
                        {/* Review Header */}
                        <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} ${isMobile ? 'items-start' : 'items-center'} justify-between ${isMobile ? 'gap-3' : 'gap-0'} mb-4`}>
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900 mb-1">
                              {review.reviewTitle}
                            </h3>
                            <div className="flex items-center gap-3">
                              <span className="text-sm text-gray-600">{review.businessName}</span>
                              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
                                {review.category}
                              </span>
                              {review.verified && (
                                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full flex items-center">
                                  <i className="ri-verified-badge-line mr-1"></i>
                                  Verified
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(review.status)}`}>
                              {review.status.replace('-', ' ').toUpperCase()}
                            </span>
                            <span className="text-sm text-gray-500">
                              {new Date(review.dateSubmitted).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        {/* Rating */}
                        <div className="flex items-center gap-2 mb-3">
                          <div className="flex">
                            {renderStars(review.rating)}
                          </div>
                          <span className="text-sm text-gray-600">({review.rating}/5)</span>
                        </div>

                        {/* Review Text */}
                        <p className="text-gray-700 mb-4 leading-relaxed">
                          {review.reviewText}
                        </p>

                        {/* Review Stats */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <span className="text-sm text-gray-600 flex items-center">
                              <i className="ri-thumb-up-line mr-1"></i>
                              {review.helpful} helpful
                            </span>
                            {review.adminResponse && (
                              <span className="text-sm text-blue-600 flex items-center">
                                <i className="ri-reply-line mr-1"></i>
                                Admin responded
                              </span>
                            )}
                            {review.conversationCount > 0 && (
                              <span className="text-sm text-orange-600 flex items-center">
                                <i className="ri-message-3-line mr-1"></i>
                                {review.conversationCount} messages
                              </span>
                            )}
                            {review.unreadMessages > 0 && (
                              <span className="text-sm text-red-600 flex items-center font-medium">
                                <i className="ri-notification-line mr-1"></i>
                                {review.unreadMessages} unread messages
                              </span>
                            )}
                          </div>
                          {review.hasConversation && (
                            <button
                              onClick={() => handleViewConversation(review.id)}
                              className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors cursor-pointer whitespace-nowrap"
                            >
                              View Conversation
                            </button>
                          )}
                        </div>
                      </div>
                    ))}

                    {filteredReviews.length === 0 && (
                      <div className="text-center py-12">
                        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                          <i className="ri-star-line text-2xl text-gray-400"></i>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          No reviews found
                        </h3>
                        <p className="text-gray-600">
                          Try adjusting your search terms or filters
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Conversations Tab */}
            {activeTab === 'conversations' && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                {/* Search */}
                <div className="p-6 border-b border-gray-200">
                  <div className="relative">
                    <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input
                      type="text"
                      placeholder="Search conversations..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none"
                    />
                  </div>
                </div>

                {/* Conversations List */}
                <div className="p-6">
                  <div className="space-y-4">
                    {filteredConversations.map((review) => (
                      <div key={review.id} className="bg-gray-50 rounded-lg p-6 border border-gray-200 hover:border-orange-300 transition-colors cursor-pointer"
                           onClick={() => handleViewConversation(review.id)}>
                        <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} ${isMobile ? 'items-start' : 'items-center'} justify-between ${isMobile ? 'gap-3' : 'gap-0'}`}>
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="text-lg font-semibold text-gray-900">
                                {review.reviewTitle}
                              </h3>
                              <span className="text-sm text-gray-600">
                                {review.businessName}
                              </span>
                              {review.unreadMessages > 0 && (
                                <span className="bg-red-500 text-white text-xs rounded-full px-2 py-1 font-medium">
                                  {review.unreadMessages} unread
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mb-2">
                              <div className="flex">
                                {renderStars(review.rating)}
                              </div>
                              <span className="text-sm text-gray-600">({review.rating}/5)</span>
                            </div>
                            <p className="text-gray-600 text-sm mb-2">
                              {review.reviewText.substring(0, 100)}...
                            </p>
                            <span className="text-xs text-gray-500">
                              {review.conversationCount} messages • {new Date(review.dateSubmitted).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="flex items-center">
                            <i className="ri-arrow-right-s-line text-gray-400"></i>
                          </div>
                        </div>
                      </div>
                    ))}

                    {filteredConversations.length === 0 && (
                      <div className="text-center py-12">
                        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                          <i className="ri-message-3-line text-2xl text-gray-400"></i>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          No conversations found
                        </h3>
                        <p className="text-gray-600">
                          Start conversations by submitting reviews and receiving admin responses
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        {showToast && (
  <div
    style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      backgroundColor: '#10b981',
      color: 'white',
      padding: '12px 20px',
      borderRadius: '8px',
      fontSize: '14px',
      transition: '0.3s ease',
      animation: 'slideIn 0.3s forwards'
    }}
  >
    {toastMessage}
  </div>)}
        
      </div>
    </div>
  );
}
