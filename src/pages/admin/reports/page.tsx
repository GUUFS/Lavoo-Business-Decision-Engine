import { useState, useEffect, useRef } from 'react';
// import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import { getAuthHeaders } from '../../../utils/auth';
import { toast } from 'react-toastify';

interface Conversation {
  user_id: number;
  user_name: string;
  user_email: string;
  unread_count: number;
  last_message: string;
  last_message_at: string;
  status: string;
}

interface Message {
  id: number;
  sender_role: 'admin' | 'user' | 'system';
  message: string;
  created_at: string;
  ticket_id: number;
  sender_name?: string;
}

export default function AdminReports() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState("");
  // const [sendingReply, setSendingReply] = useState(false);

  // Confirmation Modal State
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);

  // Track if modal is open (not just viewing state)
  const isModalOpenRef = useRef(false);
  const currentUserIdRef = useRef<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchConversations();
  }, []);

  // Update modal ref when state changes
  useEffect(() => {
    isModalOpenRef.current = isModalOpen;
    if (!isModalOpen) {
      currentUserIdRef.current = null;
    }
  }, [isModalOpen]);

  // Scroll to bottom of chat
  useEffect(() => {
    if (isModalOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isModalOpen]);

  // Update sidebar badge when conversations change
  useEffect(() => {
    const unreadUsersCount = conversations.filter(c => c.unread_count > 0).length;
    window.dispatchEvent(new CustomEvent('adminReportsUnreadCountChanged', {
      detail: { count: unreadUsersCount }
    }));
  }, [conversations]);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/customer-service/admin/conversations`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();

        // Remove duplicates by user_id
        const uniqueConversations = data.conversations.reduce((acc: Conversation[], conv: Conversation) => {
          const exists = acc.find(c => c.user_id === conv.user_id);
          if (!exists) {
            acc.push(conv);
          }
          return acc;
        }, []);

        setConversations(uniqueConversations);
      }
    } catch (error) {
      console.error('Error fetching conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenConversation = async (conv: Conversation) => {
    setSelectedConversation(conv);
    setIsModalOpen(true);
    currentUserIdRef.current = conv.user_id;

    // Mark as read immediately in local state
    setConversations(prev => prev.map(c =>
      c.user_id === conv.user_id ? { ...c, unread_count: 0 } : c
    ));

    // Fetch messages
    try {
      const response = await fetch(`${API_BASE_URL}/api/customer-service/admin/users/${conv.user_id}/messages`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages);
      }
    } catch (error) {
      console.error("Error fetching messages:", error);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedConversation(null);
    setMessages([]);
    setIsConfirmModalOpen(false);
    currentUserIdRef.current = null;
  };

  const handleResolveTicket = async () => {
    if (!selectedConversation) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/customer-service/admin/users/${selectedConversation.user_id}/resolve_all`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (response.ok) {
        // Update local conversation status
        setConversations(prev => prev.map(c =>
          c.user_id === selectedConversation.user_id ? { ...c, status: 'resolved', unread_count: 0 } : c
        ));

        // Update selected conversation
        setSelectedConversation(prev => prev ? { ...prev, status: 'resolved' } : null);

        setIsConfirmModalOpen(false);
      }
    } catch (e) {
      console.error(e);
      toast.error('Failed to resolve tickets');
    }
  };

  useEffect(() => {
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//localhost:8000/api/customer-service/ws/admin/reports`;

      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log("✅ Connected to Admin Reports WebSocket");
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle new user message
          if (data.type === 'new_message' && data.payload) {
            const msg = data.payload;
            const modalOpen = isModalOpenRef.current;
            const viewingUserId = currentUserIdRef.current;

            // Check if this message is for the currently open conversation
            const isForCurrentConversation = modalOpen && viewingUserId === msg.user_id;

            if (isForCurrentConversation) {
              // User is viewing this conversation - add to messages, no unread
              setMessages(prev => {
                const exists = prev.find(m => m.id === msg.id);
                if (exists) return prev;

                return [...prev, {
                  id: msg.id || Date.now(),
                  sender_role: msg.sender_role || 'user',
                  message: msg.content,
                  created_at: msg.created_at,
                  ticket_id: msg.ticket_id,
                  sender_name: msg.sender_name
                }];
              });

              // Move to top, update last message, NO unread increment
              setConversations(prev => {
                const otherConvs = prev.filter(c => c.user_id !== msg.user_id);
                const currentConv = prev.find(c => c.user_id === msg.user_id);

                if (currentConv) {
                  return [{
                    ...currentConv,
                    last_message: msg.content,
                    last_message_at: msg.created_at,
                    unread_count: 0 // Ensure it stays 0
                  }, ...otherConvs];
                }
                return prev; // Should be in list if we are viewing it
              });
            } else {
              // Not viewing - move to top AND increment unread
              setConversations(prev => {
                const otherConvs = prev.filter(c => c.user_id !== msg.user_id);
                const existingConv = prev.find(c => c.user_id === msg.user_id);

                if (existingConv) {
                  return [{
                    ...existingConv,
                    unread_count: existingConv.unread_count + 1,
                    last_message: msg.content,
                    last_message_at: msg.created_at,
                    status: 'active'
                  }, ...otherConvs];
                } else {
                  // New conversation - fetch all to get it (or simpler: let fetch happen)
                  fetchConversations();
                  return prev;
                }
              });
            }
          }

          // Handle admin message sent (from another admin or other tab)
          if (data.type === 'admin_message_sent' && data.message) {
            const msg = data.message;

            // Get current user ID to check if this is our own message
            const currentAdminId = parseInt(localStorage.getItem('user_id') || '0');
            const modalOpen = isModalOpenRef.current;
            const viewingUserId = currentUserIdRef.current;

            // Only add if NOT sent by current user AND viewing this conversation
            if (data.sender_id !== currentAdminId && modalOpen && viewingUserId === msg.user_id) {
              setMessages(prev => {
                const exists = prev.find(m => m.id === msg.id);
                if (exists) return prev;

                return [...prev, {
                  id: msg.id,
                  sender_role: msg.sender_role,
                  message: msg.message,
                  created_at: msg.created_at,
                  ticket_id: msg.ticket_id,
                  sender_name: msg.sender_name
                }];
              });
            }

            // Update conversation list - Move to top regardless
            setConversations(prev => {
              const otherConvs = prev.filter(c => c.user_id !== msg.user_id);
              const currentConv = prev.find(c => c.user_id === msg.user_id);

              if (currentConv) {
                return [{
                  ...currentConv,
                  last_message: msg.message,
                  last_message_at: msg.created_at
                }, ...otherConvs];
              }
              return prev;
            });
          }

          // Handle ticket resolved
          if (data.type === 'ticket_resolved' && data.payload) {
            const payload = data.payload;
            const modalOpen = isModalOpenRef.current;
            const viewingUserId = currentUserIdRef.current;

            // If viewing this conversation, add system message
            if (modalOpen && viewingUserId === payload.user_id) {
              setMessages(prev => {
                const exists = prev.find(m => m.id === payload.message.id);
                if (exists) return prev;

                return [...prev, {
                  id: payload.message.id,
                  sender_role: 'system',
                  message: payload.message.message,
                  created_at: payload.message.created_at,
                  ticket_id: payload.message.ticket_id
                }];
              });
            }

            // Update conversation status
            setConversations(prev => prev.map(c =>
              c.user_id === payload.user_id
                ? { ...c, status: 'resolved', unread_count: 0 }
                : c
            ));

            // Update selected conversation if it's the one being resolved
            if (selectedConversation?.user_id === payload.user_id) {
              setSelectedConversation(prev => prev ? { ...prev, status: 'resolved' } : null);
            }
          }
        } catch (error) {
          console.error('❌ Error processing WebSocket message:', error);
        }
      };

      ws.current.onerror = () => {
        // Silently handle WebSocket errors
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
  }, [selectedConversation]);

  const handleReply = async () => {
    if (!newMessage.trim() || !messages.length) return;

    const validMsgs = messages.filter(m => m.sender_role !== 'system');
    if (!validMsgs.length) return;

    const lastMsg = validMsgs[validMsgs.length - 1];
    const ticketId = lastMsg.ticket_id;
    const messageText = newMessage.trim();

    // Don't set sendingReply(true) to keep UI interactive (optimistic)
    // setSendingReply(true); 
    setNewMessage("");

    const textarea = document.querySelector('textarea');
    if (textarea) textarea.style.height = 'auto';

    // Add message optimistically
    const optimisticMsg: Message = {
      id: Date.now(), // Temporary ID
      sender_role: 'admin',
      message: messageText,
      created_at: new Date().toISOString(),
      ticket_id: ticketId,
      sender_name: 'You'
    };

    setMessages(prev => [...prev, optimisticMsg]);

    // Move to top immediately
    setConversations(prev => {
      const otherConvs = prev.filter(c => c.user_id !== currentUserIdRef.current);
      const currentConv = prev.find(c => c.user_id === currentUserIdRef.current);

      if (currentConv) {
        return [{
          ...currentConv,
          last_message: messageText,
          last_message_at: new Date().toISOString(),
          unread_count: 0 // Ensure read
        }, ...otherConvs];
      }
      return prev;
    });

    try {
      const response = await fetch(`${API_BASE_URL}/api/customer-service/admin/tickets/${ticketId}/reply`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({ message: messageText, ticket_id: ticketId })
      });

      if (!response.ok) {
        // Revert on failure (simple alert for now)
        toast.error("Failed to send reply. Please refresh.");
      }
    } catch (error) {
      console.error("Error sending reply:", error);
      toast.error("Error sending reply");
    }
  };

  // Check if current conversation has been resolved
  const isCurrentTicketResolved = selectedConversation?.status === 'resolved';

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      <div className="flex-1 ml-0 flex flex-col">
        <AdminHeader setIsMobileMenuOpen={setIsMobileMenuOpen} />

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            <div className="mb-6 md:mb-8 flex justify-between items-center">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Customer Reports</h1>
                <p className="text-gray-600">Manage user support tickets and conversations</p>
              </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              {loading ? (
                <div className="p-8 text-center text-gray-500">Loading conversations...</div>
              ) : conversations.length === 0 ? (
                <div className="p-8 text-center text-gray-500">No active reports found.</div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {conversations.map((conv) => (
                    <div
                      key={conv.user_id}
                      onClick={() => handleOpenConversation(conv)}
                      className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${conv.status === 'active' ? 'bg-blue-50/30' : ''}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center relative">
                            <span className="font-semibold text-gray-600 text-lg">
                              {conv.user_name.charAt(0).toUpperCase()}
                            </span>
                            {conv.unread_count > 0 && (
                              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center border-2 border-white">
                                {conv.unread_count}
                              </span>
                            )}
                          </div>
                          <div>
                            <h3 className="font-semibold text-gray-900">{conv.user_name}</h3>
                            <p className="text-sm text-gray-500">{conv.user_email}</p>
                            <p className="text-sm text-gray-600 mt-1 line-clamp-1">
                              {conv.last_message || "No messages"}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-gray-500 block mb-2">
                            {conv.last_message_at ? new Date(conv.last_message_at).toLocaleDateString() : ''}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${conv.status === 'active'
                            ? 'bg-blue-100 text-blue-700'
                            : (conv.status === 'resolved' ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700')
                            }`}>
                            {conv.status === 'active'
                              ? 'New Messages'
                              : (conv.status === 'resolved' ? 'Resolved' : 'Caught Up')}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Conversation Modal */}
      {isModalOpen && selectedConversation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full h-[600px] flex flex-col overflow-hidden">
            <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
              <div className="flex items-center gap-3">
                {!isCurrentTicketResolved && (
                  <button
                    onClick={() => setIsConfirmModalOpen(true)}
                    className="px-3 py-1 text-sm bg-green-100 text-green-700 hover:bg-green-200 rounded-lg transition-colors"
                  >
                    <i className="ri-check-double-line mr-1"></i>
                    Mark Resolved
                  </button>
                )}
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="font-semibold text-blue-600">
                    {selectedConversation.user_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{selectedConversation.user_name}</h3>
                  <p className="text-sm text-gray-500">{selectedConversation.user_email}</p>
                </div>
              </div>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-600">
                <i className="ri-close-line text-2xl"></i>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
              {messages.map((msg, index) => (
                <div key={msg.id || index}>
                  {msg.sender_role === 'system' ? (
                    <div className="flex justify-center my-4">
                      <div className="flex items-center gap-2">
                        <div className="h-px w-12 bg-gray-300"></div>
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                          {msg.message === "Ticket Resolved" ? "-------- Ticket Resolved --------" : msg.message}
                        </span>
                        <div className="h-px w-12 bg-gray-300"></div>
                      </div>
                    </div>
                  ) : (
                    <div className={`flex ${msg.sender_role === 'admin' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[70%] rounded-lg p-3 ${msg.sender_role === 'admin'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-white text-gray-900 shadow-sm rounded-bl-none'
                        }`}>
                        <p className="text-sm">{msg.message}</p>
                        <span className={`text-xs mt-1 block ${msg.sender_role === 'admin' ? 'text-blue-100' : 'text-gray-400'}`}>
                          {msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-4 border-t border-gray-200 bg-white">
              <div className="flex gap-2 items-end">
                <textarea
                  value={newMessage}
                  onChange={(e) => {
                    setNewMessage(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = `${e.target.scrollHeight}px`;
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleReply();
                    }
                  }}
                  placeholder="Type a reply..."
                  rows={1}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none overflow-hidden min-h-[46px] max-h-[150px]"
                />
                <button
                  onClick={handleReply}
                  disabled={!newMessage.trim()}
                  className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end h-[46px] w-[46px] flex items-center justify-center flex-shrink-0"
                >
                  <i className="ri-send-plane-fill"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {isConfirmModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full p-6">
            <div className="text-center mb-6">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="ri-question-line text-blue-600 text-2xl"></i>
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">Mark Ticket as Resolved?</h3>
              <p className="text-gray-600 text-sm">
                Are you sure you want to mark all active tickets for this user as resolved?
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setIsConfirmModalOpen(false)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              >
                No, Cancel
              </button>
              <button
                onClick={handleResolveTicket}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Yes, Resolve
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}