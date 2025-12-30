import { useState, useEffect } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import {
  useUserStats,
  useUsers,
  useUserDetail,
  useToggleUserStatus,
  type User,
  type UserDetails
} from '../../../api/admin-users';

export default function AdminUsers() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);

  // TanStack Query hooks
  const { data: stats = { total: 0, pro: 0, free: 0, deactivated: 0, inactive: 0 } } = useUserStats();
  const { data: usersData, isLoading: loading, refetch } = useUsers({
    page: currentPage,
    limit: 10,
    status: filterStatus,
    search: debouncedSearch
  });
  const { data: selectedUser, isLoading: loadingDetails } = useUserDetail(selectedUserId);
  const toggleStatusMutation = useToggleUserStatus();

  const users = usersData?.users || [];
  const totalPages = usersData?.totalPages || 1;
  const totalUsers = usersData?.total || 0;

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setCurrentPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleViewUser = (user: User) => {
    setSelectedUserId(user.id);
    setIsUserModalOpen(true);
  };

  const handleDeactivateUser = async (user: UserDetails) => {
    try {
      await toggleStatusMutation.mutateAsync(user.id);
    } catch (error) {
      console.error("Error toggling user status:", error);
      alert("Failed to update user status");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-600';
      case 'inactive': return 'bg-yellow-100 text-yellow-600';
      case 'suspended': return 'bg-red-100 text-red-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active': return 'Active';
      case 'inactive': return 'Inactive';
      case 'suspended': return 'Deactivated';
      default: return status;
    }
  };

  const getPlanColor = (plan: string) => {
    if (!plan) return 'bg-gray-100 text-gray-600';
    const lowerPlan = plan.toLowerCase();

    if (lowerPlan.includes('free') || lowerPlan.includes('basic')) return 'bg-gray-100 text-gray-600';
    if (lowerPlan.includes('yearly')) return 'bg-orange-100 text-orange-600';
    if (lowerPlan.includes('monthly') || lowerPlan.includes('pro')) return 'bg-sky-100 text-sky-600';
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
            <div className="mb-6 md:mb-8 flex justify-between items-start">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">User Management</h1>
                <p className="text-gray-600">Manage user accounts, subscriptions, and access permissions</p>
              </div>
              <button onClick={() => refetch()} className="p-2 text-gray-500 hover:text-red-600 transition-colors" title="Refresh">
                <i className="ri-refresh-line text-xl"></i>
              </button>
            </div>

            {/* Stats Cards */}
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
                  onChange={(e) => { setFilterStatus(e.target.value); setCurrentPage(1); }}
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
                              {getStatusLabel(user.status)}
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
                  onClick={() => { setIsUserModalOpen(false); setSelectedUserId(null); }}
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
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Account Status</label>
                        <div className={`mt-1 inline-flex px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(selectedUser.status)}`}>
                          {getStatusLabel(selectedUser.status)}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Subscription</label>
                        <div className={`mt-1 inline-flex px-2 py-1 rounded-full text-xs font-semibold ${selectedUser.subscription_status === 'active' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'}`}>
                          {selectedUser.subscription_status === 'active' ? 'Pro' : 'Free'}
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Plan</label>
                        <div className="mt-1 font-medium">{selectedUser.subscription_plan || 'Free'}</div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 uppercase">Days Remaining</label>
                        <div className="mt-1 font-medium">{selectedUser.days_remaining || 0} Days</div>
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

                  {/* Action Button - Only Activate/Deactivate */}
                  <div className="mt-6 pt-6 border-t border-gray-100">
                    <button
                      onClick={() => handleDeactivateUser(selectedUser)}
                      disabled={toggleStatusMutation.isPending}
                      className={`w-full px-4 py-3 rounded-lg font-medium transition-colors ${
                        selectedUser.status === 'suspended'
                          ? 'bg-green-600 text-white hover:bg-green-700'
                          : 'bg-red-600 text-white hover:bg-red-700'
                      } disabled:opacity-50`}
                    >
                      {toggleStatusMutation.isPending
                        ? 'Updating...'
                        : selectedUser.status === 'suspended'
                          ? 'Activate User'
                          : 'Deactivate User'
                      }
                    </button>
                    <p className="text-xs text-gray-400 text-center mt-2">
                      {selectedUser.status === 'suspended'
                        ? 'Activating will allow this user to log in again'
                        : selectedUser.status === 'inactive'
                          ? 'This user is inactive (no login for 30+ days). Deactivating will prevent login.'
                          : 'Deactivating will prevent this user from logging in'
                      }
                    </p>
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
