import { useState } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import { Link } from 'react-router-dom';

export default function AdminAIAnalysis() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterType, setFilterType] = useState('all');
  const [showAdminDropdown, setShowAdminDropdown] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  const analyses = [
    {
      id: 1,
      title: 'Q4 Sales Performance Analysis',
      user: 'Sarah Johnson',
      type: 'Sales Analysis',
      status: 'completed',
      confidence: 94,
      duration: '2m 34s',
      date: '2024-02-26 14:32',
      insights: 8,
      recommendations: 5
    },
    {
      id: 2,
      title: 'Customer Retention Strategy',
      user: 'Michael Chen',
      type: 'Customer Analysis',
      status: 'processing',
      confidence: 0,
      duration: 'Running...',
      date: '2024-02-26 14:45',
      insights: 0,
      recommendations: 0
    },
    {
      id: 3,
      title: 'Market Trend Prediction',
      user: 'Emily Rodriguez',
      type: 'Market Analysis',
      status: 'completed',
      confidence: 87,
      duration: '3m 12s',
      date: '2024-02-26 13:28',
      insights: 12,
      recommendations: 7
    },
    {
      id: 4,
      title: 'Operational Efficiency Review',
      user: 'David Kim',
      type: 'Operations Analysis',
      status: 'failed',
      confidence: 0,
      duration: '1m 45s',
      date: '2024-02-26 12:15',
      insights: 0,
      recommendations: 0
    },
    {
      id: 5,
      title: 'Financial Risk Assessment',
      user: 'Lisa Thompson',
      type: 'Financial Analysis',
      status: 'completed',
      confidence: 91,
      duration: '4m 18s',
      date: '2024-02-26 11:42',
      insights: 15,
      recommendations: 9
    },
    {
      id: 6,
      title: 'Product Performance Metrics',
      user: 'James Wilson',
      type: 'Product Analysis',
      status: 'completed',
      confidence: 89,
      duration: '2m 56s',
      date: '2024-02-26 10:33',
      insights: 10,
      recommendations: 6
    },
    {
      id: 7,
      title: 'Competitive Analysis Report',
      user: 'Anna Martinez',
      type: 'Competitive Analysis',
      status: 'processing',
      confidence: 0,
      duration: 'Running...',
      date: '2024-02-26 15:12',
      insights: 0,
      recommendations: 0
    },
    {
      id: 8,
      title: 'Supply Chain Optimization',
      user: 'Robert Taylor',
      type: 'Supply Chain Analysis',
      status: 'completed',
      confidence: 96,
      duration: '5m 23s',
      date: '2024-02-26 09:45',
      insights: 18,
      recommendations: 12
    }
  ];

  const filteredAnalyses = analyses.filter(analysis => {
    const matchesStatus = filterStatus === 'all' || analysis.status === filterStatus;
    const matchesType = filterType === 'all' || analysis.type === filterType;
    return matchesStatus && matchesType;
  });

  // Pagination calculations
  const totalPages = Math.ceil(filteredAnalyses.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentAnalyses = filteredAnalyses.slice(startIndex, endIndex);

  // Reset to page 1 when filters change
  const handleFilterChange = (setter: (value: string) => void, value: string) => {
    setter(value);
    setCurrentPage(1);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-600';
      case 'processing': return 'bg-blue-100 text-blue-600';
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
      case 'processing': return 'ri-loader-line';
      case 'failed': return 'ri-close-line';
      case 'queued': return 'ri-time-line';
      default: return 'ri-question-line';
    }
  };

  const analysisStats = {
    total: analyses.length,
    completed: analyses.filter(a => a.status === 'completed').length,
    processing: analyses.filter(a => a.status === 'processing').length,
    failed: analyses.filter(a => a.status === 'failed').length,
    avgConfidence: Math.round(analyses.filter(a => a.confidence > 0).reduce((sum, a) => sum + a.confidence, 0) / analyses.filter(a => a.confidence > 0).length)
  };

  const analysisTypes = [
    { name: 'Sales Analysis', count: 1, color: 'bg-blue-100 text-blue-600' },
    { name: 'Customer Analysis', count: 1, color: 'bg-green-100 text-green-600' },
    { name: 'Market Analysis', count: 1, color: 'bg-purple-100 text-purple-600' },
    { name: 'Financial Analysis', count: 1, color: 'bg-orange-100 text-orange-600' },
    { name: 'Operations Analysis', count: 1, color: 'bg-red-100 text-red-600' },
    { name: 'Product Analysis', count: 1, color: 'bg-yellow-100 text-yellow-600' }
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
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 md:gap-6 mb-8">
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
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <i className="ri-loader-line text-xl text-blue-600"></i>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-600 mb-1">Processing</h3>
                <p className="text-2xl font-bold text-gray-900">{analysisStats.processing}</p>
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

            {/* Analysis Types */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Types</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {analysisTypes.map((type) => (
                  <div key={type.name} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                    <span className="font-medium text-gray-900">{type.name}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${type.color}`}>
                      {type.count}
                    </span>
                  </div>
                ))}
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
                  <option value="processing">Processing</option>
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
                    {currentAnalyses.map((analysis) => (
                      <tr key={analysis.id} className="hover:bg-gray-50">
                        <td className="py-4 px-4">
                          <div>
                            <p className="font-medium text-gray-900">{analysis.title}</p>
                            <p className="text-sm text-gray-500">{analysis.date}</p>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-gray-900">{analysis.user}</span>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-sm text-gray-600">{analysis.type}</span>
                        </td>
                        <td className="py-4 px-4">
                          <div className="flex items-center gap-2">
                            <i className={`${getStatusIcon(analysis.status)} ${
                              analysis.status === 'processing' ? 'animate-spin' : ''
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
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="px-4 py-4 border-t border-gray-200">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-600">
                      Showing {startIndex + 1} to {Math.min(endIndex, filteredAnalyses.length)} of {filteredAnalyses.length} analyses
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