import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast, Toaster } from 'react-hot-toast';
import DashboardSidebar from '../../../../../components/feature/DashboardSidebar';

interface Message {
  id: number;
  ticket_id: number;
  sender_id: number;
  sender_name: string;
  sender_role: 'user' | 'admin' | 'system';
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
  // const [isSubmitting, setIsSubmitting] = useState(false);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Track if component is mounted (user is on this page)
  const isMountedRef = useRef(true);
  const ws = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load ticket and messages from backend
  useEffect(() => {
    if (!id) return;
    isMountedRef.current = true;
    loadTicketConversation();

    return () => {
      isMountedRef.current = false;
    };
  }, [id]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const connectWebSocket = () => {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      if (!token) {
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//localhost:8000/api/customer-service/ws/notifications`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("✅ Connected to notification WebSocket");
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle new message from admin
          if (data.type === 'new_message' && data.message) {
            const msg = data.message;

            // Only process if it's for the current ticket
            if (id && msg.ticket_id === parseInt(id)) {
              const isOnPage = isMountedRef.current;

              setMessages(prev => {
                const exists = prev.find(m => m.id === msg.id);
                if (exists) return prev;

                return [...prev, {
                  id: msg.id,
                  ticket_id: msg.ticket_id,
                  sender_id: msg.sender_id || 0,
                  sender_name: msg.sender_name || 'Admin',
                  sender_role: msg.sender_role || 'admin',
                  message: msg.message,
                  is_read: true, // Mark as read since we're showing it
                  created_at: msg.created_at
                }];
              });

              // Only show toast if NOT on this page (shouldn't happen, but just in case)
              if (!isOnPage) {
                toast.success('New reply from support!');
              }
            }
          }

          // Handle ticket resolved
          if (data.type === 'ticket_resolved' && data.payload) {
            const payload = data.payload;

            // Only update if it's for current ticket
            if (id && payload.ticket_id === parseInt(id)) {
              // Add system message
              setMessages(prev => {
                const exists = prev.find(m => m.id === payload.message.id);
                if (exists) return prev;

                return [...prev, {
                  id: payload.message.id,
                  ticket_id: payload.message.ticket_id,
                  sender_id: 0,
                  sender_name: 'System',
                  sender_role: 'system',
                  message: payload.message.message,
                  is_read: true,
                  created_at: payload.message.created_at
                }];
              });

              // Update ticket status
              setTicket(prev => prev ? { ...prev, status: 'resolved' } : null);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.current.onerror = () => {
        // Silently handle - connection errors are expected
      };

      ws.current.onclose = () => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
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
    if (!newMessage.trim()) return;

    const messageToSend = newMessage.trim();
    // setIsSubmitting(true); // Don't block UI for optimistic send

    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      if (!token) {
        toast.error('Authentication required');
        // setIsSubmitting(false);
        return;
      }

      // Optimistically add message to UI immediately
      const optimisticMessage: Message = {
        id: Date.now(),
        ticket_id: parseInt(id!),
        sender_id: 0,
        sender_name: 'You',
        sender_role: 'user',
        message: messageToSend,
        is_read: false,
        created_at: new Date().toISOString()
      };

      setMessages(prev => [...prev, optimisticMessage]);
      setNewMessage('');

      const response = await fetch(`/api/customer-service/tickets/${id}/reply`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          ticket_id: parseInt(id!),
          message: messageToSend
        }),
      });

      if (!response.ok) {
        // Remove optimistic message on error
        setMessages(prev => prev.filter(m => m.id !== optimisticMessage.id));
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to send message');
      }

      // Update ticket status if it was resolved
      if (ticket?.status === 'resolved') {
        setTicket(prev => prev ? { ...prev, status: 'in_progress' } : null);
      }

      toast.success('Message sent successfully!');

    } catch (error: any) {
      console.error('Error sending message:', error);
      toast.error(error.message || 'Failed to send message. Please try again.');
    } finally {
      // setIsSubmitting(false);
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
  const isTicketResolved = ticket?.status === 'resolved';

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

      <DashboardSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

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
                      <div key={message.id}>
                        {message.sender_role === 'system' ? (
                          <div className="flex justify-center my-4">
                            <div className="flex items-center gap-2">
                              <div className="h-px w-12 bg-gray-300"></div>
                              <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                                {message.message === "Ticket Resolved" ? "-------- Ticket Resolved --------" : message.message}
                              </span>
                              <div className="h-px w-12 bg-gray-300"></div>
                            </div>
                          </div>
                        ) : (
                          <div className={`flex ${message.sender_role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${message.sender_role === 'user'
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
                        )}
                      </div>
                    ))
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Message Form - Only show if ticket is NOT resolved */}
              {!isTicketResolved ? (
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
                        disabled={!newMessage.trim()}
                        className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm whitespace-nowrap"
                      >
                        <span className="flex items-center">
                          <i className="ri-send-plane-line mr-2"></i>
                          Send Message
                        </span>
                      </button>
                    </div>
                  </form>
                </div>
              ) : (
                <div className="p-6 bg-gray-50 border-t border-gray-200">
                  <div className="flex items-center justify-center gap-2 text-gray-600">
                    <i className="ri-check-double-line text-green-600 text-xl"></i>
                    <p className="text-sm font-medium">
                      This ticket has been resolved. To continue the conversation, please create a new ticket.
                    </p>
                  </div>
                </div>
              )}
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