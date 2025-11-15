import { useState, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminConversations() {
  const { reviewId } = useParams();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [conversations, setConversations] = useState<Array<{id: number, message: string, sender: 'admin' | 'user', timestamp: string, isRead: boolean}>>([]);
  const [reviewData, setReviewData] = useState<any>(null);

  // Mock data - in real app this would come from API
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
      id: 3,
      user: 'Emily Rodriguez',
      email: 'emily.r@startup.io',
      rating: 5,
      title: 'Game Changer for Our Business',
      content: 'As a startup, we needed data-driven insights without hiring a full analytics team. This AI analyst provides exactly what we need.',
      date: '2024-02-24',
      status: 'published'
    }
  ];

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
    if (reviewId) {
      const review = mockReviews.find(r => r.id === parseInt(reviewId));
      setReviewData(review);
      
      const reviewConversations = mockConversations[parseInt(reviewId)] || [];
      
      // Count unread user messages before marking as read
      const unreadUserMessages = reviewConversations.filter(msg => 
        msg.sender === 'user' && !msg.isRead
      ).length;
      
      // Mark messages as read when viewing conversation
      const updatedConversations = reviewConversations.map(msg => ({
        ...msg,
        isRead: true
      }));
      setConversations(updatedConversations);
      
      // Dispatch event to update sidebar badge counts and mark as read in reviews page
      if (unreadUserMessages > 0) {
        // Update sidebar badge
        window.dispatchEvent(new CustomEvent('reviewMessageRead', {
          detail: { reviewId: parseInt(reviewId), count: unreadUserMessages }
        }));
        
        // Mark as read in reviews page state
        window.dispatchEvent(new CustomEvent('conversationRead', {
          detail: { reviewId: parseInt(reviewId) }
        }));
        
        // Update localStorage immediately
        const savedReadStatus = localStorage.getItem('reviewReadStatus');
        const currentReadStatus = savedReadStatus ? JSON.parse(savedReadStatus) : {};
        const newReadStatus = {
          ...currentReadStatus,
          [parseInt(reviewId)]: true
        };
        localStorage.setItem('reviewReadStatus', JSON.stringify(newReadStatus));
      }
    }
  }, [reviewId]);

  const sendResponse = () => {
    if (!responseText.trim()) return;

    const newMessage = {
      id: Date.now(),
      message: responseText,
      sender: 'admin' as const,
      timestamp: new Date().toISOString(),
      isRead: true
    };

    setConversations(prev => [...prev, newMessage]);
    setResponseText('');
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <i 
        key={i} 
        className={`ri-star-${i < rating ? 'fill' : 'line'} text-yellow-400`}
      ></i>
    ));
  };

  if (!reviewData) {
    return (
      <div className="min-h-screen bg-gray-50 flex">
        <AdminSidebar 
          isMobileMenuOpen={isMobileMenuOpen} 
          setIsMobileMenuOpen={setIsMobileMenuOpen} 
        />
        
        <div className="flex-1 ml-0 flex flex-col">
          <div className="flex-1 p-4 md:p-6 lg:p-8">
            <div className="max-w-4xl mx-auto">
              <div className="text-center py-12">
                <i className="ri-chat-3-line text-6xl text-gray-300 mb-4"></i>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Conversation Not Found</h2>
                <p className="text-gray-600 mb-6">The conversation you're looking for doesn't exist.</p>
                <Link 
                  to="/admin/reviews"
                  className="inline-flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <i className="ri-arrow-left-line mr-2"></i>
                  Back to Reviews
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

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
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
              <div className="flex items-center gap-4 mb-4">
                <Link 
                  to="/admin/reviews"
                  className="flex items-center gap-2 text-gray-600 hover:text-red-600 transition-colors"
                >
                  <i className="ri-arrow-left-line"></i>
                  Back to Reviews
                </Link>
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Conversation with {reviewData.user}</h1>
              <p className="text-gray-600">Review conversation and respond to customer feedback</p>
            </div>

            {/* Review Summary */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <i className="ri-user-line text-xl text-red-600"></i>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-gray-900">{reviewData.user}</h3>
                    <span className="text-sm text-gray-500">({reviewData.email})</span>
                    <div className="flex">
                      {renderStars(reviewData.rating)}
                    </div>
                  </div>
                  <h4 className="font-medium text-gray-900 mb-2">{reviewData.title}</h4>
                  <p className="text-gray-700 mb-3">{reviewData.content}</p>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>{reviewData.date}</span>
                    <span className="capitalize">{reviewData.status}</span>
                    {reviewData.company && <span>{reviewData.company}</span>}
                  </div>
                </div>
              </div>
            </div>

            {/* Conversation */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <i className="ri-chat-3-line text-red-600"></i>
                  Conversation History
                </h2>
              </div>
              
              <div className="p-6">
                <div className="space-y-4 max-h-96 overflow-y-auto mb-6">
                  {conversations.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.sender === 'admin' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                          message.sender === 'admin'
                            ? 'bg-red-600 text-white'
                            : 'bg-gray-100 text-gray-900 border border-gray-200'
                        }`}
                      >
                        <p className="text-sm">{message.message}</p>
                        <p className={`text-xs mt-2 ${
                          message.sender === 'admin' ? 'text-red-100' : 'text-gray-500'
                        }`}>
                          {message.sender === 'admin' ? 'Admin' : reviewData.user} • {formatTimestamp(message.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Response Form */}
                <div className="border-t border-gray-200 pt-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Send Response</h3>
                  <div className="space-y-4">
                    <textarea
                      value={responseText}
                      onChange={(e) => setResponseText(e.target.value)}
                      placeholder="Type your response..."
                      className="w-full min-h-24 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 resize-vertical"
                      rows={4}
                    />
                    <div className="flex justify-end gap-3">
                      <button
                        onClick={() => setResponseText('')}
                        className="px-4 py-2 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors"
                      >
                        Clear
                      </button>
                      <button
                        onClick={sendResponse}
                        disabled={!responseText.trim()}
                        className="px-6 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Send Response
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
              <div className="flex flex-wrap gap-3">
                <button className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors">
                  Mark as Resolved
                </button>
                <button className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors">
                  Flag for Follow-up
                </button>
                <button className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 transition-colors">
                  Add Internal Note
                </button>
                <button className="px-4 py-2 bg-orange-600 text-white text-sm rounded-lg hover:bg-orange-700 transition-colors">
                  Escalate to Manager
                </button>
              </div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}