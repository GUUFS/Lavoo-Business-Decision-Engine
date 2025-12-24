import { useState } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import { useAnalytics, useActivityStream } from '../../../api/admin-analytics';

export default function AdminAnalytics() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d' | '90d'>('7d');

  // Use TanStack Query hooks with automatic caching and refetching
  const { data: metrics, isLoading: loading, isError: metricsError } = useAnalytics(timeRange);
  const { data: activityData, isError: activityError } = useActivityStream(10);

  // Extract activities from response
  const activities = activityData?.activities || [];

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
                    onChange={(e) => setTimeRange(e.target.value as '24h' | '7d' | '30d' | '90d')}
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
              {loading ? (
                // Loading skeletons
                [...Array(4)].map((_, i) => (
                  <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 animate-pulse">
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 bg-gray-200 rounded-lg"></div>
                      <div className="h-6 w-16 bg-gray-200 rounded-full"></div>
                    </div>
                    <div className="h-4 bg-gray-200 rounded w-24 mb-2"></div>
                    <div className="h-8 bg-gray-200 rounded w-20"></div>
                  </div>
                ))
              ) : metrics && (
                <>
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <i className="ri-brain-line text-xl text-blue-600"></i>
                      </div>
                    </div>
                    <h3 className="text-sm font-medium text-gray-600 mb-1">Total Analyses</h3>
                    <p className="text-2xl font-bold text-gray-900">{metrics.metrics.totalAnalyses.toLocaleString()}</p>
                  </div>

                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                        <i className="ri-check-line text-xl text-green-600"></i>
                      </div>
                    </div>
                    <h3 className="text-sm font-medium text-gray-600 mb-1">Completion Rate</h3>
                    <p className="text-2xl font-bold text-gray-900">{metrics.metrics.completionRate.toFixed(1)}%</p>
                  </div>

                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                        <i className="ri-time-line text-xl text-orange-600"></i>
                      </div>
                    </div>
                    <h3 className="text-sm font-medium text-gray-600 mb-1">Avg Processing Time</h3>
                    <p className="text-2xl font-bold text-gray-900">{metrics.metrics.avgProcessingTime.toFixed(1)}s</p>
                  </div>

                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                        <i className="ri-star-line text-xl text-purple-600"></i>
                      </div>
                    </div>
                    <h3 className="text-sm font-medium text-gray-600 mb-1">User Satisfaction</h3>
                    <p className="text-2xl font-bold text-gray-900">{metrics.metrics.userSatisfaction.toFixed(1)}/5</p>
                  </div>
                </>
              )}
            </div>

            {/* Real-time Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Usage Trends Chart */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage Trends</h3>
                {loading ? (
                  <div className="animate-pulse space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <div className="h-8 bg-gray-200 rounded flex-1"></div>
                        <div className="h-6 w-12 bg-gray-200 rounded"></div>
                      </div>
                    ))}
                  </div>
                ) : metrics && metrics.chartData ? (
                  <div className="space-y-3">
                    {metrics.chartData.map((day: any, index: number) => {
                      const maxAnalyses = Math.max(...metrics.chartData.map((d: any) => d.analyses));
                      const barWidth = maxAnalyses > 0 ? (day.analyses / maxAnalyses) * 100 : 0;
                      const dayName = new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

                      return (
                        <div key={index} className="flex items-center gap-3">
                          <span className="text-xs text-gray-600 w-20 text-right">{dayName}</span>
                          <div className="flex-1 bg-gray-100 rounded-lg h-8 relative overflow-hidden">
                            <div
                              className="bg-gradient-to-r from-blue-500 to-blue-600 h-full rounded-lg transition-all duration-500 flex items-center justify-end pr-2"
                              style={{ width: `${barWidth}%` }}
                            >
                              {day.analyses > 0 && (
                                <span className="text-xs font-medium text-white">{day.analyses}</span>
                              )}
                            </div>
                          </div>
                          <span className="text-xs text-gray-500 w-16">{day.users} users</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No data available</p>
                )}
              </div>

              {/* Top Analysis Types */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Analysis Types</h3>
                {loading ? (
                  <div className="animate-pulse space-y-3">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <div className="w-8 h-8 bg-gray-200 rounded"></div>
                          <div className="h-4 bg-gray-200 rounded w-32"></div>
                        </div>
                        <div className="h-4 bg-gray-200 rounded w-16"></div>
                      </div>
                    ))}
                  </div>
                ) : metrics && metrics.topAnalysisTypes && metrics.topAnalysisTypes.length > 0 ? (
                  <div className="space-y-3">
                    {metrics.topAnalysisTypes.map((type: any, index: number) => {
                      const colors = [
                        'bg-blue-100 text-blue-600',
                        'bg-green-100 text-green-600',
                        'bg-purple-100 text-purple-600',
                        'bg-orange-100 text-orange-600',
                        'bg-pink-100 text-pink-600',
                        'bg-indigo-100 text-indigo-600',
                        'bg-red-100 text-red-600',
                        'bg-yellow-100 text-yellow-600',
                      ];
                      const colorClass = colors[index % colors.length];

                      return (
                        <div key={index} className="flex items-center justify-between">
                          <div className="flex items-center gap-3 flex-1">
                            <div className={`w-8 h-8 ${colorClass} rounded-lg flex items-center justify-center`}>
                              <i className="ri-bar-chart-line text-sm"></i>
                            </div>
                            <div className="flex-1">
                              <p className="text-sm font-medium text-gray-900">{type.type}</p>
                              <div className="w-full bg-gray-100 rounded-full h-1.5 mt-1">
                                <div
                                  className={`h-1.5 rounded-full ${colorClass.split(' ')[0].replace('100', '500')}`}
                                  style={{ width: `${type.percentage}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                          <div className="text-right ml-4">
                            <p className="text-sm font-semibold text-gray-900">{type.count}</p>
                            <p className="text-xs text-gray-500">{type.percentage}%</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No analysis types data</p>
                )}
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Metrics</h3>
              {loading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="p-4 border border-gray-200 rounded-lg">
                      <div className="h-4 bg-gray-200 rounded w-32 mb-2"></div>
                      <div className="h-8 bg-gray-200 rounded w-20 mb-1"></div>
                      <div className="h-4 bg-gray-200 rounded w-16"></div>
                    </div>
                  ))}
                </div>
              ) : metrics && metrics.performanceMetrics ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {metrics.performanceMetrics.map((metric: any, index: number) => (
                    <div key={index} className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
                      <p className="text-sm text-gray-600 mb-1">{metric.metric}</p>
                      <p className="text-2xl font-bold text-gray-900 mb-1">{metric.value}</p>
                      <div className="flex items-center">
                        <i className={`text-sm mr-1 ${
                          metric.trend === 'up' ? 'ri-arrow-up-line text-green-600' :
                          metric.trend === 'down' ? 'ri-arrow-down-line text-red-600' :
                          'ri-subtract-line text-gray-400'
                        }`}></i>
                        <span className={`text-xs font-medium ${
                          metric.trend === 'up' ? 'text-green-600' :
                          metric.trend === 'down' ? 'text-red-600' :
                          'text-gray-500'
                        }`}>
                          {metric.change}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No performance metrics available</p>
              )}
            </div>

            {/* Real-time Activity */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Real-time Activity</h3>
                <div className="flex items-center text-green-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                  <span className="text-sm font-medium">Live (14s refresh)</span>
                </div>
              </div>
              <div className="space-y-3">
                {activities.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <i className="ri-time-line text-3xl mb-2"></i>
                    <p>No recent activity</p>
                  </div>
                ) : (
                  activities.map((activity, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center mr-3 ${
                          activity.type === 'analysis_started' ? 'bg-blue-100' :
                          activity.type === 'analysis_completed' ? 'bg-green-100' :
                          activity.type === 'analysis_failed' ? 'bg-red-100' :
                          'bg-gray-100'
                        }`}>
                          <i className={`text-sm ${
                            activity.type === 'analysis_started' ? 'ri-brain-line text-blue-600' :
                            activity.type === 'analysis_completed' ? 'ri-check-line text-green-600' :
                            activity.type === 'analysis_failed' ? 'ri-error-warning-line text-red-600' :
                            'ri-information-line text-gray-600'
                          }`}></i>
                        </div>
                        <span className="text-sm text-gray-900">{activity.message}</span>
                      </div>
                      <span className="text-xs text-gray-500">{activity.timeAgo}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
