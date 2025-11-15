import { useState } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminUsers() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);

  const usersPerPage = 10;

  const [users, setUsers] = useState([
    {
      id: 1,
      name: 'Sarah Johnson',
      email: 'sarah.johnson@email.com',
      plan: 'Premium',
      status: 'active',
      joinDate: '2024-01-15',
      lastActive: '2 hours ago',
      analyses: 47,
      avatar: 'SJ'
    },
    {
      id: 2,
      name: 'Michael Chen',
      email: 'michael.chen@company.com',
      plan: 'Pro',
      status: 'active',
      joinDate: '2024-01-20',
      lastActive: '1 day ago',
      analyses: 23,
      avatar: 'MC'
    },
    {
      id: 3,
      name: 'Emily Rodriguez',
      email: 'emily.r@startup.io',
      plan: 'Basic',
      status: 'inactive',
      joinDate: '2024-02-01',
      lastActive: '1 week ago',
      analyses: 8,
      avatar: 'ER'
    },
    {
      id: 4,
      name: 'David Kim',
      email: 'david.kim@logistics.com',
      plan: 'Enterprise',
      status: 'active',
      joinDate: '2024-01-10',
      lastActive: '30 minutes ago',
      analyses: 156,
      avatar: 'DK'
    },
    {
      id: 5,
      name: 'Lisa Thompson',
      email: 'lisa@strategyplus.com',
      plan: 'Pro',
      status: 'suspended',
      joinDate: '2024-01-25',
      lastActive: '3 days ago',
      analyses: 34,
      avatar: 'LT'
    },
    {
      id: 6,
      name: 'James Wilson',
      email: 'james.wilson@growthcorp.com',
      plan: 'Premium',
      status: 'active',
      joinDate: '2024-02-05',
      lastActive: '5 hours ago',
      analyses: 67,
      avatar: 'JW'
    },
    {
      id: 7,
      name: 'Anna Martinez',
      email: 'anna.martinez@retail.com',
      plan: 'Basic',
      status: 'active',
      joinDate: '2024-02-10',
      lastActive: '1 hour ago',
      analyses: 12,
      avatar: 'AM'
    },
    {
      id: 8,
      name: 'Robert Taylor',
      email: 'robert.taylor@finance.org',
      plan: 'Enterprise',
      status: 'active',
      joinDate: '2024-01-05',
      lastActive: '15 minutes ago',
      analyses: 203,
      avatar: 'RT'
    },
    {
      id: 9,
      name: 'Jennifer Lee',
      email: 'jennifer.lee@marketing.co',
      plan: 'Pro',
      status: 'active',
      joinDate: '2024-02-12',
      lastActive: '3 hours ago',
      analyses: 29,
      avatar: 'JL'
    },
    {
      id: 10,
      name: 'Mark Anderson',
      email: 'mark.anderson@tech.com',
      plan: 'Premium',
      status: 'inactive',
      joinDate: '2024-01-30',
      lastActive: '2 weeks ago',
      analyses: 45,
      avatar: 'MA'
    },
    {
      id: 11,
      name: 'Sophie Brown',
      email: 'sophie.brown@consulting.com',
      plan: 'Basic',
      status: 'active',
      joinDate: '2024-02-15',
      lastActive: '6 hours ago',
      analyses: 7,
      avatar: 'SB'
    },
    {
      id: 12,
      name: 'Alex Turner',
      email: 'alex.turner@startup.io',
      plan: 'Pro',
      status: 'active',
      joinDate: '2024-02-18',
      lastActive: '1 hour ago',
      analyses: 18,
      avatar: 'AT'
    },
    {
      id: 13,
      name: 'Rachel Green',
      email: 'rachel.green@agency.com',
      plan: 'Premium',
      status: 'suspended',
      joinDate: '2024-01-12',
      lastActive: '1 week ago',
      analyses: 89,
      avatar: 'RG'
    },
    {
      id: 14,
      name: 'Tom Wilson',
      email: 'tom.wilson@corp.com',
      plan: 'Enterprise',
      status: 'active',
      joinDate: '2024-01-08',
      lastActive: '2 hours ago',
      analyses: 178,
      avatar: 'TW'
    },
    {
      id: 15,
      name: 'Maria Garcia',
      email: 'maria.garcia@business.com',
      plan: 'Basic',
      status: 'active',
      joinDate: '2024-02-20',
      lastActive: '4 hours ago',
      analyses: 5,
      avatar: 'MG'
    }
  ]);

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || user.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  // Pagination
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
  const startIndex = (currentPage - 1) * usersPerPage;
  const endIndex = startIndex + usersPerPage;
  const currentUsers = filteredUsers.slice(startIndex, endIndex);

  const handleViewUser = (user: any) => {
    setSelectedUser(user);
    setIsUserModalOpen(true);
  };

  const handleDeactivateUser = (userId: number) => {
    setUsers(users.map(user => 
      user.id === userId 
        ? { ...user, status: user.status === 'active' ? 'inactive' : 'active' }
        : user
    ));
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
    switch (plan) {
      case 'Basic': return 'bg-blue-100 text-blue-600';
      case 'Pro': return 'bg-purple-100 text-purple-600';
      case 'Premium': return 'bg-orange-100 text-orange-600';
      case 'Enterprise': return 'bg-red-100 text-red-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const userStats = {
    total: users.length,
    active: users.filter(u => u.status === 'active').length,
    inactive: users.filter(u => u.status === 'inactive').length,
    suspended: users.filter(u => u.status === 'suspended').length
  };

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
              
              {/* Backdrop for click outside to close */}
              {isProfileDropdownOpen && (
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setIsProfileDropdownOpen(false)}
                ></div>
              )}
              
              {/* Profile Dropdown */}
              {isProfileDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <Link 
                    to="/admin/profile"
                    onClick={() => setIsProfileDropdownOpen(false)}
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
                  >
                    <i className="ri-user-line text-gray-500"></i>
                    Profile
                  </Link>
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
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">User Management</h1>
              <p className="text-gray-600">Manage user accounts, subscriptions, and access permissions</p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-line text-xl text-blue-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Total Users</h3>
                <p className="text-2xl font-bold text-gray-900">{userStats.total}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-check-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">
                    {((userStats.active / userStats.total) * 100).toFixed(1)}%
                  </span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Active Users</h3>
                <p className="text-2xl font-bold text-gray-900">{userStats.active}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-unfollow-line text-xl text-gray-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Inactive Users</h3>
                <p className="text-2xl font-bold text-gray-900">{userStats.inactive}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <i className="ri-user-forbid-line text-xl text-red-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Suspended</h3>
                <p className="text-2xl font-bold text-gray-900">{userStats.suspended}</p>
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
                  <option value="inactive">Inactive</option>
                  <option value="suspended">Suspended</option>
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
                    {currentUsers.map((user) => (
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
                            {user.status.charAt(0).toUpperCase() + user.status.slice(1)}
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
                            <button 
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                              title="Edit User"
                            >
                              <i className="ri-edit-line"></i>
                            </button>
                            <button 
                              onClick={() => handleDeactivateUser(user.id)}
                              className={`p-2 rounded-lg transition-colors ${
                                user.status === 'active' 
                                  ? 'text-red-600 hover:bg-red-50' 
                                  : 'text-green-600 hover:bg-green-50'
                              }`}
                              title={user.status === 'active' ? 'Deactivate User' : 'Activate User'}
                            >
                              <i className={user.status === 'active' ? 'ri-user-forbid-line' : 'ri-user-check-line'}></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-sm text-gray-600">
                  Showing {startIndex + 1} to {Math.min(endIndex, filteredUsers.length)} of {filteredUsers.length} results
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    Previous
                  </button>
                  
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap ${
                        currentPage === page
                          ? 'bg-red-600 text-white'
                          : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                  
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
      {isUserModalOpen && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
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
              
              <div className="space-y-4">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                    <span className="text-xl font-medium text-red-600">{selectedUser.avatar}</span>
                  </div>
                  <div>
                    <h4 className="text-xl font-semibold text-gray-900">{selectedUser.name}</h4>
                    <p className="text-gray-600">{selectedUser.email}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Plan</label>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getPlanColor(selectedUser.plan)}`}>
                      {selectedUser.plan}
                    </span>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600 mb-1">Status</label>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(selectedUser.status)}`}>
                      {selectedUser.status.charAt(0).toUpperCase() + selectedUser.status.slice(1)}
                    </span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Join Date</label>
                  <p className="text-gray-900">{selectedUser.joinDate}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Last Active</label>
                  <p className="text-gray-900">{selectedUser.lastActive}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Total Analyses</label>
                  <p className="text-gray-900">{selectedUser.analyses}</p>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                  Edit User
                </button>
                <button 
                  onClick={() => {
                    handleDeactivateUser(selectedUser.id);
                    setIsUserModalOpen(false);
                  }}
                  className={`flex-1 px-4 py-2 rounded-lg transition-colors whitespace-nowrap ${
                    selectedUser.status === 'active'
                      ? 'bg-red-100 text-red-600 hover:bg-red-200'
                      : 'bg-green-100 text-green-600 hover:bg-green-200'
                  }`}
                >
                  {selectedUser.status === 'active' ? 'Deactivate' : 'Activate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
