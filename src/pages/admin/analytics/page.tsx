import { useState } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminAnalytics() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [timeRange, setTimeRange] = useState('7d');

  const analyticsData = {
    totalAnalyses: 15847,
    completionRate: 94.2,
    avgProcessingTime: 2.3,
    userSatisfaction: 4.8
  };

  const chartData = [
    { date: '2024-02-20', analyses: 245, users: 189 },
    { date: '2024-02-21', analyses: 312, users: 234 },
    { date: '2024-02-22', analyses: 289, users: 201 },
    { date: '2024-02-23', analyses: 356, users: 267 },
    { date: '2024-02-24', analyses: 423, users: 298 },
    { date: '2024-02-25', analyses: 378, users: 245 },
    { date: '2024-02-26', analyses: 445, users: 312 }
  ];

  const topAnalysisTypes = [
    { type: 'E-commerce Optimization', count: 3247, percentage: 20.5 },
    { type: 'Supply Chain Analysis', count: 2891, percentage: 18.2 },
    { type: 'Marketing Automation', count: 2456, percentage: 15.5 },
    { type: 'Customer Service AI', count: 2134, percentage: 13.5 },
    { type: 'Financial Planning', count: 1876, percentage: 11.8 },
    { type: 'HR Optimization', count: 1543, percentage: 9.7 },
    { type: 'Operations Management', count: 1234, percentage: 7.8 },
    { type: 'Other', count: 466, percentage: 2.9 }
  ];

  const performanceMetrics = [
    { metric: 'Average Response Time', value: '2.3s', change: '-12%', trend: 'down' },
    { metric: 'Success Rate', value: '99.7%', change: '+0.3%', trend: 'up' },
    { metric: 'User Engagement', value: '87.4%', change: '+5.2%', trend: 'up' },
    { metric: 'Error Rate', value: '0.3%', change: '-45%', trend: 'down' }
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
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Analytics Dashboard</h1>
                  <p className="text-gray-600">Monitor platform performance and user behavior</p>
                </div>
                <div className="mt-4 sm:mt-0">
                  <select
                    value={timeRange}
                    onChange={(e) => setTimeRange(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                  >
                    <option value="24h">Last 24 Hours</option>
                    <option value="7d">Last 7 Days</option>
                    <option value="30d">Last 30 Days</option>
                    <option value="90d">Last 90 Days</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-brain-line text-xl text-blue-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">+18.2%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Total Analyses</h3>
                <p className="text-2xl font-bold text-gray-900">{analyticsData.totalAnalyses.toLocaleString()}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-check-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">+2.1%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Completion Rate</h3>
                <p className="text-2xl font-bold text-gray-900">{analyticsData.completionRate}%</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                    <i className="ri-time-line text-xl text-orange-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">-12%</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Avg Processing Time</h3>
                <p className="text-2xl font-bold text-gray-900">{analyticsData.avgProcessingTime}s</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-star-line text-xl text-purple-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">+0.3</span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">User Satisfaction</h3>
                <p className="text-2xl font-bold text-gray-900">{analyticsData.userSatisfaction}/5</p>
              </div>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8 mb-8">
              {/* Usage Trends */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">Usage Trends</h3>
                <div className="space-y-4">
                  {chartData.map((data, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="text-sm text-gray-600">{new Date(data.date).toLocaleDateString()}</div>
                      <div className="flex items-center gap-4">
                        <div className="flex items-center">
                          <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                          <span className="text-sm text-gray-600">Analyses: {data.analyses}</span>
                        </div>
                        <div className="flex items-center">
                          <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                          <span className="text-sm text-gray-600">Users: {data.users}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top Analysis Types */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-6">Top Analysis Types</h3>
                <div className="space-y-4">
                  {topAnalysisTypes.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-900">{item.type}</span>
                          <span className="text-sm text-gray-600">{item.count}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-red-500 h-2 rounded-full" 
                            style={{ width: `${item.percentage}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-6">Performance Metrics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                {performanceMetrics.map((metric, index) => (
                  <div key={index} className="text-center">
                    <div className="text-2xl font-bold text-gray-900 mb-1">{metric.value}</div>
                    <div className="text-sm text-gray-600 mb-2">{metric.metric}</div>
                    <div className={`text-sm font-medium ${
                      metric.trend === 'up' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      <i className={`ri-arrow-${metric.trend === 'up' ? 'up' : 'down'}-line mr-1`}></i>
                      {metric.change}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Real-time Activity */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Real-time Activity</h3>
                <div className="flex items-center text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                  <span className="text-sm font-medium">Live</span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-brain-line text-blue-600 text-sm"></i>
                    </div>
                    <span className="text-sm text-gray-900">New analysis started: E-commerce Optimization</span>
                  </div>
                  <span className="text-xs text-gray-500">Just now</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-check-line text-green-600 text-sm"></i>
                    </div>
                    <span className="text-sm text-gray-900">Analysis completed: Supply Chain Analysis</span>
                  </div>
                  <span className="text-xs text-gray-500">2 min ago</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-user-add-line text-orange-600 text-sm"></i>
                    </div>
                    <span className="text-sm text-gray-900">New user registered: alex.johnson@tech.startup</span>
                  </div>
                  <span className="text-xs text-gray-500">5 min ago</span>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}