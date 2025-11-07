
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardSidebar from '../../components/feature/DashboardSidebar';
import Footer from '../../components/feature/Footer';

export default function AnalysisHistoryPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();

  const itemsPerPage = 10;

  // Mock analysis history data - sorted by most recent first
  const analysisHistory = [
    {
      id: 1,
      title: 'Business Analysis - 11/15/2025',
      date: '11/15/2025',
      description: 'E-commerce platform seeking to improve conversion rates and customer retention',
      bottlenecks: 6,
      solutions: 7,
      confidence: '94%',
      status: 'completed',
      industry: 'E-commerce'
    },
    {
      id: 2,
      title: 'Business Analysis - 11/12/2025',
      date: '11/12/2025',
      description: 'Healthcare clinic looking to streamline patient management and reduce wait times',
      bottlenecks: 3,
      solutions: 4,
      confidence: '87%',
      status: 'completed',
      industry: 'Healthcare'
    },
    {
      id: 3,
      title: 'Business Analysis - 11/10/2025',
      date: '11/10/2025',
      description: 'Restaurant chain wanting to optimize delivery and reduce operational costs',
      bottlenecks: 4,
      solutions: 4,
      confidence: '88%',
      status: 'completed',
      industry: 'Food & Beverage'
    },
    {
      id: 4,
      title: 'Business Analysis - 11/8/2025',
      date: '11/8/2025',
      description: 'Tech startup looking to scale operations and improve customer acquisition',
      bottlenecks: 7,
      solutions: 6,
      confidence: '92%',
      status: 'completed',
      industry: 'Technology'
    },
    {
      id: 5,
      title: 'Business Analysis - 11/5/2025',
      date: '11/5/2025',
      description: 'I sell soaps and would want to increase visibility and sales for my business',
      bottlenecks: 5,
      solutions: 3,
      confidence: '85%',
      status: 'completed',
      industry: 'Retail'
    },
    {
      id: 6,
      title: 'Business Analysis - 11/3/2025',
      date: '11/3/2025',
      description: 'I am a content creator and I want to make my audience laugh',
      bottlenecks: 5,
      solutions: 5,
      confidence: '90%',
      status: 'completed',
      industry: 'Entertainment'
    },
    {
      id: 7,
      title: 'Business Analysis - 11/1/2025',
      date: '11/1/2025',
      description: 'Digital marketing agency looking to automate client reporting and improve efficiency',
      bottlenecks: 4,
      solutions: 5,
      confidence: '89%',
      status: 'completed',
      industry: 'Marketing'
    },
    {
      id: 8,
      title: 'Business Analysis - 10/28/2025',
      date: '10/28/2025',
      description: 'Manufacturing company seeking to reduce production costs and improve quality control',
      bottlenecks: 6,
      solutions: 4,
      confidence: '91%',
      status: 'completed',
      industry: 'Manufacturing'
    },
    {
      id: 9,
      title: 'Business Analysis - 10/25/2025',
      date: '10/25/2025',
      description: 'Real estate agency wanting to improve lead generation and client management',
      bottlenecks: 5,
      solutions: 6,
      confidence: '86%',
      status: 'completed',
      industry: 'Real Estate'
    },
    {
      id: 10,
      title: 'Business Analysis - 10/22/2025',
      date: '10/22/2025',
      description: 'Educational platform looking to increase student engagement and retention rates',
      bottlenecks: 4,
      solutions: 5,
      confidence: '88%',
      status: 'completed',
      industry: 'Education'
    },
    {
      id: 11,
      title: 'Business Analysis - 10/20/2025',
      date: '10/20/2025',
      description: 'Fitness center chain wanting to improve member retention and class booking system',
      bottlenecks: 3,
      solutions: 4,
      confidence: '84%',
      status: 'completed',
      industry: 'Fitness'
    },
    {
      id: 12,
      title: 'Business Analysis - 10/18/2025',
      date: '10/18/2025',
      description: 'Financial services firm seeking to streamline client onboarding and compliance',
      bottlenecks: 7,
      solutions: 6,
      confidence: '93%',
      status: 'completed',
      industry: 'Finance'
    },
    {
      id: 13,
      title: 'Business Analysis - 10/15/2025',
      date: '10/15/2025',
      description: 'Travel agency looking to improve booking experience and customer support',
      bottlenecks: 5,
      solutions: 5,
      confidence: '87%',
      status: 'completed',
      industry: 'Travel'
    },
    {
      id: 14,
      title: 'Business Analysis - 10/12/2025',
      date: '10/12/2025',
      description: 'Automotive dealership wanting to enhance online presence and lead conversion',
      bottlenecks: 4,
      solutions: 4,
      confidence: '85%',
      status: 'completed',
      industry: 'Automotive'
    },
    {
      id: 15,
      title: 'Business Analysis - 10/10/2025',
      date: '10/10/2025',
      description: 'Legal firm seeking to improve client communication and case management efficiency',
      bottlenecks: 6,
      solutions: 5,
      confidence: '90%',
      status: 'completed',
      industry: 'Legal'
    }
  ];

  const filteredAnalyses = analysisHistory.filter(analysis => {
    const matchesSearch = analysis.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         analysis.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         analysis.industry.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || analysis.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  // Pagination calculations
  const totalPages = Math.ceil(filteredAnalyses.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentAnalyses = filteredAnalyses.slice(startIndex, endIndex);

  const getConfidenceColor = (confidence: string) => {
    const value = parseInt(confidence);
    if (value >= 90) return 'bg-green-100 text-green-700';
    if (value >= 85) return 'bg-blue-100 text-blue-700';
    return 'bg-yellow-100 text-yellow-700';
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    const pages = [];
    const maxVisiblePages = 5;
    
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    // Previous button
    pages.push(
      <button
        key="prev"
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-l-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <i className="ri-arrow-left-s-line"></i>
      </button>
    );

    // First page
    if (startPage > 1) {
      pages.push(
        <button
          key={1}
          onClick={() => handlePageChange(1)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
        >
          1
        </button>
      );
      if (startPage > 2) {
        pages.push(
          <span key="ellipsis1" className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300">
            ...
          </span>
        );
      }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => handlePageChange(i)}
          className={`px-3 py-2 text-sm font-medium border ${
            currentPage === i
              ? 'text-orange-600 bg-orange-50 border-orange-500'
              : 'text-gray-700 bg-white border-gray-300 hover:bg-gray-50'
          }`}
        >
          {i}
        </button>
      );
    }

    // Last page
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push(
          <span key="ellipsis2" className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300">
            ...
          </span>
        );
      }
      pages.push(
        <button
          key={totalPages}
          onClick={() => handlePageChange(totalPages)}
          className="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
        >
          {totalPages}
        </button>
      );
    }

    // Next button
    pages.push(
      <button
        key="next"
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-r-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <i className="ri-arrow-right-s-line"></i>
      </button>
    );

    return (
      <div className="flex items-center justify-between mt-6 px-4 sm:px-6">
        <div className="flex-1 flex justify-between sm:hidden">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="ml-3 relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
        <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-700">
              Showing <span className="font-medium">{startIndex + 1}</span> to{' '}
              <span className="font-medium">{Math.min(endIndex, filteredAnalyses.length)}</span> of{' '}
              <span className="font-medium">{filteredAnalyses.length}</span> results
            </p>
          </div>
          <div>
            <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
              {pages}
            </nav>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />
      
      {/* Main Content */}
      <div className="flex-1 md:ml-64 flex flex-col">
        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 lg:mb-8">
              <div className="flex items-center mb-4">
                <button
                  onClick={() => navigate('/analyze')}
                  className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors whitespace-nowrap mr-4"
                >
                  <i className="ri-arrow-left-line mr-2"></i>
                  Back to Analysis
                </button>
              </div>
              <h1 className="text-2xl md:text-3xl lg:text-4xl font-bold text-gray-900 mb-2 md:mb-4">
                Analysis History
              </h1>
              <p className="text-base md:text-lg text-gray-600">
                View and manage all your previous business analysis reports
              </p>
            </div>

            {/* Search and Filter */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:p-6 mb-6 lg:mb-8">
              <div className="flex flex-col lg:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input
                      type="text"
                      placeholder="Search analyses..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm md:text-base"
                    />
                  </div>
                </div>
                <div className="lg:w-48">
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full px-4 py-3 pr-8 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm md:text-base"
                  >
                    <option value="all">All Status</option>
                    <option value="completed">Completed</option>
                    <option value="processing">Processing</option>
                    <option value="draft">Draft</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-6 lg:mb-8">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center">
                  <div className="w-10 h-10 md:w-12 md:h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-3 md:mr-4">
                    <i className="ri-file-list-3-line text-blue-600 text-lg md:text-xl"></i>
                  </div>
                  <div>
                    <p className="text-xs md:text-sm font-medium text-gray-600">Total Analyses</p>
                    <p className="text-lg md:text-2xl font-bold text-gray-900">{analysisHistory.length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center">
                  <div className="w-10 h-10 md:w-12 md:h-12 bg-green-100 rounded-lg flex items-center justify-center mr-3 md:mr-4">
                    <i className="ri-check-line text-green-600 text-lg md:text-xl"></i>
                  </div>
                  <div>
                    <p className="text-xs md:text-sm font-medium text-gray-600">Completed</p>
                    <p className="text-lg md:text-2xl font-bold text-gray-900">{analysisHistory.filter(a => a.status === 'completed').length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center">
                  <div className="w-10 h-10 md:w-12 md:h-12 bg-orange-100 rounded-lg flex items-center justify-center mr-3 md:mr-4">
                    <i className="ri-lightbulb-line text-orange-600 text-lg md:text-xl"></i>
                  </div>
                  <div>
                    <p className="text-xs md:text-sm font-medium text-gray-600">Avg. Solutions</p>
                    <p className="text-lg md:text-2xl font-bold text-gray-900">
                      {Math.round(analysisHistory.reduce((acc, a) => acc + a.solutions, 0) / analysisHistory.length)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:p-6">
                <div className="flex items-center">
                  <div className="w-10 h-10 md:w-12 md:h-12 bg-purple-100 rounded-lg flex items-center justify-center mr-3 md:mr-4">
                    <i className="ri-line-chart-line text-purple-600 text-lg md:text-xl"></i>
                  </div>
                  <div>
                    <p className="text-xs md:text-sm font-medium text-gray-600">Avg. Confidence</p>
                    <p className="text-lg md:text-2xl font-bold text-gray-900">
                      {Math.round(analysisHistory.reduce((acc, a) => acc + parseInt(a.confidence), 0) / analysisHistory.length)}%
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Analysis List */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <h2 className="text-lg md:text-xl font-semibold text-gray-900">
                  Analysis Reports ({filteredAnalyses.length})
                </h2>
              </div>
              
              <div className="divide-y divide-gray-200">
                {currentAnalyses.map((analysis) => (
                  <div key={analysis.id} className="p-4 md:p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between">
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-2 md:gap-3 mb-2">
                          <h3 className="font-semibold text-gray-900 text-sm md:text-base">{analysis.title}</h3>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${getConfidenceColor(analysis.confidence)}`}>
                            {analysis.confidence} confidence
                          </span>
                          <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
                            {analysis.industry}
                          </span>
                        </div>
                        <p className="text-gray-600 text-sm mb-3 line-clamp-2">{analysis.description}</p>
                        <div className="flex flex-wrap items-center gap-4 md:gap-6 text-xs md:text-sm text-gray-500">
                          <span className="flex items-center">
                            <i className="ri-calendar-line mr-1"></i>
                            {analysis.date}
                          </span>
                          <span className="flex items-center">
                            <i className="ri-alert-line mr-1"></i>
                            {analysis.bottlenecks} bottlenecks
                          </span>
                          <span className="flex items-center">
                            <i className="ri-lightbulb-line mr-1"></i>
                            {analysis.solutions} solutions
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-4 lg:mt-0 lg:ml-4">
                        <button
                          onClick={() => navigate('/results', { state: { businessDetails: analysis.description } })}
                          className="flex-1 lg:flex-none px-3 md:px-4 py-2 text-xs md:text-sm font-medium text-orange-600 hover:text-orange-700 border border-orange-200 rounded-md hover:bg-orange-50 transition-colors whitespace-nowrap"
                        >
                          <i className="ri-eye-line mr-1"></i>
                          View Report
                        </button>
                        <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                          <i className="ri-download-line text-sm md:text-base"></i>
                        </button>
                        <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                          <i className="ri-more-2-line text-sm md:text-base"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {filteredAnalyses.length === 0 && (
                <div className="p-8 md:p-12 text-center">
                  <div className="w-12 h-12 md:w-16 md:h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i className="ri-file-list-3-line text-gray-400 text-xl md:text-2xl"></i>
                  </div>
                  <h3 className="text-base md:text-lg font-medium text-gray-900 mb-2">No analyses found</h3>
                  <p className="text-gray-600 mb-6 text-sm md:text-base">Try adjusting your search or filter criteria</p>
                  <button
                    onClick={() => navigate('/analyze')}
                    className="px-4 md:px-6 py-2 md:py-3 bg-orange-500 text-white rounded-lg font-medium hover:bg-orange-600 transition-colors whitespace-nowrap text-sm md:text-base"
                  >
                    <i className="ri-add-line mr-2"></i>
                    Create New Analysis
                  </button>
                </div>
              )}

              {/* Pagination */}
              {renderPagination()}
            </div>
          </div>
        </div>
        
        <Footer />
      </div>
    </div>
  );
}
