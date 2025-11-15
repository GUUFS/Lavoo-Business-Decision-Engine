import { useState } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminRevenue() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [timeFilter, setTimeFilter] = useState('month');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const revenueData = {
    total: 89247,
    monthly: 89247,
    growth: 15.3,
    subscriptions: 67890,
    referralCommissions: 21357,
    refunds: 2156
  };

  const subscriptionPlans = [
    {
      name: 'Premium',
      price: 149,
      subscribers: 5496,
      revenue: 819104,
      growth: 22.1
    }
  ];

  const recentTransactions = [
    {
      id: 'TXN-2024-001',
      user: 'Sarah Johnson',
      plan: 'Premium',
      amount: 149,
      type: 'subscription',
      status: 'completed',
      date: '2024-02-26 14:32',
      method: 'Credit Card'
    },
    {
      id: 'TXN-2024-002',
      user: 'Michael Chen',
      plan: 'Pro',
      amount: 79,
      type: 'subscription',
      status: 'completed',
      date: '2024-02-26 13:45',
      method: 'PayPal'
    },
    {
      id: 'TXN-2024-003',
      user: 'Emily Rodriguez',
      plan: 'Basic',
      amount: 29,
      type: 'subscription',
      status: 'pending',
      date: '2024-02-26 12:18',
      method: 'Bank Transfer'
    },
    {
      id: 'TXN-2024-004',
      user: 'David Kim',
      plan: 'Enterprise',
      amount: 299,
      type: 'subscription',
      status: 'completed',
      date: '2024-02-26 11:22',
      method: 'Credit Card'
    },
    {
      id: 'TXN-2024-005',
      user: 'Lisa Thompson',
      plan: 'Premium',
      amount: 149,
      type: 'refund',
      status: 'processed',
      date: '2024-02-26 10:15',
      method: 'Credit Card'
    },
    {
      id: 'TXN-2024-006',
      user: 'John Davis',
      plan: 'Pro',
      amount: 79,
      type: 'subscription',
      status: 'completed',
      date: '2024-02-25 16:45',
      method: 'Credit Card'
    },
    {
      id: 'TXN-2024-007',
      user: 'Maria Garcia',
      plan: 'Basic',
      amount: 29,
      type: 'subscription',
      status: 'completed',
      date: '2024-02-25 14:20',
      method: 'PayPal'
    },
    {
      id: 'TXN-2024-008',
      user: 'Robert Brown',
      plan: 'Premium',
      amount: 149,
      type: 'subscription',
      status: 'failed',
      date: '2024-02-25 11:30',
      method: 'Credit Card'
    }
  ];

  // Pagination calculations
  const totalPages = Math.ceil(recentTransactions.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentTransactions = recentTransactions.slice(startIndex, endIndex);

  const monthlyRevenue = [
    { month: 'Jan', revenue: 67234, analyses: 1247 },
    { month: 'Feb', revenue: 89247, analyses: 1523 },
    { month: 'Mar', revenue: 0, analyses: 0 },
    { month: 'Apr', revenue: 0, analyses: 0 },
    { month: 'May', revenue: 0, analyses: 0 },
    { month: 'Jun', revenue: 0, analyses: 0 }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-600';
      case 'pending': return 'bg-yellow-100 text-yellow-600';
      case 'failed': return 'bg-red-100 text-red-600';
      case 'processed': return 'bg-blue-100 text-blue-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'subscription': return 'bg-green-100 text-green-600';
      case 'one_time': return 'bg-blue-100 text-blue-600';
      case 'refund': return 'bg-red-100 text-red-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />
      
      <div className="flex-1 flex flex-col">
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
              <button className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-red-600"></i>
                </div>
                <span className="font-medium text-gray-900">Admin User</span>
                <i className="ri-arrow-down-s-line text-gray-400"></i>
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Revenue Analytics</h1>
              <p className="text-gray-600">Monitor subscription revenue, transactions, and financial performance</p>
            </div>

            {/* Revenue Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-money-dollar-circle-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">+{revenueData.growth}%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Monthly Revenue</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueData.monthly.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-refresh-line text-xl text-blue-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">+18.2%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Subscription Revenue</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueData.subscriptions.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-share-line text-xl text-purple-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">+8.7%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Referral Commissions</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueData.referralCommissions.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <i className="ri-refund-line text-xl text-red-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-red-100 text-red-600">-2.1%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Refunds</h3>
                <p className="text-2xl font-bold text-gray-900">${revenueData.refunds.toLocaleString()}</p>
              </div>
            </div>

            {/* Subscription Plans Performance */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Subscription Plans Performance</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {subscriptionPlans.map((plan) => (
                  <div key={plan.name} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-gray-900">{plan.name}</h4>
                      <span className="text-lg font-bold text-gray-900">${plan.price}</span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Subscribers</span>
                        <span className="font-medium">{plan.subscribers.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Revenue</span>
                        <span className="font-medium">${plan.revenue.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Growth</span>
                        <span className={`font-medium ${plan.growth > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          +{plan.growth}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Revenue Chart */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Revenue Trend</h3>
                <select
                  value={timeFilter}
                  onChange={(e) => setTimeFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                >
                  <option value="week">Last 7 Days</option>
                  <option value="month">Last 6 Months</option>
                  <option value="year">Last Year</option>
                </select>
              </div>
              <div className="h-64 flex items-end justify-between gap-4">
                {monthlyRevenue.map((data, index) => (
                  <div key={index} className="flex-1 flex flex-col items-center">
                    <div 
                      className="w-full bg-orange-500 rounded-t-lg mb-2 min-h-[20px]"
                      style={{ height: `${(data.revenue / 100000) * 200}px` }}
                    ></div>
                    <span className="text-sm text-gray-600">{data.month}</span>
                    <span className="text-xs text-gray-500">${(data.revenue / 1000).toFixed(0)}k</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Transactions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Recent Transactions</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Transaction ID</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Plan</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Amount</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Type</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {currentTransactions.map((transaction) => (
                      <tr key={transaction.id} className="hover:bg-gray-50">
                        <td className="py-4 px-4">
                          <span className="font-mono text-sm text-gray-900">{transaction.id}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className="font-medium text-gray-900">{transaction.user}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-gray-900">{transaction.plan}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className="font-medium text-gray-900">${transaction.amount}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(transaction.type)}`}>
                            {transaction.type.replace('_', ' ').charAt(0).toUpperCase() + transaction.type.replace('_', ' ').slice(1)}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(transaction.status)}`}>
                            {transaction.status.charAt(0).toUpperCase() + transaction.status.slice(1)}
                          </span>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-sm text-gray-600">{transaction.date}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                      Showing {startIndex + 1} to {Math.min(endIndex, recentTransactions.length)} of {recentTransactions.length} transactions
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                      >
                        Previous
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                        <button
                          key={page}
                          onClick={() => setCurrentPage(page)}
                          className={`px-3 py-1 rounded-lg text-sm font-medium whitespace-nowrap ${
                            currentPage === page
                              ? 'bg-red-600 text-white'
                              : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                      <button
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}