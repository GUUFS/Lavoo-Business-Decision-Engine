
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';

export default function CustomerServicePage() {
  const navigate = useNavigate();
  const [issue, setIssue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [activeTab, setActiveTab] = useState('submit');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);
  const [reportsUnreadCount, setReportsUnreadCount] = useState(0);
  const [reportReadStatus, setReportReadStatus] = useState<{[key: number]: boolean}>({});

  useEffect(() => {
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Load unread counts and read status
  useEffect(() => {
    const loadUnreadCounts = () => {
      // Load reports unread count for tab badge
      const reportsCount = localStorage.getItem('reportsUnreadCount');
      setReportsUnreadCount(reportsCount ? parseInt(reportsCount) : 0);

      // Load read status for individual reports
      const readStatus = localStorage.getItem('reportReadStatus');
      if (readStatus) {
        setReportReadStatus(JSON.parse(readStatus));
      }
    };

    const handleReportsUnreadCountChange = (event: CustomEvent) => {
      setReportsUnreadCount(event.detail.count);
    };

    const handleReportReadStatusChange = (event: CustomEvent) => {
      setReportReadStatus(event.detail.readStatus);
    };

    loadUnreadCounts();
    window.addEventListener('reportsUnreadCountChanged', handleReportsUnreadCountChange as EventListener);
    window.addEventListener('reportReadStatusChanged', handleReportReadStatusChange as EventListener);

    return () => {
      window.removeEventListener('reportsUnreadCountChanged', handleReportsUnreadCountChange as EventListener);
      window.removeEventListener('reportReadStatusChanged', handleReportReadStatusChange as EventListener);
    };
  }, []);

  // Listen for page visibility changes to reload read status
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        const readStatus = localStorage.getItem('reportReadStatus');
        if (readStatus) {
          setReportReadStatus(JSON.parse(readStatus));
        }
        const reportsCount = localStorage.getItem('reportsUnreadCount');
        setReportsUnreadCount(reportsCount ? parseInt(reportsCount) : 0);
      }
    };

    const handleFocus = () => {
      const readStatus = localStorage.getItem('reportReadStatus');
      if (readStatus) {
        setReportReadStatus(JSON.parse(readStatus));
      }
      const reportsCount = localStorage.getItem('reportsUnreadCount');
      setReportsUnreadCount(reportsCount ? parseInt(reportsCount) : 0);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issue.trim()) return;

    setIsSubmitting(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Save the submitted issue to localStorage for the reports tab
    const existingReports = JSON.parse(localStorage.getItem('userReports') || '[]');
    const newReport = {
      id: Date.now(),
      issue: issue.trim(),
      status: 'Pending',
      submittedAt: new Date().toISOString(),
      hasResponse: false,
      unreadMessages: 0
    };
    existingReports.unshift(newReport);
    localStorage.setItem('userReports', JSON.stringify(existingReports));
    
    setIsSubmitting(false);
    setIsSubmitted(true);
    setIssue('');

    // Reset success message after 3 seconds
    setTimeout(() => {
      setIsSubmitted(false);
    }, 3000);
  };

  const handleViewConversation = (reportId: number) => {
    // Mark this report as read
    const newReadStatus = { ...reportReadStatus, [reportId]: true };
    setReportReadStatus(newReadStatus);
    localStorage.setItem('reportReadStatus', JSON.stringify(newReadStatus));

    // Update the report to remove unread messages
    const reports = JSON.parse(localStorage.getItem('userReports') || '[]');
    const updatedReports = reports.map((report: any) => {
      if (report.id === reportId) {
        const previousUnreadCount = report.unreadMessages || 0;
        
        // Reduce the total unread count
        const currentReportsUnreadCount = parseInt(localStorage.getItem('reportsUnreadCount') || '0');
        const newReportsUnreadCount = Math.max(0, currentReportsUnreadCount - previousUnreadCount);
        localStorage.setItem('reportsUnreadCount', newReportsUnreadCount.toString());
        setReportsUnreadCount(newReportsUnreadCount);

        // Also reduce customer service sidebar count
        const currentCustomerServiceCount = parseInt(localStorage.getItem('customerServiceUnreadCount') || '0');
        const newCustomerServiceCount = Math.max(0, currentCustomerServiceCount - previousUnreadCount);
        localStorage.setItem('customerServiceUnreadCount', newCustomerServiceCount.toString());

        // Dispatch events to update other components
        window.dispatchEvent(new CustomEvent('reportsUnreadCountChanged', { 
          detail: { count: newReportsUnreadCount } 
        }));
        window.dispatchEvent(new CustomEvent('customerServiceUnreadCountChanged', { 
          detail: { count: newCustomerServiceCount } 
        }));

        return { ...report, unreadMessages: 0 };
      }
      return report;
    });
    localStorage.setItem('userReports', JSON.stringify(updatedReports));

    // Navigate to conversation page
    navigate(`/dashboard/customer-service/conversation/${reportId}`);
  };

  const quickHelpOptions = [
    {
      title: 'Reports',
      description: 'View all your submitted issues',
      icon: 'ri-file-list-line',
      action: 'View Reports',
      onClick: () => setActiveTab('reports')
    },
    {
      title: 'Live Chat Support',
      description: 'Chat with our support team',
      icon: 'ri-chat-3-line',
      action: 'Start Chat'
    },
    {
      title: 'Documentation',
      description: 'Access user guides and tutorials',
      icon: 'ri-book-open-line',
      action: 'View Docs'
    },
    //{
      //title: 'Video Tutorials',
      //description: 'Watch step-by-step guides',
      //icon: 'ri-play-circle-line',
      //action: 'Watch Videos'
    //}
  ];

  // Get user reports from localStorage and add mock admin responses for demo
  const userReports = JSON.parse(localStorage.getItem('userReports') || '[]').map((report: any, index: number) => {
    // Add mock admin responses for demo purposes
    if (index < 2) {
      return {
        ...report,
        hasResponse: true,
        unreadMessages: reportReadStatus[report.id] ? 0 : (report.unreadMessages || Math.floor(Math.random() * 3) + 1)
      };
    }
    return report;
  });

  const isMobile = windowWidth < 768;

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Dashboard Sidebar */}
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      {/* Main Content */}
      <div className={`flex-1 transition-all duration-300 ${isMobile ? 'ml-0' : 0}`}>
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6 sm:mb-8">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Customer Service</h1>
              <p className="text-sm sm:text-base text-gray-600">Get help and support for your account</p>
            </div>

            {/* Tabs */}
            <div className="mb-6">
              <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
                <button
                  onClick={() => setActiveTab('submit')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                    activeTab === 'submit'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 hover:text-orange-600'
                  }`}
                >
                  Submit Issue
                </button>
                <button
                  onClick={() => setActiveTab('reports')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap relative ${
                    activeTab === 'reports'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 hover:text-orange-600'
                  }`}
                >
                  My Reports
                  {reportsUnreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-medium">
                      {reportsUnreadCount}
                    </span>
                  )}
                </button>
              </div>
            </div>

            {activeTab === 'submit' && (
              <>
                {/* Quick Help Options */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
                  {quickHelpOptions.map((option, index) => (
                    <div 
                      key={index} 
                      className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                      onClick={option.onClick}
                    >
                      <div className="text-center">
                        <div className="w-12 h-12 sm:w-14 sm:h-14 bg-orange-100 rounded-lg flex items-center justify-center mx-auto mb-3 sm:mb-4">
                          <i className={`${option.icon} text-orange-600 text-xl sm:text-2xl`}></i>
                        </div>
                        <h3 className="font-semibold text-gray-900 mb-2 text-sm sm:text-base">{option.title}</h3>
                        <p className="text-xs sm:text-sm text-gray-600 mb-3 sm:mb-4">{option.description}</p>
                        <button className="w-full bg-orange-500 text-white px-3 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium text-xs sm:text-sm whitespace-nowrap">
                          {option.action}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Support Form */}
                <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 lg:p-8 border border-gray-200 shadow-sm">
                  <div className="max-w-2xl mx-auto">
                    <div className="text-center mb-6 sm:mb-8">
                      <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i className="ri-customer-service-line text-orange-600 text-2xl sm:text-3xl"></i>
                      </div>
                      <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">Describe Your Issue</h2>
                      <p className="text-sm sm:text-base text-gray-600">
                        Tell us about the problem you're experiencing and we'll help you resolve it
                      </p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                      <div>
                        <label htmlFor="issue" className="block text-sm font-medium text-gray-700 mb-2">
                          Issue Description
                        </label>
                        <textarea
                          id="issue"
                          value={issue}
                          onChange={(e) => setIssue(e.target.value)}
                          placeholder="Please describe your issue in detail. Include any error messages, steps you took, and what you expected to happen..."
                          rows={8}
                          maxLength={500}
                          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none text-sm sm:text-base"
                          required
                        />
                        <div className="flex justify-between items-center mt-2">
                          <p className="text-xs text-gray-500">
                            Please provide as much detail as possible to help us assist you better
                          </p>
                          <p className="text-xs text-gray-500">
                            {issue.length}/500 characters
                          </p>
                        </div>
                      </div>

                      <div className="flex justify-center">
                        <button
                          type="submit"
                          disabled={isSubmitting || !issue.trim()}
                          className="bg-orange-500 text-white px-8 py-3 rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm sm:text-base whitespace-nowrap min-w-[200px]"
                        >
                          {isSubmitting ? (
                            <span className="flex items-center justify-center">
                              <i className="ri-loader-4-line animate-spin mr-2"></i>
                              Submitting...
                            </span>
                          ) : (
                            <span className="flex items-center justify-center">
                              <i className="ri-send-plane-line mr-2"></i>
                              Submit Issue
                            </span>
                          )}
                        </button>
                      </div>
                    </form>

                    {/* Success Message */}
                    {isSubmitted && (
                      <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                            <i className="ri-check-line text-green-600"></i>
                          </div>
                          <div>
                            <h3 className="font-semibold text-green-800">Issue Submitted Successfully!</h3>
                            <p className="text-sm text-green-700">
                              We've received your request and will respond within 24 hours.
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Contact Information */}
                    <div className="mt-8 pt-6 border-t border-gray-200">
                      <h3 className="font-semibold text-gray-900 mb-4 text-center">Other Ways to Reach Us</h3>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                        <div className="flex flex-col items-center">
                          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-2">
                            <i className="ri-mail-line text-blue-600"></i>
                          </div>
                          <p className="text-sm font-medium text-gray-900">Email</p>
                          <p className="text-xs text-gray-600">support@aitugo.com</p>
                        </div>
                        <div className="flex flex-col items-center">
                          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-2">
                            <i className="ri-phone-line text-green-600"></i>
                          </div>
                          <p className="text-sm font-medium text-gray-900">Phone</p>
                          <p className="text-xs text-gray-600">1-800-AI-HELP</p>
                        </div>
                        <div className="flex flex-col items-center">
                          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-2">
                            <i className="ri-time-line text-purple-600"></i>
                          </div>
                          <p className="text-sm font-medium text-gray-900">Hours</p>
                          <p className="text-xs text-gray-600">24/7 Support</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            {activeTab === 'reports' && (
              <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 lg:p-8 border border-gray-200 shadow-sm">
                <div className="mb-6">
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">My Reports</h2>
                  <p className="text-sm sm:text-base text-gray-600">
                    View all your submitted issues and their current status
                  </p>
                </div>

                {userReports.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <i className="ri-file-list-line text-gray-400 text-2xl"></i>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Reports Yet</h3>
                    <p className="text-gray-600 mb-4">You haven't submitted any issues yet.</p>
                    <button
                      onClick={() => setActiveTab('submit')}
                      className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium whitespace-nowrap"
                    >
                      Submit Your First Issue
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {userReports.map((report: any) => (
                      <div key={report.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <span className="text-sm font-medium text-gray-500">
                                Report #{report.id}
                              </span>
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                report.status === 'Pending' 
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : report.status === 'In Progress'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-green-100 text-green-800'
                              }`}>
                                {report.status}
                              </span>
                            </div>
                            <p className="text-gray-900 mb-2 line-clamp-3">{report.issue}</p>
                            <p className="text-sm text-gray-500">
                              Submitted on {new Date(report.submittedAt).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </p>
                          </div>
                        </div>
                        
                        {report.hasResponse && (
                          <div className="mt-3 pt-3 border-t border-gray-100">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-sm text-green-600 font-medium">
                                  <i className="ri-message-line mr-1"></i>
                                  Admin has responded
                                </span>
                                {report.unreadMessages > 0 && !reportReadStatus[report.id] && (
                                  <span className="text-xs text-red-600 font-medium">
                                    {report.unreadMessages} unread message{report.unreadMessages > 1 ? 's' : ''}
                                  </span>
                                )}
                              </div>
                              <button 
                                onClick={() => handleViewConversation(report.id)}
                                className="text-orange-600 hover:text-orange-700 text-sm font-medium whitespace-nowrap"
                              >
                                View Conversation
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
