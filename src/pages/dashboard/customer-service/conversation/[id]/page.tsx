import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import DashboardSidebar from '../../../../../components/feature/DashboardSidebar';

interface Message {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_name: string;
  sender_role: 'user' | 'admin';
  message: string;
  is_read: boolean;
  created_at: string;
}

interface Ticket {
  id: number;
  issue: string;
  status: string;
  created_at: string;
}

export default function CustomerServiceConversationPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);
  const [newMessage, setNewMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load ticket and messages from backend
  useEffect(() => {
    if (!id) return;
    loadTicketConversation();
  }, [id]);

  const loadTicketConversation = async () => {
    setIsLoading(true);
    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      if (!token) {
        toast.error('Authentication required');
        navigate('/dashboard/customer-service');
        return;
      }

      const response = await fetch(`/api/customer-service/tickets/${id}/messages`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          toast.error('Ticket not found');
          navigate('/dashboard/customer-service');
          return;
        }
        throw new Error('Failed to load conversation');
      }

      const data = await response.json();
      setTicket(data.ticket);
      setMessages(data.messages || []);
      
    } catch (error: any) {
      console.error('Error loading conversation:', error);
      toast.error('Failed to load conversation');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || isSubmitting) return;

    setIsSubmitting(true);

    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      if (!token) {
        toast.error('Authentication required');
        setIsSubmitting(false);
        return;
      }

      const response = await fetch(`/api/customer-service/tickets/${id}/reply`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ticket_id: parseInt(id!),
          message: newMessage.trim()
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to send message');
      }

      toast.success('Message sent successfully!');
      setNewMessage('');
      
      // Reload conversation to show the new message
      await loadTicketConversation();
      
    } catch (error: any) {
      console.error('Error sending message:', error);
      toast.error(error.message || 'Failed to send message. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackToReports = () => {
    navigate('/dashboard/customer-service');
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

  const isMobile = windowWidth < 768;

  if (isLoading) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Toaster position="top-right" />
        <DashboardSidebar 
          isMobileMenuOpen={isMobileMenuOpen}
          setIsMobileMenuOpen={setIsMobileMenuOpen}
        />
        <div className={`flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : '0'}`}>
          <div className="p-8 text-center">
            <div className="animate-spin w-12 h-12 border-4 border-orange-600 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600">Loading conversation...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="flex min-h-screen bg-gray-50">
        <Toaster position="top-right" />
        <DashboardSidebar 
          isMobileMenuOpen={isMobileMenuOpen}
          setIsMobileMenuOpen={setIsMobileMenuOpen}
        />
        <div className={`min-h-screen bg-gradient-to-br from-orange-50 to-white flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : '0'}`}>
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="ri-error-warning-line text-gray-400 text-2xl"></i>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Report Not Found</h2>
            <p className="text-gray-600 mb-4">The requested report could not be found.</p>
            <button
              onClick={handleBackToReports}
              className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium whitespace-nowrap"
            >
              Back to Reports
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Toaster position="top-right" />
      
      {/* Dashboard Sidebar */}
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* Main Content */}
      <div className={`min-h-screen bg-gradient-to-br from-orange-50 to-white flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : '0'}`}>
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
              <div className="flex items-center gap-4 mb-4">
                <button
                  onClick={handleBackToReports}
                  className="flex items-center text-orange-600 hover:text-orange-700 font-medium whitespace-nowrap"
                >
                  <i className="ri-arrow-left-line mr-2"></i>
                  Back to Reports
                </button>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
                Ticket #{ticket.id} - Conversation
              </h1>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(ticket.status)}`}>
                  {getStatusText(ticket.status)}
                </span>
                <span className="text-sm text-gray-500">
                  Submitted on {new Date(ticket.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>

            {/* Original Report */}
            <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm mb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Original Report</h2>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-gray-800">{ticket.issue}</p>
              </div>
            </div>

            {/* Conversation */}
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              {/* Messages */}
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Conversation</h2>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {messages.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <i className="ri-message-3-line text-4xl mb-2"></i>
                      <p>No messages yet. Start the conversation below.</p>
                    </div>
                  ) : (
                    messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.sender_role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                          message.sender_role === 'user'
                            ? 'bg-orange-500 text-white'
                            : 'bg-gray-100 text-gray-900'
                        }`}>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium opacity-75">
                              {message.sender_role === 'user' ? 'You' : message.sender_name}
                            </span>
                            <span className="text-xs opacity-60">
                              {new Date(message.created_at).toLocaleTimeString('en-US', {
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                          <p className="text-sm whitespace-pre-wrap">{message.message}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Message Form */}
              <div className="p-6">
                <form onSubmit={handleSendMessage} className="space-y-4">
                  <div>
                    <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                      Send a message
                    </label>
                    <textarea
                      id="message"
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Type your message here..."
                      rows={4}
                      maxLength={1000}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none text-sm"
                      required
                    />
                    <div className="flex justify-between items-center mt-2">
                      <p className="text-xs text-gray-500">
                        Our support team typically responds within 24 hours
                      </p>
                      <p className="text-xs text-gray-500">
                        {newMessage.length}/1000 characters
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={isSubmitting || !newMessage.trim()}
                      className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm whitespace-nowrap"
                    >
                      {isSubmitting ? (
                        <span className="flex items-center">
                          <i className="ri-loader-4-line animate-spin mr-2"></i>
                          Sending...
                        </span>
                      ) : (
                        <span className="flex items-center">
                          <i className="ri-send-plane-line mr-2"></i>
                          Send Message
                        </span>
                      )}
                    </button>
                  </div>
                </form>
              </div>
            </div>

            {/* Help Information */}
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3 flex-shrink-0">
                  <i className="ri-information-line text-blue-600"></i>
                </div>
                <div>
                  <h3 className="font-semibold text-blue-800 mb-1">Need immediate assistance?</h3>
                  <p className="text-sm text-blue-700">
                    For urgent issues, you can also contact us directly at support@aitugo.com or call 1-800-AI-HELP.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}