import { useState, useEffect } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import { getAuthHeaders } from '../../../utils/auth';

interface User {
  id: number;
  name: string;
  email: string;
  plan: string;
  status: 'active' | 'suspended' | 'inactive';
  joinDate: string;
  lastActive: string;
  analyses: number;
  avatar: string;
}

interface UserDetails extends User {
  subscription_status: string;
  subscription_plan: string;
  total_chops: number;
  referral_chops: number;
  alert_reading_chops: number;
  insight_reading_chops: number;
  referral_count: number;
  referrals: string[];
  insight_sharing_chops: number;
  alert_sharing_chops: number;
  days_remaining: number;
  referral_code: string;
  is_active: boolean;
}

interface UserStats {
  total: number;
  pro: number;
  free: number;
  deactivated: number;
  inactive: number;
  active?: number;
}

export default function AdminUsers() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedUser, setSelectedUser] = useState<UserDetails | null>(null);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const [stats, setStats] = useState<UserStats>({
    total: 0,
    pro: 0,
    free: 0,
    deactivated: 0,
    inactive: 0,
    active: 0
  });

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchStats();
    fetchUsers();
  }, [currentPage, filterStatus]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (currentPage === 1) fetchUsers();
      else setCurrentPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/control/users/stats`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        // Add dummy active if missing to satisfy potential types, or just map pro -> active logic
        setStats({ ...data, active: data.pro });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams({
        page: currentPage.toString(),
        limit: '10',
        search: searchTerm,
        status: filterStatus
      });

      const response = await fetch(`${API_BASE_URL}/api/control/users?${queryParams}`, {
        headers: getAuthHeaders()
      });

      if (response.ok) {
        const data = await response.json();
        setUsers(data.users);
        setTotalPages(data.totalPages);
        setTotalUsers(data.total);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivateUser = async (user: UserDetails) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/control/users/${user.id}/status`, {
        method: 'PATCH',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        // Update local state in list
        setUsers(users.map(u =>
          u.id === user.id
            ? { ...u, status: u.status === 'active' ? 'suspended' : 'active' }
            : u
        ));

        // Update modal internal state
        if (selectedUser && selectedUser.id === user.id) {
          setSelectedUser({
            ...selectedUser,
            status: selectedUser.status === 'active' ? 'suspended' : 'active',
            is_active: !selectedUser.is_active
          });
        }

        fetchStats();
      } else {
        const err = await response.json();
        alert(`Error: ${err.detail}`);
      }
    } catch (error) {
      console.error('Error updating user status:', error);
      alert('Failed to update user status');
    }
  };

  const handleViewUser = async (user: User) => {
    setIsUserModalOpen(true);
    setLoadingDetails(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/control/users/${user.id}`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const details = await response.json();
        // Merge list data (avatar, lastActive) with details if needed, 
        // but details should have most info. Avatar logic might need repeating or passing.
        const fullDetails: UserDetails = {
          ...user, // Default fallback
          ...details,
          status: details.is_active ? 'active' : 'suspended', // Map bool to string
          avatar: user.avatar // Keep avatar from list or regenerate
        };
        setSelectedUser(fullDetails);
      } else {
        alert("Failed to load user details");
        setIsUserModalOpen(false);
      }
    } catch (error) {
      console.error("Error fetching user details:", error);
    } finally {
      setLoadingDetails(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-600';
      case 'inactive': return 'bg-gray-100 text-gray-600';
      case 'suspended': return 'bg-red-100 text-red-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getPlanColor = (plan: string) => {
    if (!plan) return 'bg-gray-100 text-gray-600';
    const lowerPlan = plan.toLowerCase();

    // Free -> Normal Gray
    if (lowerPlan.includes('free') || lowerPlan.includes('basic')) return 'bg-gray-100 text-gray-600';

    // Yearly -> Normal Orange
    if (lowerPlan.includes('yearly')) return 'bg-orange-100 text-orange-600';

    // Monthly -> Sky Blue
    if (lowerPlan.includes('monthly') || lowerPlan.includes('pro')) return 'bg-sky-100 text-sky-600';

    // Fallbacks
    if (lowerPlan.includes('premium')) return 'bg-orange-100 text-orange-600';
    return 'bg-gray-100 text-gray-600';
  };

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
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">User Management</h1>
              <p className="text-gray-600">Manage user accounts, subscriptions, and access permissions</p>
            </div>

            {/* Stats Cards - Updated grid to 5 cols and reduced padding */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 md:p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-line text-lg text-blue-600"></i>
                  </div>
                </div>
                <h3 className="text-xs font-medium text-gray-600 mb-1">Total Users</h3>
                <p className="text-xl font-bold text-gray-900">{stats.total}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 md:p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-vip-crown-line text-lg text-purple-600"></i>
                  </div>
                </div>
                <h3 className="text-xs font-medium text-gray-600 mb-1">Pro Users</h3>
                <p className="text-xl font-bold text-gray-900">{stats.pro}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 md:p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-smile-line text-lg text-gray-600"></i>
                  </div>
                </div>
                <h3 className="text-xs font-medium text-gray-600 mb-1">Free Users</h3>
                <p className="text-xl font-bold text-gray-900">{stats.free}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 md:p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-forbid-line text-lg text-red-600"></i>
                  </div>
                </div>
                <h3 className="text-xs font-medium text-gray-600 mb-1">Deactivated</h3>
                <p className="text-xl font-bold text-gray-900">{stats.deactivated}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 md:p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                    <i className="ri-zzz-line text-lg text-yellow-600"></i>
                  </div>
                </div>
                <h3 className="text-xs font-medium text-gray-600 mb-1">Inactive Users</h3>
                <p className="text-xl font-bold text-gray-900">{stats.inactive}</p>
              </div>
            </div>

            {/* Search and Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Search users by name or email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  />
                </div>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="suspended">Deactivated (Suspended)</option>
                  <option value="inactive">Inactive (Dormant &gt; 3 mo)</option>
                  <option value="free">Free Users</option>
                </select>
              </div>
            </div>

            {/* Users Table */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-6">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Plan</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Analyses</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Last Active</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {loading ? (
                      <tr><td colSpan={6} className="text-center py-8">Loading users...</td></tr>
                    ) : users.length === 0 ? (
                      <tr><td colSpan={6} className="text-center py-8">No users found.</td></tr>
                    ) : (
                      users.map((user) => (
                        <tr key={user.id} className="hover:bg-gray-50">
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                                <span className="text-sm font-medium text-red-600">{user.avatar}</span>
                              </div>
                              <div>
                                <p className="font-medium text-gray-900">{user.name}</p>
                                <p className="text-sm text-gray-500">{user.email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPlanColor(user.plan)}`}>
                              {user.plan}
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(user.status)}`}>
                              {user.status === 'suspended' ? 'Deactivated' : 'Active'}
                            </span>
                          </td>
                          <td className="py-4 px-4">
                            <span className="font-medium text-gray-900">{user.analyses}</span>
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-sm text-gray-600">{user.lastActive}</span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleViewUser(user)}
                                className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                title="View User"
                              >
                                <i className="ri-eye-line"></i>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-sm text-gray-600">
                  Showing {(currentPage - 1) * 10 + 1} to {Math.min(currentPage * 10, totalUsers)} of {totalUsers} results
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    Previous
                  </button>

                  <span className="px-3 py-2 text-sm text-gray-600">
                    Page {currentPage} of {totalPages}
                  </span>

                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* User Details Modal */}
      {isUserModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">User Details</h3>
                <button
                  onClick={() => setIsUserModalOpen(false)}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <i className="ri-close-line text-xl"></i>
                </button>
              </div>

              {loadingDetails || !selectedUser ? (
                <div className="text-center py-10">Loading details...</div>
              ) : (
                <div className="space-y-6">
                  {/* Header Info */}
                  <div className="flex items-center gap-4 border-b border-gray-100 pb-6">
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                      <span className="text-xl font-medium text-red-600">{selectedUser.avatar}</span>
                    </div>
                    <div>
                      <h4 className="text-xl font-semibold text-gray-900">{selectedUser.name}</h4>
                      <p className="text-gray-600">{selectedUser.email}</p>
                      <p className="text-sm text-gray-400 mt-1">ID: {selectedUser.id}</p>
                    </div>
                  </div>

                  {/* Subscription Section */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h5 className="font-medium text-gray-900 mb-3 border-b border-gray-200 pb-2">Subscription</h5>
                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Status</label>
                        <div className={`mt-1 inline-flex px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(selectedUser.status)}`}>
                          {selectedUser.subscription_plan?.toLowerCase().includes('free') ? 'Free' : (selectedUser.status === 'suspended' ? 'Deactivated' : 'Active')}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Plan</label>
                        <div className="mt-1 font-medium">{selectedUser.subscription_plan || 'None'}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Pro Days Remaining</label>
                        <div className="mt-1 font-medium">{selectedUser.days_remaining} Days</div>
                      </div>
                    </div>
                  </div>

                  {/* Chops System */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h5 className="font-medium text-gray-900 mb-3 border-b border-gray-200 pb-2">Chops System</h5>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Total Chops</label>
                        <div className="font-bold text-gray-900">{selectedUser.total_chops}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Referral Chops</label>
                        <div>{selectedUser.referral_chops}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Alert Read</label>
                        <div>{selectedUser.alert_reading_chops}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Alert Share</label>
                        <div>{selectedUser.alert_sharing_chops}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Insight Read</label>
                        <div>{selectedUser.insight_reading_chops}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Insight Share</label>
                        <div>{selectedUser.insight_sharing_chops}</div>
                      </div>
                    </div>
                  </div>

                  {/* Referrals */}
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h5 className="font-medium text-gray-900 mb-3 border-b border-gray-200 pb-2">Referrals</h5>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Referral Code</label>
                        <div className="font-mono bg-white px-2 py-1 rounded border inline-block">{selectedUser.referral_code || 'N/A'}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Total Referrals</label>
                        <div className="font-bold">{selectedUser.referral_count}</div>
                      </div>
                    </div>

                    <div className="mt-4">
                      <label className="text-xs text-gray-500 uppercase block mb-2">Referred Users</label>
                      {selectedUser.referrals && selectedUser.referrals.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {selectedUser.referrals.map((refName, idx) => (
                            <span key={idx} className="bg-white border border-gray-200 px-2 py-1 rounded text-xs text-gray-700">
                              {refName}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400">No referrals yet.</p>
                      )}
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="text-xs text-gray-400 grid grid-cols-2 gap-4 pt-2">
                    <div>
                      Joined: {new Date(selectedUser.joinDate).toLocaleDateString()}
                    </div>
                    <div>
                      Last Active: {selectedUser.lastActive}
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6 pt-6 border-t border-gray-100">
                    <button
                      onClick={() => setIsUserModalOpen(false)}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors whitespace-nowrap"
                    >
                      Close
                    </button>

                    <button
                      onClick={() => handleDeactivateUser(selectedUser)}
                      className={`flex-1 px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${selectedUser.status === 'active'
                        ? 'bg-red-100 text-red-600 hover:bg-red-200'
                        : 'bg-green-100 text-green-600 hover:bg-green-200'
                        }`}
                    >
                      {selectedUser.status === 'active' ? 'Deactivate User' : 'Activate User'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
