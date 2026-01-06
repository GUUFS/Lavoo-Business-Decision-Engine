import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import { toast } from 'react-toastify';
import { useAnalyses, type AnalysisStats, type AnalysisItem } from '../../../api/admin-analysis';

const API_BASE_URL = 'http://localhost:8000';

const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token') || localStorage.getItem('token') || localStorage.getItem('authToken');
};

const getAuthHeaders = (): Record<string, string> => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
};

interface UserDetails {
  id: number;
  name: string;
  email: string;
  join_date: string;
  subscription: string;
}

interface AnalysisDetail extends AnalysisItem {
  user_details?: UserDetails;
  // Full analysis data structure
  bottlenecks?: any[];
  business_strategies?: any[];
  ai_tools?: any[];
  roadmap?: any[];
  roi_metrics?: any[];
  [key: string]: any;
}

const AnalysisDetailModal = ({ analysis, onClose, onDownload }: { analysis: AnalysisDetail, onClose: () => void, onDownload: () => void }) => {
  if (!analysis) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto flex flex-col">
        {/* Modal Header */}
        <div className="sticky top-0 bg-white px-6 py-4 border-b border-gray-200 flex justify-between items-center z-10">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{analysis.title}</h2>
            <p className="text-sm text-gray-500">Analysis ID: #{analysis.id} • {analysis.date}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <i className="ri-close-line text-2xl text-gray-500"></i>
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-8">

          {/* User Details Section */}
          {analysis.user_details && (
            <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
              <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <i className="ri-user-star-line"></i> User Profile
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-blue-600 mb-1">Name</p>
                  <p className="font-medium text-gray-900">{analysis.user_details.name}</p>
                </div>
                <div>
                  <p className="text-sm text-blue-600 mb-1">Email</p>
                  <p className="font-medium text-gray-900">{analysis.user_details.email}</p>
                </div>
                <div>
                  <p className="text-sm text-blue-600 mb-1">Subscription</p>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {analysis.user_details.subscription}
                  </span>
                </div>
                <div>
                  <p className="text-sm text-blue-600 mb-1">Member Since</p>
                  <p className="font-medium text-gray-900">{analysis.user_details.join_date}</p>
                </div>
              </div>
            </div>
          )}

          {/* Analysis Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Type</p>
              <p className="font-medium">{analysis.type}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Status</p>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                analysis.status === 'processing' ? 'bg-blue-100 text-blue-800' : 'bg-red-100 text-red-800'
                }`}>
                {analysis.status.toUpperCase()}
              </span>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-100">
              <p className="text-sm text-gray-500 mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500" style={{ width: `${analysis.confidence}%` }}></div>
                </div>
                <span className="font-bold text-purple-600">{analysis.confidence}%</span>
              </div>
            </div>
          </div>

          {/* Full Details Preview (Bottlenecks, etc.) */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Highlights</h3>

            {/* Bottlenecks */}
            {analysis.bottlenecks && analysis.bottlenecks.length > 0 && (
              <div className="mb-6">
                <h4 className="font-medium text-gray-700 mb-2">Identified Bottlenecks</h4>
                <div className="space-y-3">
                  {analysis.bottlenecks.slice(0, 3).map((b: any, idx: number) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                      <div className="flex justify-between items-start">
                        <span className="font-medium text-red-600">{b.title}</span>
                        <span className="text-xs bg-red-50 text-red-600 px-2 py-1 rounded">{b.priority}</span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{b.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {analysis.business_strategies && analysis.business_strategies.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-700 mb-2">Top Recommendations</h4>
                <div className="space-y-3">
                  {analysis.business_strategies.slice(0, 3).map((s: any, idx: number) => (
                    <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3 shadow-sm">
                      <p className="font-medium text-green-700">{s.title}</p>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{s.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="sticky bottom-0 bg-white px-6 py-4 border-t border-gray-200 flex justify-end items-center gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
          >
            Close
          </button>
          <button
            onClick={onDownload}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium flex items-center gap-2 transition-colors shadow-sm"
          >
            <i className="ri-download-line"></i>
            Download Report
          </button>
        </div>
      </div>
    </div>
  );
};


export default function AdminAIAnalysis() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Use TanStack Query hook with automatic caching (2-minute cache)
  const { data, isLoading: loading, error } = useAnalyses({
    page: currentPage,
    limit: itemsPerPage,
    status: filterStatus === 'all' ? undefined : filterStatus,
    type: filterType === 'all' ? undefined : filterType
  });

  // Extract data from response
  const analyses = data?.analyses || [];
  const totalPages = data?.pagination?.totalPages || 1;
  const total = data?.total || 0;
  const stats: AnalysisStats = data?.stats || {
    completed: 0,
    failed: 0,
    avgConfidence: 0
  };

  // Show error toast if query fails
  if (error) {
    toast.error('Failed to load analyses');
  }


  // Reset to page 1 when filters change
  const handleFilterChange = (setter: (value: string) => void, value: string) => {
    setter(value);
    setCurrentPage(1);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-600';
      case 'failed': return 'bg-red-100 text-red-600';
      case 'queued': return 'bg-yellow-100 text-yellow-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600';
    if (confidence >= 80) return 'text-yellow-600';
    if (confidence >= 70) return 'text-orange-600';
    return 'text-red-600';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return 'ri-check-line';
      case 'failed': return 'ri-close-line';
      case 'queued': return 'ri-time-line';
      default: return 'ri-question-line';
    }
  };

  // Use stats from API
  const analysisStats = {
    total: total,
    completed: stats.completed,
    failed: stats.failed,
    avgConfidence: Math.round(stats.avgConfidence || 0)
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
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <button
                className="md:hidden p-2 text-gray-600 hover:text-gray-900 mr-3"
                onClick={() => setIsMobileMenuOpen(true)}
              >
                <i className="ri-menu-line text-xl"></i>
              </button>

            </div>
            <div className="relative">
              <button
                onClick={() => setShowAdminDropdown(!showAdminDropdown)}
                className="flex items-center gap-2 px-3 py-2 text-gray-700 hover:text-gray-900 transition-colors"
              >
                <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-orange-600"></i>
                </div>
                <span className="font-medium">John Admin</span>
                <i className="ri-arrow-down-s-line"></i>
              </button>

              {showAdminDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowAdminDropdown(false)}
                  ></div>
                  <div className="absolute top-full right-0 mt-2 w-48 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                    <Link
                      to="/admin/profile"
                      className="w-full flex items-center px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors"
                      onClick={() => setShowAdminDropdown(false)}
                    >
                      <i className="ri-user-line mr-3"></i>
                      Profile
                    </Link>
                    <button className="w-full flex items-center px-4 py-2 text-gray-700 hover:bg-gray-50 transition-colors">
                      <i className="ri-logout-box-line mr-3"></i>
                      Logout
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">AI Analysis Monitor</h1>
              <p className="text-gray-600">Monitor AI analysis performance, track completion rates, and manage analysis queue</p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-robot-line text-xl text-blue-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Total Analyses</h3>
                <p className="text-2xl font-bold text-gray-900">{analysisStats.total}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <i className="ri-check-line text-xl text-green-600"></i>
                  </div>
                  <span className="text-sm font-medium px-2 py-1 rounded-full bg-green-100 text-green-600">
                    {((analysisStats.completed / analysisStats.total) * 100).toFixed(1)}%
                  </span>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Completed</h3>
                <p className="text-2xl font-bold text-gray-900">{analysisStats.completed}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                    <i className="ri-close-line text-xl text-red-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Failed</h3>
                <p className="text-2xl font-bold text-gray-900">{analysisStats.failed}</p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <i className="ri-star-line text-xl text-purple-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Avg Confidence</h3>
                <p className="text-2xl font-bold text-gray-900">{analysisStats.avgConfidence}%</p>
              </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-6">
              <div className="flex flex-col sm:flex-row gap-4">
                <select
                  value={filterStatus}
                  onChange={(e) => handleFilterChange(setFilterStatus, e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                >
                  <option value="all">All Status</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="queued">Queued</option>
                </select>
                <select
                  value={filterType}
                  onChange={(e) => handleFilterChange(setFilterType, e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                >
                  <option value="all">All Types</option>
                  <option value="Sales Analysis">Sales Analysis</option>
                  <option value="Customer Analysis">Customer Analysis</option>
                  <option value="Market Analysis">Market Analysis</option>
                  <option value="Financial Analysis">Financial Analysis</option>
                  <option value="Operations Analysis">Operations Analysis</option>
                  <option value="Product Analysis">Product Analysis</option>
                </select>
              </div>
            </div>

            {/* Analyses List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Analysis</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">User</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Type</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Confidence</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Duration</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Results</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {loading ? (
                      // Loading skeleton
                      [...Array(itemsPerPage)].map((_, i) => (
                        <tr key={i} className="animate-pulse">
                          <td className="py-4 px-4">
                            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-4 bg-gray-200 rounded w-24"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-4 bg-gray-200 rounded w-32"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-6 bg-gray-200 rounded-full w-20"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-4 bg-gray-200 rounded w-12"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-4 bg-gray-200 rounded w-16"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-4 bg-gray-200 rounded w-20"></div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="h-8 bg-gray-200 rounded w-20"></div>
                          </td>
                        </tr>
                      ))
                    ) : analyses.length === 0 ? (
                      // Empty state
                      <tr>
                        <td colSpan={8} className="py-12 text-center">
                          <div className="flex flex-col items-center gap-2">
                            <i className="ri-inbox-line text-4xl text-gray-400"></i>
                            <p className="text-gray-500">No analyses found</p>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      // Data rows
                      analyses.map((analysis) => (
                        <tr key={analysis.id} className="hover:bg-gray-50">
                          <td className="py-4 px-4">
                            <div>
                              <p className="font-medium text-gray-900">{analysis.title}</p>
                              <p className="text-sm text-gray-500">{new Date(analysis.date).toLocaleString()}</p>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-gray-900">{analysis.userName}</span>
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-sm text-gray-600">{analysis.type}</span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <i className={`${getStatusIcon(analysis.status)} ${analysis.status === 'processing' ? 'animate-spin' : ''
                                }`}></i>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(analysis.status)}`}>
                                {analysis.status.charAt(0).toUpperCase() + analysis.status.slice(1)}
                              </span>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            {analysis.confidence > 0 ? (
                              <span className={`font-medium ${getConfidenceColor(analysis.confidence)}`}>
                                {analysis.confidence}%
                              </span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                          <td className="py-4 px-4">
                            <span className="text-sm text-gray-600">{analysis.duration}</span>
                          </td>
                          <td className="py-4 px-4">
                            <div className="text-sm text-gray-600">
                              <div>{analysis.insights} insights</div>
                              <div>{analysis.recommendations} recommendations</div>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                                <i className="ri-eye-line"></i>
                              </button>
                              <button className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors">
                                <i className="ri-download-line"></i>
                              </button>
                              <button className="p-2 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors">
                                <i className="ri-more-line"></i>
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                      Page {currentPage} of {totalPages}
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
                          className={`px-3 py-1 rounded-lg text-sm font-medium whitespace-nowrap ${currentPage === page
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
