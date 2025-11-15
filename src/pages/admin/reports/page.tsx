
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminReports() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedPriority, setSelectedPriority] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [reportReadStatus, setReportReadStatus] = useState<{[key: number]: boolean}>({});
  const [resolvedReports, setResolvedReports] = useState<{[key: number]: boolean}>({});
  const [currentPage, setCurrentPage] = useState(1);
  const reportsPerPage = 5;

  // Mock data for reports
  const reports = [
    {
      id: 1,
      title: 'AI Analysis Accuracy Feedback',
      type: 'feedback',
      user: 'Sarah Johnson',
      email: 'sarah.johnson@email.com',
      content: 'The AI analysis was incredibly accurate for our retail business. It identified cost-saving opportunities that our team missed. The recommendations were actionable and resulted in 15% cost reduction.',
      category: 'Analysis Quality',
      priority: 'high',
      status: 'resolved',
      date: '2024-02-26',
      rating: 5,
      hasConversation: true,
      unreadMessages: 2
    },
    {
      id: 2,
      title: 'Feature Request: Export Options',
      type: 'feature_request',
      user: 'Michael Chen',
      email: 'michael.chen@company.com',
      content: 'Would love to see more export options for the analysis reports. Currently only PDF is available, but Excel and CSV formats would be very helpful for our team presentations.',
      category: 'Feature Enhancement',
      priority: 'medium',
      status: 'in_progress',
      date: '2024-02-25',
      rating: 4,
      hasConversation: true,
      unreadMessages: 3
    },
    {
      id: 3,
      title: 'Bug Report: Dashboard Loading Issue',
      type: 'bug_report',
      user: 'Emily Rodriguez',
      email: 'emily.r@startup.io',
      content: 'Experiencing slow loading times on the dashboard when accessing historical analysis data. Takes about 30 seconds to load reports from last month.',
      category: 'Technical Issue',
      priority: 'high',
      status: 'pending',
      date: '2024-02-24',
      rating: 2,
      hasConversation: true,
      unreadMessages: 2
    },
    {
      id: 4,
      title: 'Positive Feedback: Customer Support',
      type: 'feedback',
      user: 'David Kim',
      email: 'david.kim@logistics.com',
      content: 'Outstanding customer support experience. The team helped us integrate the AI analyst with our existing systems seamlessly. Response time was excellent.',
      category: 'Customer Service',
      priority: 'low',
      status: 'resolved',
      date: '2024-02-23',
      rating: 5,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 5,
      title: 'Feature Request: Real-time Alerts',
      type: 'feature_request',
      user: 'Lisa Thompson',
      email: 'lisa@strategyplus.com',
      content: 'It would be great to have real-time alerts when the AI detects significant changes in business metrics or identifies urgent optimization opportunities.',
      category: 'Feature Enhancement',
      priority: 'medium',
      status: 'planned',
      date: '2024-02-22',
      rating: 4,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 6,
      title: 'UI/UX Improvement Suggestion',
      type: 'feedback',
      user: 'James Wilson',
      email: 'james.wilson@growthcorp.com',
      content: 'The analysis results page could benefit from better data visualization. Charts and graphs would make it easier to understand the insights at a glance.',
      category: 'User Experience',
      priority: 'medium',
      status: 'in_progress',
      date: '2024-02-21',
      rating: 3,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 7,
      title: 'Integration Request: Salesforce',
      type: 'feature_request',
      user: 'Anna Martinez',
      email: 'anna.martinez@retail.com',
      content: 'Our team would benefit greatly from direct Salesforce integration. This would allow us to pull customer data directly for more comprehensive analysis.',
      category: 'Integration',
      priority: 'high',
      status: 'planned',
      date: '2024-02-20',
      rating: 4,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 8,
      title: 'Performance Feedback',
      type: 'feedback',
      user: 'Robert Taylor',
      email: 'robert.taylor@finance.org',
      content: 'The AI analysis speed has improved significantly over the past month. What used to take 10 minutes now completes in under 3 minutes. Great optimization work!',
      category: 'Performance',
      priority: 'low',
      status: 'resolved',
      date: '2024-02-19',
      rating: 5,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 9,
      title: 'Security Concern: Data Privacy',
      type: 'bug_report',
      user: 'Jennifer Lee',
      email: 'jennifer.lee@security.com',
      content: 'Need clarification on data privacy measures. How is sensitive business data protected during analysis?',
      category: 'Security',
      priority: 'high',
      status: 'pending',
      date: '2024-02-18',
      rating: 3,
      hasConversation: true,
      unreadMessages: 1
    },
    {
      id: 10,
      title: 'Mobile App Feature Request',
      type: 'feature_request',
      user: 'Mark Davis',
      email: 'mark.davis@mobile.com',
      content: 'Would love to have a mobile app version for quick access to analysis results on the go.',
      category: 'Mobile Development',
      priority: 'medium',
      status: 'planned',
      date: '2024-02-17',
      rating: 4,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 11,
      title: 'API Documentation Request',
      type: 'feedback',
      user: 'Rachel Green',
      email: 'rachel.green@developer.com',
      content: 'The API documentation could be more comprehensive with more examples and use cases.',
      category: 'Documentation',
      priority: 'medium',
      status: 'in_progress',
      date: '2024-02-16',
      rating: 3,
      hasConversation: false,
      unreadMessages: 0
    },
    {
      id: 12,
      title: 'Billing Issue Report',
      type: 'bug_report',
      user: 'Tom Brown',
      email: 'tom.brown@billing.com',
      content: 'Experiencing issues with subscription billing. Double charges appearing on credit card.',
      category: 'Billing',
      priority: 'high',
      status: 'resolved',
      date: '2024-02-15',
      rating: 2,
      hasConversation: false,
      unreadMessages: 0
    }
  ];

  // Calculate total unread messages for sidebar
  const totalUnreadMessages = reports.reduce((sum, report) => {
    if (!reportReadStatus[report.id] && report.unreadMessages > 0) {
      return sum + report.unreadMessages;
    }
    return sum;
  }, 0);

  // Store unread count in localStorage for sidebar access
  useEffect(() => {
    localStorage.setItem('adminReportsUnreadCount', totalUnreadMessages.toString());
    // Dispatch custom event to notify sidebar of count change
    window.dispatchEvent(new CustomEvent('adminReportsUnreadCountChanged', { 
      detail: { count: totalUnreadMessages } 
    }));
  }, [totalUnreadMessages, reportReadStatus]);

  // Load read status from localStorage on component mount
  useEffect(() => {
    const savedReadStatus = localStorage.getItem('reportReadStatus');
    if (savedReadStatus) {
      setReportReadStatus(JSON.parse(savedReadStatus));
    }
    
    const savedResolvedStatus = localStorage.getItem('resolvedReports');
    if (savedResolvedStatus) {
      setResolvedReports(JSON.parse(savedResolvedStatus));
    }
  }, []);

  // Listen for conversation read events
  useEffect(() => {
    const handleConversationRead = (event: CustomEvent) => {
      const { reportId } = event.detail;
      setReportReadStatus(prev => {
        const newStatus = {
          ...prev,
          [reportId]: true
        };
        localStorage.setItem('reportReadStatus', JSON.stringify(newStatus));
        return newStatus;
      });
    };

    const handlePageFocus = () => {
      // Refresh read status when page gains focus
      const savedReadStatus = localStorage.getItem('reportReadStatus');
      if (savedReadStatus) {
        setReportReadStatus(JSON.parse(savedReadStatus));
      }
    };

    window.addEventListener('reportConversationRead', handleConversationRead as EventListener);
    window.addEventListener('focus', handlePageFocus);

    return () => {
      window.removeEventListener('reportConversationRead', handleConversationRead as EventListener);
      window.removeEventListener('focus', handlePageFocus);
    };
  }, []);

  // Filter reports based on selected filters
  const filteredReports = reports.filter(report => {
    const matchesFilter = selectedFilter === 'all' || report.type === selectedFilter;
    const matchesStatus = selectedStatus === 'all' || report.status === selectedStatus;
    const matchesPriority = selectedPriority === 'all' || report.priority === selectedPriority;
    const matchesSearch = report.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         report.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         report.content.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesFilter && matchesStatus && matchesPriority && matchesSearch;
  });

  // Calculate pagination
  const indexOfLastReport = currentPage * reportsPerPage;
  const indexOfFirstReport = indexOfLastReport - reportsPerPage;
  const currentReports = filteredReports.slice(indexOfFirstReport, indexOfLastReport);
  const totalPages = Math.ceil(filteredReports.length / reportsPerPage);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedFilter, selectedStatus, selectedPriority, searchTerm]);

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <i 
        key={i} 
        className={`ri-star-${i < rating ? 'fill' : 'line'} text-yellow-400`}
      ></i>
    ));
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'feedback': return 'ri-feedback-line';
      case 'bug_report': return 'ri-bug-line';
      case 'feature_request': return 'ri-lightbulb-line';
      default: return 'ri-file-text-line';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'resolved': return 'bg-green-100 text-green-600';
      case 'in_progress': return 'bg-blue-100 text-blue-600';
      case 'pending': return 'bg-yellow-100 text-yellow-600';
      case 'planned': return 'bg-purple-100 text-purple-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-600';
      case 'medium': return 'bg-orange-100 text-orange-600';
      case 'low': return 'bg-green-100 text-green-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const hasUnreadMessages = (reportId: number) => {
    return !reportReadStatus[reportId];
  };

  const getUnreadCount = (report: any) => {
    return hasUnreadMessages(report.id) ? report.unreadMessages : 0;
  };

  const isReportResolved = (reportId: number) => {
    return resolvedReports[reportId] === true;
  };

  const markAsResolved = (reportId: number) => {
    const newResolvedStatus = {
      ...resolvedReports,
      [reportId]: true
    };
    setResolvedReports(newResolvedStatus);
    localStorage.setItem('resolvedReports', JSON.stringify(newResolvedStatus));
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
            <div className="mb-6">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">User Reports & Feedback</h1>
              <p className="text-gray-600">Manage user feedback, bug reports, and feature requests</p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Reports</p>
                    <p className="text-2xl font-bold text-gray-900">247</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                    <i className="ri-file-list-3-line text-xl text-blue-600"></i>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-green-600 font-medium">+12%</span>
                  <span className="text-gray-500 ml-2">from last month</span>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Pending</p>
                    <p className="text-2xl font-bold text-gray-900">23</p>
                  </div>
                  <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                    <i className="ri-time-line text-xl text-yellow-600"></i>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-red-600 font-medium">+3</span>
                  <span className="text-gray-500 ml-2">new today</span>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Resolved</p>
                    <p className="text-2xl font-bold text-gray-900">198</p>
                  </div>
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <i className="ri-check-line text-xl text-green-600"></i>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-green-600 font-medium">+18</span>
                  <span className="text-gray-500 ml-2">this week</span>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Avg Rating</p>
                    <p className="text-2xl font-bold text-gray-900">4.2</p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                    <i className="ri-star-line text-xl text-purple-600"></i>
                  </div>
                </div>
                <div className="mt-4 flex items-center text-sm">
                  <span className="text-green-600 font-medium">+0.3</span>
                  <span className="text-gray-500 ml-2">improvement</span>
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
                  <div className="relative">
                    <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Search reports..."
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Type</label>
                  <select
                    value={selectedFilter}
                    onChange={(e) => setSelectedFilter(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm pr-8"
                  >
                    <option value="all">All Types</option>
                    <option value="feedback">Feedback</option>
                    <option value="bug_report">Bug Reports</option>
                    <option value="feature_request">Feature Requests</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                  <select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm pr-8"
                  >
                    <option value="all">All Status</option>
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                    <option value="planned">Planned</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
                  <select
                    value={selectedPriority}
                    onChange={(e) => setSelectedPriority(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm pr-8"
                  >
                    <option value="all">All Priority</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Reports List */}
            <div className="space-y-4">
              {currentReports.map((report) => (
                <div key={report.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <i className={`${getTypeIcon(report.type)} text-xl text-red-600`}></i>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-gray-900">{report.user}</h3>
                        <span className="text-sm text-gray-500">({report.email})</span>
                        {report.rating && (
                          <div className="flex">
                            {renderStars(report.rating)}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(report.status)}`}>
                          {report.status.replace('_', ' ').charAt(0).toUpperCase() + report.status.replace('_', ' ').slice(1)}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(report.priority)}`}>
                          {report.priority.charAt(0).toUpperCase() + report.priority.slice(1)} Priority
                        </span>
                        <span className="text-xs text-gray-500">{report.category}</span>
                      </div>
                      <h4 className="font-medium text-gray-900 mb-2">{report.title}</h4>
                      <p className="text-gray-700 mb-3">{report.content}</p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-sm text-gray-500">
                          <span>{report.date}</span>
                          <span className="capitalize">{report.type.replace('_', ' ')}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          {hasUnreadMessages(report.id) && report.unreadMessages > 0 && report.hasConversation && (
                            <span className="text-sm text-red-600 font-medium">
                              {report.unreadMessages} unread messages
                            </span>
                          )}
                          {report.hasConversation ? (
                            <Link
                              to={`/admin/report-conversations/${report.id}`}
                              className="inline-flex items-center px-3 py-1 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap"
                            >
                              <i className="ri-chat-3-line mr-1"></i>
                              View Conversations
                            </Link>
                          ) : (
                            <button className="inline-flex items-center px-3 py-1 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap">
                              <i className="ri-reply-line mr-1"></i>
                              Respond
                            </button>
                          )}
                          {isReportResolved(report.id) ? (
                            <button 
                              disabled
                              className="inline-flex items-center px-3 py-1 bg-green-100 text-green-700 text-sm rounded-lg cursor-not-allowed whitespace-nowrap"
                            >
                              <i className="ri-check-line mr-1"></i>
                              Report Resolved
                            </button>
                          ) : (
                            <button 
                              onClick={() => markAsResolved(report.id)}
                              className="inline-flex items-center px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 transition-colors whitespace-nowrap"
                            >
                              <i className="ri-check-line mr-1"></i>
                              Mark as Resolved
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-8">
                <div className="text-sm text-gray-700">
                  Showing {indexOfFirstReport + 1} to {Math.min(indexOfLastReport, filteredReports.length)} of {filteredReports.length} reports
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`px-3 py-2 text-sm rounded-lg ${
                        currentPage === page
                          ? 'bg-red-600 text-white'
                          : 'border border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                  
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}

            {filteredReports.length === 0 && (
              <div className="text-center py-12">
                <i className="ri-file-list-3-line text-6xl text-gray-300 mb-4"></i>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No reports found</h3>
                <p className="text-gray-600">Try adjusting your filters or search terms.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}