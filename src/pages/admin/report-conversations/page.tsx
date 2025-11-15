import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

interface Message {
  id: number;
  sender: 'user' | 'admin';
  content: string;
  timestamp: string;
  senderName: string;
}

interface Report {
  id: number;
  title: string;
  type: string;
  user: string;
  email: string;
  content: string;
  category: string;
  priority: string;
  status: string;
  date: string;
  rating?: number;
}

export default function AdminReportConversations() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [report, setReport] = useState<Report | null>(null);

  // Mock report data
  const mockReports: { [key: string]: Report } = {
    '1': {
      id: 1,
      title: 'AI Analysis Accuracy Feedback',
      type: 'feedback',
      user: 'Sarah Johnson',
      email: 'sarah.johnson@email.com',
      content: 'The AI analysis was incredibly accurate for our retail business. It identified cost-saving opportunities that our team missed. The recommendations were actionable and resulted in 15% cost reduction.',
      category: 'Analysis Quality',
      priority: 'high',
      status: 'resolved',
      date: '2024-02-26',
      rating: 5
    },
    '2': {
      id: 2,
      title: 'Feature Request: Export Options',
      type: 'feature_request',
      user: 'Michael Chen',
      email: 'michael.chen@company.com',
      content: 'Would love to see more export options for the analysis reports. Currently only PDF is available, but Excel and CSV formats would be very helpful for our team presentations.',
      category: 'Feature Enhancement',
      priority: 'medium',
      status: 'in_progress',
      date: '2024-02-25',
      rating: 4
    },
    '3': {
      id: 3,
      title: 'Bug Report: Dashboard Loading Issue',
      type: 'bug_report',
      user: 'Emily Rodriguez',
      email: 'emily.r@startup.io',
      content: 'Experiencing slow loading times on the dashboard when accessing historical analysis data. Takes about 30 seconds to load reports from last month.',
      category: 'Technical Issue',
      priority: 'high',
      status: 'pending',
      date: '2024-02-24',
      rating: 2
    },
    '9': {
      id: 9,
      title: 'Security Concern: Data Privacy',
      type: 'bug_report',
      user: 'Jennifer Lee',
      email: 'jennifer.lee@security.com',
      content: 'Need clarification on data privacy measures. How is sensitive business data protected during analysis?',
      category: 'Security',
      priority: 'high',
      status: 'pending',
      date: '2024-02-18',
      rating: 3
    }
  };

  // Mock conversation data
  const mockConversations: { [key: string]: Message[] } = {
    '1': [
      {
        id: 1,
        sender: 'user',
        content: 'Thank you for the positive feedback! We\'re thrilled to hear that our AI analysis helped you achieve a 15% cost reduction. Could you share more details about which specific recommendations were most valuable?',
        timestamp: '2024-02-26T10:30:00Z',
        senderName: 'Sarah Johnson'
      },
      {
        id: 2,
        sender: 'admin',
        content: 'Thank you for the detailed feedback, Sarah! We\'re delighted to hear about your success. The inventory optimization and supplier analysis recommendations seem to have made the biggest impact. We\'d love to feature your case study in our success stories if you\'re interested.',
        timestamp: '2024-02-26T14:15:00Z',
        senderName: 'Admin Support'
      },
      {
        id: 3,
        sender: 'user',
        content: 'I\'d be happy to participate in a case study! The supplier analysis was particularly insightful - it identified redundancies we never noticed.',
        timestamp: '2024-02-27T09:20:00Z',
        senderName: 'Sarah Johnson'
      }
    ],
    '2': [
      {
        id: 1,
        sender: 'user',
        content: 'The current PDF export is good, but our team really needs Excel and CSV formats for further data manipulation and presentations to stakeholders.',
        timestamp: '2024-02-25T11:45:00Z',
        senderName: 'Michael Chen'
      },
      {
        id: 2,
        sender: 'admin',
        content: 'Thanks for the suggestion, Michael! Export functionality is definitely on our roadmap. We\'re planning to add Excel and CSV exports in our next major update. I\'ll make sure to prioritize this based on your feedback.',
        timestamp: '2024-02-25T16:30:00Z',
        senderName: 'Product Team'
      },
      {
        id: 3,
        sender: 'user',
        content: 'That\'s great news! Do you have an estimated timeline for when this feature might be available?',
        timestamp: '2024-02-26T08:15:00Z',
        senderName: 'Michael Chen'
      },
      {
        id: 4,
        sender: 'admin',
        content: 'We\'re targeting the Q2 release for the enhanced export features. I\'ll add you to our beta testing list so you can try it out early!',
        timestamp: '2024-02-26T10:45:00Z',
        senderName: 'Product Team'
      }
    ],
    '3': [
      {
        id: 1,
        sender: 'user',
        content: 'The dashboard is taking way too long to load historical data. This is affecting our daily operations and decision-making process.',
        timestamp: '2024-02-24T13:20:00Z',
        senderName: 'Emily Rodriguez'
      },
      {
        id: 2,
        sender: 'admin',
        content: 'I apologize for the performance issues, Emily. Our technical team is investigating the slow loading times. Can you tell me which specific date ranges are causing the longest delays?',
        timestamp: '2024-02-24T15:45:00Z',
        senderName: 'Technical Support'
      },
      {
        id: 3,
        sender: 'user',
        content: 'Anything older than 2 weeks seems to take 30+ seconds. Data from the last week loads fine.',
        timestamp: '2024-02-25T09:10:00Z',
        senderName: 'Emily Rodriguez'
      }
    ],
    '9': [
      {
        id: 1,
        sender: 'user',
        content: 'I need detailed information about how our sensitive business data is protected during the AI analysis process. Our compliance team requires this information.',
        timestamp: '2024-02-18T14:30:00Z',
        senderName: 'Jennifer Lee'
      },
      {
        id: 2,
        sender: 'admin',
        content: 'Thank you for your security inquiry, Jennifer. We take data privacy very seriously. All data is encrypted in transit and at rest using AES-256 encryption. Our analysis runs in isolated environments and data is never stored permanently. I can provide you with our detailed security whitepaper.',
        timestamp: '2024-02-18T16:15:00Z',
        senderName: 'Security Team'
      }
    ]
  };

  useEffect(() => {
    if (reportId) {
      const reportData = mockReports[reportId];
      const conversationData = mockConversations[reportId] || [];
      
      if (reportData) {
        setReport(reportData);
        setMessages(conversationData);
        
        // Mark conversation as read
        const event = new CustomEvent('reportConversationRead', {
          detail: { reportId: parseInt(reportId) }
        });
        window.dispatchEvent(event);
      }
    }
  }, [reportId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;

    setIsSubmitting(true);

    // Simulate API call
    setTimeout(() => {
      const message: Message = {
        id: messages.length + 1,
        sender: 'admin',
        content: newMessage,
        timestamp: new Date().toISOString(),
        senderName: 'Admin Support'
      };

      setMessages(prev => [...prev, message]);
      setNewMessage('');
      setIsSubmitting(false);
    }, 1000);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'feedback': return 'ri-feedback-line';
      case 'bug_report': return 'ri-bug-line';
      case 'feature_request': return 'ri-lightbulb-line';
      default: return 'ri-file-text-line';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-600';
      case 'medium': return 'bg-orange-100 text-orange-600';
      case 'low': return 'bg-green-100 text-green-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <i 
        key={i} 
        className={`ri-star-${i < rating ? 'fill' : 'line'} text-yellow-400`}
      ></i>
    ));
  };

  if (!report) {
    return (
      <div className="min-h-screen bg-gray-50 flex">
        <AdminSidebar 
          isMobileMenuOpen={isMobileMenuOpen} 
          setIsMobileMenuOpen={setIsMobileMenuOpen} 
        />
        
        <div className="flex-1 ml-0 md:ml-64 flex flex-col">
          <div className="flex-1 p-4 md:p-6 lg:p-8">
            <div className="max-w-4xl mx-auto">
              <div className="text-center py-12">
                <i className="ri-file-list-3-line text-6xl text-gray-300 mb-4"></i>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Report not found</h3>
                <p className="text-gray-600 mb-4">The requested report could not be found.</p>
                <button
                  onClick={() => navigate('/admin/reports')}
                  className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                >
                  Back to Reports
                </button>
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
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/admin/reports')}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <i className="ri-arrow-left-line"></i>
                <span>Back to Reports</span>
              </button>
            </div>
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
              
              {isProfileDropdownOpen && (
                <div 
                  className="fixed inset-0 z-40"
                  onClick={() => setIsProfileDropdownOpen(false)}
                ></div>
              )}
              
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
            {/* Report Header */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                  <i className={`${getTypeIcon(report.type)} text-xl text-red-600`}></i>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h1 className="text-xl font-bold text-gray-900">{report.title}</h1>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(report.priority)}`}>
                      {report.priority.charAt(0).toUpperCase() + report.priority.slice(1)} Priority
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mb-3">
                    <span className="text-sm font-medium text-gray-900">{report.user}</span>
                    <span className="text-sm text-gray-500">{report.email}</span>
                    <span className="text-sm text-gray-500">{report.category}</span>
                    {report.rating && (
                      <div className="flex">
                        {renderStars(report.rating)}
                      </div>
                    )}
                  </div>
                  <p className="text-gray-700 mb-3">{report.content}</p>
                  <div className="text-sm text-gray-500">
                    Submitted on {new Date(report.date).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </div>

            {/* Conversation */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Conversation</h2>
                <p className="text-sm text-gray-600 mt-1">Messages between you and {report.user}</p>
              </div>

              {/* Messages */}
              <div className="p-6 max-h-96 overflow-y-auto">
                {messages.length > 0 ? (
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.sender === 'admin' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                          message.sender === 'admin'
                            ? 'bg-red-600 text-white'
                            : 'bg-gray-100 text-gray-900'
                        }`}>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium opacity-75">
                              {message.senderName}
                            </span>
                            <span className="text-xs opacity-60">
                              {formatTimestamp(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm">{message.content}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <i className="ri-chat-3-line text-4xl text-gray-300 mb-3"></i>
                    <p className="text-gray-500">No messages yet. Start the conversation!</p>
                  </div>
                )}
              </div>

              {/* Reply Form */}
              <div className="p-6 border-t border-gray-200">
                <form onSubmit={handleSubmit}>
                  <div className="mb-4">
                    <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                      Reply to {report.user}
                    </label>
                    <textarea
                      id="message"
                      rows={3}
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type your message..."
                      className="w-full px-3 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-200 focus:border-red-500 outline-none resize-none"
                      required
                    />
                    <div className="mt-2 text-xs text-gray-500">
                      {newMessage.length}/500 characters
                    </div>
                  </div>

                  <div className="flex gap-3 justify-end">
                    <button
                      type="button"
                      onClick={() => setNewMessage('')}
                      className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium bg-white hover:bg-gray-50 transition-colors cursor-pointer whitespace-nowrap"
                    >
                      Clear
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting || !newMessage.trim()}
                      className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors cursor-pointer whitespace-nowrap"
                    >
                      {isSubmitting ? (
                        <>
                          <i className="ri-loader-4-line animate-spin mr-2"></i>
                          Sending...
                        </>
                      ) : (
                        <>
                          <i className="ri-send-plane-line mr-2"></i>
                          Send Reply
                        </>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}