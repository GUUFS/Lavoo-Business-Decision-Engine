
import { useState } from 'react';
import AdminSidebar from '../../components/feature/AdminSidebar';
import { Link } from 'react-router-dom';

export default function AdminDashboard() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);

  const stats = [
    {
      title: 'Total Users',
      value: '12,847',
      change: '+12.5%',
      changeType: 'positive',
      icon: 'ri-user-line',
      color: 'blue'
    },
    {
      title: 'Active Analyses',
      value: '3,429',
      change: '+8.2%',
      changeType: 'positive',
      icon: 'ri-brain-line',
      color: 'green'
    },
    {
      title: 'Monthly Revenue',
      value: '$89,247',
      change: '+15.3%',
      changeType: 'positive',
      icon: 'ri-money-dollar-circle-line',
      color: 'orange'
    },
    {
      title: 'System Uptime',
      value: '99.9%',
      change: '+0.1%',
      changeType: 'positive',
      icon: 'ri-server-line',
      color: 'purple'
    }
  ];

  const recentActivities = [
    {
      id: 1,
      type: 'user_signup',
      message: 'New user registration: sarah.johnson@email.com',
      time: '2 minutes ago',
      icon: 'ri-user-add-line',
      color: 'green'
    },
    {
      id: 2,
      type: 'analysis_completed',
      message: 'AI analysis completed for TechStart Solutions',
      time: '5 minutes ago',
      icon: 'ri-brain-line',
      color: 'blue'
    },
    {
      id: 3,
      type: 'payment_received',
      message: 'Payment received: $299 from Premium subscription',
      time: '12 minutes ago',
      icon: 'ri-money-dollar-circle-line',
      color: 'orange'
    },
    {
      id: 4,
      type: 'system_alert',
      message: 'High CPU usage detected on server-02',
      time: '18 minutes ago',
      icon: 'ri-alert-line',
      color: 'red'
    },
    {
      id: 5,
      type: 'review_submitted',
      message: 'New 5-star review from Michael Chen',
      time: '25 minutes ago',
      icon: 'ri-star-line',
      color: 'yellow'
    }
  ];

  const topPerformingAnalyses = [
    {
      id: 1,
      title: 'E-commerce Optimization',
      completions: 1247,
      avgRating: 4.8,
      revenue: '$12,450'
    },
    {
      id: 2,
      title: 'Supply Chain Analysis',
      completions: 892,
      avgRating: 4.9,
      revenue: '$8,920'
    },
    {
      id: 3,
      title: 'Marketing Automation',
      completions: 756,
      avgRating: 4.7,
      revenue: '$7,560'
    },
    {
      id: 4,
      title: 'Customer Service AI',
      completions: 634,
      avgRating: 4.6,
      revenue: '$6,340'
    }
  ];

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
              
              {/* Profile Dropdown */}
              {isProfileDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <Link 
                    to="/admin/profile"
                    className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3"
                    onClick={() => setIsProfileDropdownOpen(false)}
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
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
              <p className="text-gray-600">Monitor platform performance, user activity, and system metrics</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              {stats.map((stat, index) => (
                <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      stat.color === 'blue' ? 'bg-blue-100' :
                      stat.color === 'green' ? 'bg-green-100' :
                      stat.color === 'orange' ? 'bg-orange-100' :
                      'bg-purple-100'
                    }`}>
                      <i className={`${stat.icon} text-xl ${
                        stat.color === 'blue' ? 'text-blue-600' :
                        stat.color === 'green' ? 'text-green-600' :
                        stat.color === 'orange' ? 'text-orange-600' :
                        'text-purple-600'
                      }`}></i>
                    </div>
                    <span className={`text-sm font-medium px-2 py-1 rounded-full ${
                      stat.changeType === 'positive' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                    }`}>
                      {stat.change}
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-gray-600 mb-1">{stat.title}</h3>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
              ))}
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 md:gap-8">
              {/* Recent Activities */}
              <div className="lg:col-span-2">
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-900">Recent Activities</h3>
                    <Link 
                      to="/admin/notifications"
                      className="text-sm text-red-600 hover:text-red-700 font-medium"
                    >
                      View All
                    </Link>
                  </div>
                  <div className="space-y-4">
                    {recentActivities.map((activity) => (
                      <div key={activity.id} className="flex items-start gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          activity.color === 'green' ? 'bg-green-100' :
                          activity.color === 'blue' ? 'bg-blue-100' :
                          activity.color === 'orange' ? 'bg-orange-100' :
                          activity.color === 'red' ? 'bg-red-100' :
                          'bg-yellow-100'
                        }`}>
                          <i className={`${activity.icon} text-sm ${
                            activity.color === 'green' ? 'text-green-600' :
                            activity.color === 'blue' ? 'text-blue-600' :
                            activity.color === 'orange' ? 'text-orange-600' :
                            activity.color === 'red' ? 'text-red-600' :
                            'text-yellow-600'
                          }`}></i>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-900 mb-1">{activity.message}</p>
                          <p className="text-xs text-gray-500">{activity.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Top Performing Analyses */}
              <div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-6">Top Performing Analyses</h3>
                  <div className="space-y-4">
                    {topPerformingAnalyses.map((analysis) => (
                      <div key={analysis.id} className="p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors">
                        <h4 className="font-medium text-gray-900 mb-2">{analysis.title}</h4>
                        <div className="space-y-1 text-sm text-gray-600">
                          <div className="flex justify-between">
                            <span>Completions:</span>
                            <span className="font-medium">{analysis.completions}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Avg Rating:</span>
                            <div className="flex items-center">
                              <span className="font-medium mr-1">{analysis.avgRating}</span>
                              <i className="ri-star-fill text-yellow-400 text-xs"></i>
                            </div>
                          </div>
                          <div className="flex justify-between">
                            <span>Revenue:</span>
                            <span className="font-medium text-green-600">{analysis.revenue}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">Quick Actions</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                  <button className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-red-200 hover:bg-red-50 transition-colors group">
                    <i className="ri-user-add-line text-2xl text-gray-600 group-hover:text-red-600 mb-2"></i>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-red-600">Add User</span>
                  </button>
                  <button className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-red-200 hover:bg-red-50 transition-colors group">
                    <i className="ri-bar-chart-line text-2xl text-gray-600 group-hover:text-red-600 mb-2"></i>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-red-600">View Analytics</span>
                  </button>
                  <button className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-red-200 hover:bg-red-50 transition-colors group">
                    <i className="ri-settings-line text-2xl text-gray-600 group-hover:text-red-600 mb-2"></i>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-red-600">Settings</span>
                  </button>
                  <button className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-red-200 hover:bg-red-50 transition-colors group">
                    <i className="ri-database-line text-2xl text-gray-600 group-hover:text-red-600 mb-2"></i>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-red-600">Database</span>
                  </button>
                  <button className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-red-200 hover:bg-red-50 transition-colors group">
                    <i className="ri-shield-line text-2xl text-gray-600 group-hover:text-red-600 mb-2"></i>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-red-600">Security</span>
                  </button>
                  <button className="flex flex-col items-center p-4 rounded-lg border border-gray-200 hover:border-red-200 hover:bg-red-50 transition-colors group">
                    <i className="ri-file-text-line text-2xl text-gray-600 group-hover:text-red-600 mb-2"></i>
                    <span className="text-sm font-medium text-gray-700 group-hover:text-red-600">Reports</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}