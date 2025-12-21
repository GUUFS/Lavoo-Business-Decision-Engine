
import { useState } from 'react';
// import DashboardSidebar from '../../../components/feature/DashboardSidebar';
// import Footer from '../../../components/feature/Footer';

export default function AccountsPage() {
  // const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedTab, setSelectedTab] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const tabs = [
    { id: 'all', name: 'All Accounts', count: 247 },
    { id: 'active', name: 'Active', count: 189 },
    { id: 'inactive', name: 'Inactive', count: 34 },
    { id: 'pending', name: 'Pending', count: 24 }
  ];

  const accounts = [
    {
      id: 1,
      name: 'Sarah Johnson',
      email: 'sarah.johnson@techcorp.com',
      company: 'TechCorp Solutions',
      role: 'Admin',
      status: 'active',
      lastLogin: '2 hours ago',
      joinDate: 'Mar 15, 2024',
      avatar: 'SJ'
    },
    {
      id: 2,
      name: 'Michael Chen',
      email: 'michael.chen@innovate.io',
      company: 'Innovate Labs',
      role: 'User',
      status: 'active',
      lastLogin: '1 day ago',
      joinDate: 'Feb 28, 2024',
      avatar: 'MC'
    },
    {
      id: 3,
      name: 'Emily Rodriguez',
      email: 'emily.r@startup.com',
      company: 'StartupCo',
      role: 'Manager',
      status: 'inactive',
      lastLogin: '1 week ago',
      joinDate: 'Jan 12, 2024',
      avatar: 'ER'
    },
    {
      id: 4,
      name: 'David Kim',
      email: 'david.kim@enterprise.net',
      company: 'Enterprise Solutions',
      role: 'User',
      status: 'pending',
      lastLogin: 'Never',
      joinDate: 'Mar 20, 2024',
      avatar: 'DK'
    },
    {
      id: 5,
      name: 'Lisa Thompson',
      email: 'lisa.thompson@digital.agency',
      company: 'Digital Agency Pro',
      role: 'Admin',
      status: 'active',
      lastLogin: '5 minutes ago',
      joinDate: 'Feb 05, 2024',
      avatar: 'LT'
    },
    {
      id: 6,
      name: 'James Wilson',
      email: 'james.wilson@consulting.biz',
      company: 'Wilson Consulting',
      role: 'User',
      status: 'active',
      lastLogin: '3 hours ago',
      joinDate: 'Mar 08, 2024',
      avatar: 'JW'
    }
  ];

  const filteredAccounts = accounts.filter(account => {
    const matchesTab = selectedTab === 'all' || account.status === selectedTab;
    const matchesSearch = account.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      account.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      account.company.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesTab && matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-600';
      case 'inactive':
        return 'bg-gray-100 text-gray-600';
      case 'pending':
        return 'bg-yellow-100 text-yellow-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'Admin':
        return 'bg-purple-100 text-purple-600';
      case 'Manager':
        return 'bg-blue-100 text-blue-600';
      case 'User':
        return 'bg-orange-100 text-orange-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">


      <div className="flex-1 p-4 md:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6 md:mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Account Management</h1>
                <p className="text-gray-600">Manage user accounts and permissions</p>
              </div>
              <button className="bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                <i className="ri-add-line mr-2"></i>
                Add Account
              </button>
            </div>
          </div>

          {/* Search and Tabs */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
            <div className="flex flex-col lg:flex-row gap-4 mb-6">
              {/* Search */}
              <div className="flex-1">
                <div className="relative">
                  <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                  <input
                    type="text"
                    placeholder="Search accounts..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm"
                  />
                </div>
              </div>

              {/* Filter Buttons */}
              <div className="flex gap-2">
                <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                  <i className="ri-filter-line mr-2"></i>
                  Filter
                </button>
                <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                  <i className="ri-download-line mr-2"></i>
                  Export
                </button>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 overflow-x-auto pb-2">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSelectedTab(tab.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${selectedTab === tab.id
                      ? 'bg-orange-100 text-orange-600 border border-orange-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                >
                  {tab.name} ({tab.count})
                </button>
              ))}
            </div>
          </div>

          {/* Accounts Table */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            {/* Desktop Table */}
            <div className="hidden lg:block overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left py-4 px-6 font-medium text-gray-700">User</th>
                    <th className="text-left py-4 px-6 font-medium text-gray-700">Company</th>
                    <th className="text-left py-4 px-6 font-medium text-gray-700">Role</th>
                    <th className="text-left py-4 px-6 font-medium text-gray-700">Status</th>
                    <th className="text-left py-4 px-6 font-medium text-gray-700">Last Login</th>
                    <th className="text-left py-4 px-6 font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredAccounts.map((account) => (
                    <tr key={account.id} className="hover:bg-gray-50">
                      <td className="py-4 px-6">
                        <div className="flex items-center">
                          <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                            <span className="text-orange-600 font-medium text-sm">{account.avatar}</span>
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">{account.name}</div>
                            <div className="text-sm text-gray-500">{account.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-gray-900">{account.company}</td>
                      <td className="py-4 px-6">
                        <span className={`text-xs px-2 py-1 rounded-full ${getRoleColor(account.role)}`}>
                          {account.role}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <span className={`text-xs px-2 py-1 rounded-full capitalize ${getStatusColor(account.status)}`}>
                          {account.status}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-gray-600 text-sm">{account.lastLogin}</td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <button className="text-gray-400 hover:text-orange-600 transition-colors">
                            <i className="ri-edit-line"></i>
                          </button>
                          <button className="text-gray-400 hover:text-red-600 transition-colors">
                            <i className="ri-delete-bin-line"></i>
                          </button>
                          <button className="text-gray-400 hover:text-gray-600 transition-colors">
                            <i className="ri-more-line"></i>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Cards */}
            <div className="lg:hidden divide-y divide-gray-200">
              {filteredAccounts.map((account) => (
                <div key={account.id} className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center">
                      <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                        <span className="text-orange-600 font-medium">{account.avatar}</span>
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">{account.name}</div>
                        <div className="text-sm text-gray-500">{account.email}</div>
                      </div>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600">
                      <i className="ri-more-line"></i>
                    </button>
                  </div>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Company:</span>
                      <span className="text-gray-900">{account.company}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Role:</span>
                      <span className={`text-xs px-2 py-1 rounded-full ${getRoleColor(account.role)}`}>
                        {account.role}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Status:</span>
                      <span className={`text-xs px-2 py-1 rounded-full capitalize ${getStatusColor(account.status)}`}>
                        {account.status}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Last Login:</span>
                      <span className="text-gray-900">{account.lastLogin}</span>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    <button className="flex-1 bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors">
                      Edit
                    </button>
                    <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
                      View
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Empty State */}
          {filteredAccounts.length === 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="ri-user-line text-2xl text-gray-400"></i>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No accounts found</h3>
              <p className="text-gray-600 mb-6">Try adjusting your search terms or filters</p>
              <button className="bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                Add New Account
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
