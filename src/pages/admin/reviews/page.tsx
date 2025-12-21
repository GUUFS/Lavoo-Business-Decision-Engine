import { useState, useEffect, useRef } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import { getAuthHeaders } from '../../../utils/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface Message {
  id: number;
  review_id: number;
  sender_type: 'user' | 'admin';
  message: string;
  timestamp: string;
  is_read: boolean;
}

interface Review {
  id: number;
  user_name: string;
  user_email: string;
  business_name: string;
  review_title: string;
  rating: number;
  review_text: string;
  date_submitted: string;
  status: string;
  category: string;
  admin_response: boolean;
  conversation_count: number;
  unread_messages: number;
  is_attended: boolean; // Added field
}

const ConversationModal = ({ review, onClose, onReply }: {
  review: Review,
  onClose: () => void,
  onReply: (id: number, message: string) => Promise<boolean>
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchMessages = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/reviews/${review.id}/conversations`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
      }
    } catch (error) {
      console.error("Error fetching messages", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [review.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!newMessage.trim()) return;
    setSending(true);
    const success = await onReply(review.id, newMessage);
    if (success) {
      setNewMessage('');
      fetchMessages();
    }
    setSending(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl h-[80vh] flex flex-col animate-fade-in">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Review #{review.id}</h2>
            <div className="flex items-center gap-2 text-sm text-gray-600 mt-1">
              <span className="font-medium">{review.user_name}</span>
              <span>&bull;</span>
              <span>{review.business_name}</span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <i className="ri-close-line text-2xl text-gray-500"></i>
          </button>
        </div>
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center mb-1">
            {Array.from({ length: 5 }, (_, i) => (
              <i key={i} className={`ri-star-${i < review.rating ? 'fill' : 'line'} text-yellow-400 mr-1`}></i>
            ))}
            <span className="font-medium ml-2 text-gray-900">{review.review_title}</span>
          </div>
          <p className="text-sm text-gray-600 italic">"{review.review_text}"</p>
        </div>
        <div className="flex-1 overflow-y-auto p-6 bg-white space-y-4">
          {loading ? (
            <div className="flex justify-center py-10">
              <i className="ri-loader-4-line text-2xl animate-spin text-gray-400"></i>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center text-gray-400 py-10">No messages yet.</div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender_type === 'admin' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[70%] rounded-2xl px-4 py-3 shadow-sm ${msg.sender_type === 'admin' ? 'bg-red-600 text-white rounded-br-none' : 'bg-gray-100 text-gray-800 border border-gray-200 rounded-bl-none'}`}>
                  <p className="text-sm whitespace-pre-wrap">{msg.message}</p>
                  <div className={`text-xs mt-1 ${msg.sender_type === 'admin' ? 'text-red-100' : 'text-gray-400'}`}>
                    {msg.timestamp ? new Date(msg.timestamp).toLocaleString() : ''}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <div className="flex gap-2">
            <input type="text" value={newMessage} onChange={(e) => setNewMessage(e.target.value)} placeholder="Type your reply..." onKeyDown={(e) => e.key === 'Enter' && handleSend()} className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-red-500 outline-none transition-all" />
            <button onClick={handleSend} disabled={sending || !newMessage.trim()} className="px-6 py-3 bg-red-600 text-white rounded-xl hover:bg-red-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
              {sending ? <i className="ri-loader-4-line animate-spin"></i> : <i className="ri-send-plane-fill"></i>}
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const HistoryModal = ({ user, reviews, onClose, onToggleAttended }: { user: any, reviews: Review[], onClose: () => void, onToggleAttended: (id: number) => Promise<void> }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl h-[85vh] flex flex-col animate-fade-in">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Review History</h2>
            <div className="text-sm text-gray-600 mt-1">User: <span className="font-semibold">{user.user_name}</span> ({user.user_email})</div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <i className="ri-close-line text-2xl text-gray-500"></i>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50 space-y-4">
          {reviews.length === 0 ? (
            <div className="text-center py-10 text-gray-500">No review history found.</div>
          ) : (
            reviews.map((review) => (
              <div key={review.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 relative">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <div className="flex">
                      {Array.from({ length: 5 }, (_, i) => (
                        <i key={i} className={`ri-star-${i < review.rating ? 'fill' : 'line'} text-yellow-400 text-sm`}></i>
                      ))}
                    </div>
                    <span className="text-sm text-gray-500">{new Date(review.date_submitted).toLocaleDateString()}</span>
                  </div>
                  <button onClick={() => onToggleAttended(review.id)} className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors border ${review.is_attended ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-600 border-gray-200 hover:bg-gray-200'}`}>
                    {review.is_attended ? 'Details Attended' : 'Mark Attended'}
                  </button>
                </div>
                <h4 className="font-semibold text-gray-900 mb-1">{review.review_title}</h4>
                <p className="text-sm text-gray-700 mb-3">{review.review_text}</p>
                <div className="flex gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs border ${review.status === 'published' ? 'bg-green-50 text-green-700 border-green-200' : 'bg-yellow-50 text-yellow-700 border-yellow-200'}`}>{review.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default function AdminReviews() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [selectedRating, setSelectedRating] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReview, setSelectedReview] = useState<Review | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'users'>('list');
  const [users, setUsers] = useState<any[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [historyModal, setHistoryModal] = useState<{ open: boolean, user: any, reviews: Review[] }>({
    open: false, user: null, reviews: []
  });
  const [totalPages, setTotalPagesState] = useState(1);

  const fetchReviews = async () => {
    try {
      setLoading(true);
      let url = `${API_BASE_URL}/api/admin/reviews?page=${currentPage}&limit=${itemsPerPage}`;
      if (selectedFilter !== 'all') url += `&status=${selectedFilter}`;
      const response = await fetch(url, { headers: getAuthHeaders() });
      if (response.ok) {
        const data = await response.json();
        if (data.reviews) {
          setReviews(data.reviews);
          const total = Math.ceil(data.total / itemsPerPage);
          setTotalPagesState(total > 0 ? total : 1);
        } else {
          setReviews(data);
          setTotalPagesState(1);
        }
      }
    } catch (e) {
      console.error("Failed to fetch reviews", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, [selectedFilter, currentPage]);

  const filteredReviews = reviews.filter(r => {
    if (selectedRating === 'all') return true;
    return Math.round(r.rating).toString() === selectedRating;
  });

  const handleReply = async (id: number, message: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/reviews/${id}/reply`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ message })
      });
      if (response.ok) return true;
      alert('Failed to send reply');
      return false;
    } catch (e) {
      alert('Error sending reply');
      return false;
    }
  };

  const handleUpdateStatus = async (id: number, status: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/reviews/${id}/status`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ status })
      });
      if (response.ok) {
        setReviews(prev => prev.map(r => r.id === id ? { ...r, status } : r));
      }
    } catch (e) {
      alert('Failed to update status');
    }
  };

  const handleToggleAttended = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/reviews/${id}/attended`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        // Update reviews in main list and history modal
        setReviews(prev => prev.map(r => r.id === id ? { ...r, is_attended: data.is_attended } : r));
        if (historyModal.open) {
          setHistoryModal(prev => ({
            ...prev,
            reviews: prev.reviews.map(r => r.id === id ? { ...r, is_attended: data.is_attended } : r)
          }));
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchUsers = async () => {
    setLoadingUsers(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/reviews/users`, { headers: getAuthHeaders() });
      if (res.ok) setUsers(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleViewHistory = async (user: any) => {
    setHistoryModal({ open: true, user, reviews: [] });
    // TODO: Pagination support for history in future if needed, currently fetching all?
    // The backend endpoint admin_get_user_reviews supports pagination now. Default 10.
    // For now we just fetch page 1.
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/reviews/user/${user.user_id}?page=1&limit=50`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setHistoryModal(prev => ({ ...prev, reviews: data.reviews }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <i key={i} className={`ri-star-${i < rating ? 'fill' : 'line'} text-yellow-400`}></i>
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

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar isMobileMenuOpen={isMobileMenuOpen} setIsMobileMenuOpen={setIsMobileMenuOpen} />
      <div className="flex-1 ml-0 flex flex-col">
        <AdminHeader setIsMobileMenuOpen={setIsMobileMenuOpen} />
        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            <div className="mb-6 flex justify-between items-end">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Customer Reviews</h1>
                <p className="text-gray-600">Manage feedback and engage with users</p>
              </div>
              <div className="flex gap-2">
                <button onClick={fetchReviews} className="p-2 text-gray-500 hover:text-red-600 transition-colors" title="Refresh">
                  <i className="ri-refresh-line text-xl"></i>
                </button>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <div className="flex border-b border-gray-200 mb-6">
                <button className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${viewMode === 'list' ? 'border-red-600 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`} onClick={() => setViewMode('list')}>All Reviews</button>
                <button className={`px-4 py-2 font-medium text-sm transition-colors border-b-2 ${viewMode === 'users' ? 'border-red-600 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`} onClick={() => { setViewMode('users'); fetchUsers(); }}>Group by User</button>
              </div>
              {viewMode === 'list' ? (
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Status</label>
                    <select value={selectedFilter} onChange={(e) => setSelectedFilter(e.target.value)} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500">
                      <option value="all">All Reviews</option>
                      <option value="published">Published</option>
                      <option value="pending">Pending</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Rating</label>
                    <select value={selectedRating} onChange={(e) => setSelectedRating(e.target.value)} className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500">
                      <option value="all">All Ratings</option>
                      <option value="5">5 Stars</option>
                      <option value="4">4 Stars</option>
                      <option value="3">3 Stars</option>
                      <option value="2">2 Stars</option>
                      <option value="1">1 Star</option>
                    </select>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">Viewing reviews grouped by distinct users. Click "History" to see all reviews for a user.</div>
              )}
            </div>
            {viewMode === 'list' ? (
              <div className="space-y-4">
                {loading ? <div className="text-center py-10 text-gray-500">Loading reviews...</div> : filteredReviews.length === 0 ? <div className="text-center py-10 text-gray-500">No reviews found.</div> : filteredReviews.map((review) => (
                  <div key={review.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 relative">
                    {/* Attended Badge/Button */}
                    <div className="absolute top-6 right-6 flex gap-2">
                      <button onClick={() => handleToggleAttended(review.id)} className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors border ${review.is_attended ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'}`}>
                        {review.is_attended ? <><i className="ri-check-line mr-1"></i>Attended</> : 'Mark Attended'}
                      </button>
                    </div>

                    <div className="flex items-start justify-between">
                      <div className="flex-1 pr-32">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center"><i className="ri-user-line text-red-600"></i></div>
                          <div>
                            <h3 className="font-semibold text-gray-900">{review.user_name}</h3>
                            <p className="text-sm text-gray-500">{review.business_name}</p>
                          </div>
                          <div className="flex">{renderStars(review.rating)}</div>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(review.status)}`}>{review.status}</span>
                        </div>
                        <h4 className="font-medium text-gray-900 mb-2">{review.review_title}</h4>
                        <p className="text-gray-700 mb-4">{review.review_text}</p>
                        <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                          <span>{new Date(review.date_submitted).toLocaleDateString()}</span>
                        </div>
                        <div className="flex gap-2">
                          <button onClick={() => { setSelectedReview(review); setIsModalOpen(true); }} className="px-4 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors text-sm font-medium flex items-center gap-2"><i className="ri-chat-1-line"></i> View Conversation ({review.conversation_count})</button>
                          {review.status === 'pending' && (<><button onClick={() => handleUpdateStatus(review.id, 'published')} className="px-4 py-2 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors text-sm">Approve</button><button onClick={() => handleUpdateStatus(review.id, 'rejected')} className="px-4 py-2 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors text-sm">Reject</button></>)}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {totalPages > 1 && (
                  <div className="mt-8 flex items-center justify-between">
                    <span className="text-sm text-gray-600">Page {currentPage} of {totalPages}</span>
                    <div className="flex gap-2">
                      <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50">Previous</button>
                      <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50">Next</button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Total Reviews</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Avg Rating</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Activity</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {loadingUsers ? <tr><td colSpan={5} className="px-6 py-10 text-center text-gray-500">Loading users...</td></tr> : users.length === 0 ? <tr><td colSpan={5} className="px-6 py-10 text-center text-gray-500">No users found.</td></tr> : users.map(user => (
                      <tr key={user.user_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap"><div className="flex items-center"><div className="h-10 w-10 flex-shrink-0 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">{user.user_name?.charAt(0) || 'U'}</div><div className="ml-4"><div className="text-sm font-medium text-gray-900">{user.user_name}</div><div className="text-sm text-gray-500">{user.user_email}</div></div></div></td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{user.review_count}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center"><div className="flex items-center justify-center"><span className="text-sm text-gray-900 font-medium mr-1">{user.average_rating}</span><i className="ri-star-fill text-yellow-400 text-xs"></i></div></td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.last_review_date ? new Date(user.last_review_date).toLocaleDateString() : '-'}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium"><button onClick={() => handleViewHistory(user)} className="text-blue-600 hover:text-blue-900 hover:bg-blue-50 px-3 py-1 rounded-md transition-colors">History</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
      {isModalOpen && selectedReview && <ConversationModal review={selectedReview} onClose={() => setIsModalOpen(false)} onReply={handleReply} />}
      {historyModal.open && historyModal.user && <HistoryModal user={historyModal.user} reviews={historyModal.reviews} onClose={() => setHistoryModal({ ...historyModal, open: false })} onToggleAttended={handleToggleAttended} />}
    </div>
  );
}