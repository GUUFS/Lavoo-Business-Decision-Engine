import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';

interface Ticket {
  id: number;
  issue: string;
  category: string;
  status: string;
  created_at: string;
  updated_at: string;
  unread_count: number;
  last_message: string | null;
  last_message_at: string | null;
}

export default function CustomerServicePage() {
  const navigate = useNavigate();
  const [issue, setIssue] = useState('');
  const [category, setCategory] = useState('general');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState('submit');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoadingTickets, setIsLoadingTickets] = useState(false);
  const [totalUnread, setTotalUnread] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load tickets when switching to reports tab
  useEffect(() => {
    if (activeTab === 'reports') {
      loadTickets();
    }
  }, [activeTab]);

  const loadTickets = async () => {
    setIsLoadingTickets(true);
    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      if (!token) {
        toast.error('Authentication required');
        return;
      }

      const response = await fetch('/api/customer-service/tickets/my-tickets', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load tickets');
      }

      const data = await response.json();
      setTickets(data.tickets || []);

      // Calculate total unread messages
      const unreadCount = data.tickets.reduce((sum: number, ticket: Ticket) => sum + ticket.unread_count, 0);
      setTotalUnread(unreadCount);

    } catch (error: any) {
      console.error('Error loading tickets:', error);
      toast.error('Failed to load your reports');
    } finally {
      setIsLoadingTickets(false);
    }
};

// WebSocket for Real-time Updates
useEffect(() => {
  const connectWebSocket = () => {
    const token = document.cookie
      .split('; ')
      .find((row) => row.startsWith('access_token='))
      ?.split('=')[1];

    if (!token) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//localhost:8000/api/customer-service/ws/notifications`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log("✅ CustService List: Connected to WS");
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'new_message' && data.message) {
          const msg = data.message;

          // Update tickets list
          setTickets(prev => {
            const otherTickets = prev.filter(t => t.id !== msg.ticket_id);
            const currentTicket = prev.find(t => t.id === msg.ticket_id);

            if (currentTicket) {
              // Return updated ticket at the top
              return [{
                ...currentTicket,
                last_message: msg.message,
                last_message_at: msg.created_at,
                unread_count: currentTicket.unread_count + 1,
                status: 'in_progress' // usually re-opens if new message
              }, ...otherTickets];
            }
            // If new ticket not in list, might need to fetch, but usually we just update existing
            return prev;
          });

          // Update total unread
          setTotalUnread(prev => prev + 1);
        }

        if (data.type === 'ticket_resolved' && data.payload) {
          const { ticket_id } = data.payload;
          setTickets(prev => prev.map(t =>
            t.id === ticket_id ? { ...t, status: 'resolved' } : t
          ));
        }

      } catch (error) {
        console.error('Error processing WS message:', error);
      }
    };

    ws.current.onclose = () => {
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    };
  };

  if (activeTab === 'reports') {
    connectWebSocket();
  }

  return () => {
    if (ws.current) ws.current.close();
    if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
  };
}, [activeTab]);

const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!issue.trim()) {
    toast.error('Please describe your issue');
    return;
  }

  setIsSubmitting(true);

  try {
    // Improved token extraction
    const getAccessToken = () => {
      const cookies = document.cookie.split('; ');
      const tokenCookie = cookies.find(row => row.startsWith('access_token='));
      return tokenCookie ? tokenCookie.split('=')[1] : null;
    };

    const token = getAccessToken();

    if (!token) {
      toast.error('Authentication required. Please log in again.');
      // Optionally redirect to login
      // navigate('/login');
      setIsSubmitting(false);
      return;
    }

    console.log('Submitting ticket with token:', token.substring(0, 20) + '...'); // Debug log

    const response = await fetch('/api/customer-service/tickets/create', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        issue: issue.trim(),
        category: category
      }),
    });

    const responseData = await response.json().catch(() => ({}));

    if (!response.ok) {
      // Handle specific error cases
      if (response.status === 401) {
        toast.error('Session expired. Please log in again.');
        // Optionally redirect to login
        // navigate('/login');
      } else if (response.status === 403) {
        toast.error('You do not have permission to perform this action.');
      } else {
        throw new Error(responseData.detail || `Server error: ${response.status}`);
      }
      return;
    }

    // Success!
    toast.success('Issue submitted successfully! We\'ll respond within 24 hours.');

    // Reset form
    setIssue('');
    setCategory('general');

    // Reload tickets if on reports tab
    if (activeTab === 'reports') {
      loadTickets();
    }

  } catch (error: any) {
    console.error('Error submitting issue:', error);
    toast.error(error.message || 'Failed to submit issue. Please try again.');
  } finally {
    setIsSubmitting(false);
  }
};

const handleViewConversation = (ticketId: number) => {
  navigate(`/dashboard/customer-service/conversation/${ticketId}`);
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'open':
      return 'bg-yellow-100 text-yellow-800';
    case 'in_progress':
      return 'bg-blue-100 text-blue-800';
    case 'resolved':
      return 'bg-green-100 text-green-800';
    case 'closed':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const getStatusText = (status: string) => {
  return status.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};

const quickHelpOptions = [
  {
    title: 'Reports',
    description: 'View all your submitted issues',
    icon: 'ri-file-list-line',
    action: 'View Reports',
    onClick: () => setActiveTab('reports')
  },
  {
    title: 'Live Chat Support',
    description: 'Chat with our support team',
    icon: 'ri-chat-3-line',
    action: 'Start Chat'
  },
  {
    title: 'Documentation',
    description: 'Access user guides and tutorials',
    icon: 'ri-book-open-line',
    action: 'View Docs'
  }
];

const isMobile = windowWidth < 768;

return (
  <div className="flex min-h-screen bg-gray-50">
    <Toaster position="top-right" />

    {/* Dashboard Sidebar */}
    <DashboardSidebar
      isMobileMenuOpen={isMobileMenuOpen}
      setIsMobileMenuOpen={setIsMobileMenuOpen}
    />

    {/* Main Content */}
    <div className={`min-h-screen bg-gradient-to-br from-orange-50 to-white flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : 0}`}>
      <div className="p-4 sm:p-6 lg:p-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6 sm:mb-8">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Customer Service</h1>
            <p className="text-sm sm:text-base text-gray-600">Get help and support for your account</p>
          </div>

          {/* Tabs */}
          <div className="mb-6">
            <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
              <button
                onClick={() => setActiveTab('submit')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${activeTab === 'submit'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-orange-600'
                  }`}
              >
                Submit Issue
              </button>
              <button
                onClick={() => setActiveTab('reports')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap relative ${activeTab === 'reports'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-orange-600'
                  }`}
              >
                My Reports
                {totalUnread > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium">
                    {totalUnread}
                  </span>
                )}
              </button>
            </div>
          </div>

          {activeTab === 'submit' && (
            <>
              {/* Quick Help Options */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
                {quickHelpOptions.map((option, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    onClick={option.onClick}
                  >
                    <div className="text-center">
                      <div className="w-12 h-12 sm:w-14 sm:h-14 bg-orange-100 rounded-lg flex items-center justify-center mx-auto mb-3 sm:mb-4">
                        <i className={`${option.icon} text-orange-600 text-xl sm:text-2xl`}></i>
                      </div>
                      <h3 className="font-semibold text-gray-900 mb-2 text-sm sm:text-base">{option.title}</h3>
                      <p className="text-xs sm:text-sm text-gray-600 mb-3 sm:mb-4">{option.description}</p>
                      <button className="w-full bg-orange-500 text-white px-3 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium text-xs sm:text-sm whitespace-nowrap">
                        {option.action}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Support Form */}
              <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 lg:p-8 border border-gray-200 shadow-sm">
                <div className="max-w-2xl mx-auto">
                  <div className="text-center mb-6 sm:mb-8">
                    <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <i className="ri-customer-service-line text-orange-600 text-2xl sm:text-3xl"></i>
                    </div>
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">Describe Your Issue</h2>
                    <p className="text-sm sm:text-base text-gray-600">
                      Tell us about the problem you're experiencing and we'll help you resolve it
                    </p>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                      <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
                        Category
                      </label>
                      <select
                        id="category"
                        value={category}
                        onChange={(e) => setCategory(e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm sm:text-base"
                      >
                        <option value="general">General</option>
                        <option value="technical">Technical Issue</option>
                        <option value="billing">Billing</option>
                        <option value="account">Account</option>
                        <option value="other">Other</option>
                      </select>
                    </div>

                    <div>
                      <label htmlFor="issue" className="block text-sm font-medium text-gray-700 mb-2">
                        Issue Description
                      </label>
                      <textarea
                        id="issue"
                        value={issue}
                        onChange={(e) => setIssue(e.target.value)}
                        placeholder="Please describe your issue in detail. Include any error messages, steps you took, and what you expected to happen..."
                        rows={8}
                        maxLength={1000}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none text-sm sm:text-base"
                        required
                      />
                      <div className="flex justify-between items-center mt-2">
                        <p className="text-xs text-gray-500">
                          Please provide as much detail as possible
                        </p>
                        <p className="text-xs text-gray-500">
                          {issue.length}/1000 characters
                        </p>
                      </div>
                    </div>

                    <div className="flex justify-center">
                      <button
                        type="submit"
                        disabled={isSubmitting || !issue.trim()}
                        className="bg-orange-500 text-white px-8 py-3 rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm sm:text-base whitespace-nowrap min-w-[200px]"
                      >
                        {isSubmitting ? (
                          <span className="flex items-center justify-center">
                            <i className="ri-loader-4-line animate-spin mr-2"></i>
                            Submitting...
                          </span>
                        ) : (
                          <span className="flex items-center justify-center">
                            <i className="ri-send-plane-line mr-2"></i>
                            Submit Issue
                          </span>
                        )}
                      </button>
                    </div>
                  </form>

                  {/* Contact Information */}
                  <div className="mt-8 pt-6 border-t border-gray-200">
                    <h3 className="font-semibold text-gray-900 mb-4 text-center">Other Ways to Reach Us</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-2">
                          <i className="ri-mail-line text-blue-600"></i>
                        </div>
                        <p className="text-sm font-medium text-gray-900">Email</p>
                        <p className="text-xs text-gray-600">support@aitugo.com</p>
                      </div>
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-2">
                          <i className="ri-phone-line text-green-600"></i>
                        </div>
                        <p className="text-sm font-medium text-gray-900">Phone</p>
                        <p className="text-xs text-gray-600">1-800-AI-HELP</p>
                      </div>
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-2">
                          <i className="ri-time-line text-purple-600"></i>
                        </div>
                        <p className="text-sm font-medium text-gray-900">Hours</p>
                        <p className="text-xs text-gray-600">24/7 Support</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {activeTab === 'reports' && (
            <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 lg:p-8 border border-gray-200 shadow-sm">
              <div className="mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">My Reports</h2>
                <p className="text-sm sm:text-base text-gray-600">
                  View all your submitted issues and their current status
                </p>
              </div>

              {isLoadingTickets ? (
                <div className="text-center py-12">
                  <div className="animate-spin w-8 h-8 border-4 border-orange-600 border-t-transparent rounded-full mx-auto mb-3"></div>
                  <p className="text-gray-600">Loading your reports...</p>
                </div>
              ) : tickets.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i className="ri-file-list-line text-gray-400 text-2xl"></i>
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No Reports Yet</h3>
                  <p className="text-gray-600 mb-4">You haven't submitted any issues yet.</p>
                  <button
                    onClick={() => setActiveTab('submit')}
                    className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium whitespace-nowrap"
                  >
                    Submit Your First Issue
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  {tickets.map((ticket) => (
                    <div key={ticket.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2 flex-wrap">
                            <span className="text-sm font-medium text-gray-500">
                              Ticket #{ticket.id}
                            </span>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(ticket.status)}`}>
                              {getStatusText(ticket.status)}
                            </span>
                            <span className="text-xs text-gray-500">
                              {ticket.category}
                            </span>
                          </div>
                          <p className="text-gray-900 mb-2 line-clamp-3">{ticket.issue}</p>
                          <p className="text-sm text-gray-500">
                            Submitted on {new Date(ticket.created_at).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                      </div>

                      <div className="mt-3 pt-3 border-t border-gray-100">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {ticket.last_message && (
                              <span className="text-sm text-gray-600">
                                <i className="ri-message-line mr-1"></i>
                                Last message: {new Date(ticket.last_message_at!).toLocaleString()}
                              </span>
                            )}
                            {ticket.unread_count > 0 && (
                              <span className="px-2 py-1 bg-red-100 text-red-600 text-xs font-medium rounded-full">
                                {ticket.unread_count} new message{ticket.unread_count > 1 ? 's' : ''}
                              </span>
                            )}
                          </div>
                          <button
                            onClick={() => handleViewConversation(ticket.id)}
                            className="text-orange-600 hover:text-orange-700 text-sm font-medium whitespace-nowrap"
                          >
                            View Conversation →
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  </div>
);
}