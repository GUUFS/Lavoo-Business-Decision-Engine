
import { useState, useEffect } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';


export default function AdminNotifications() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Clear notification badge when page loads
  useEffect(() => {
    // Dispatch event to clear notification badge
    window.dispatchEvent(new CustomEvent('notificationsViewed'));
  }, []);

  // Mock notifications data
  const notifications = [
    {
      id: 1,
      type: 'user_signup',
      title: 'New User Registration',
      message: 'Sarah Johnson has created a new account',
      timestamp: '2024-02-26T10:30:00Z',
      isRead: false,
      priority: 'medium',
      user: 'Sarah Johnson'
    },
    {
      id: 2,
      type: 'system_alert',
      title: 'System Maintenance Scheduled',
      message: 'Scheduled maintenance window: March 1st, 2:00 AM - 4:00 AM EST',
      timestamp: '2024-02-25T14:15:00Z',
      isRead: true,
      priority: 'high'
    },
    {
      id: 3,
      type: 'security',
      title: 'Failed Login Attempts',
      message: 'Multiple failed login attempts detected from IP: 192.168.1.100',
      timestamp: '2024-02-25T09:20:00Z',
      isRead: false,
      priority: 'high'
    },
    {
      id: 4,
      type: 'revenue',
      title: 'Revenue Milestone Reached',
      message: 'Monthly revenue target of $50,000 has been achieved',
      timestamp: '2024-02-24T16:45:00Z',
      isRead: true,
      priority: 'medium'
    },
    {
      id: 5,
      type: 'user_feedback',
      title: 'New User Feedback',
      message: 'Michael Chen submitted feedback about export features',
      timestamp: '2024-02-24T11:30:00Z',
      isRead: false,
      priority: 'low',
      user: 'Michael Chen'
    },
    {
      id: 6,
      type: 'system_alert',
      title: 'Database Backup Completed',
      message: 'Daily database backup completed successfully at 3:00 AM',
      timestamp: '2024-02-24T03:00:00Z',
      isRead: true,
      priority: 'low'
    },
    {
      id: 7,
      type: 'security',
      title: 'New Device Login',
      message: 'Admin login detected from new device: Chrome on Windows',
      timestamp: '2024-02-23T15:20:00Z',
      isRead: false,
      priority: 'medium'
    },
    {
      id: 8,
      type: 'user_signup',
      title: 'Bulk User Registration',
      message: '15 new users registered through corporate signup',
      timestamp: '2024-02-23T12:45:00Z',
      isRead: true,
      priority: 'medium'
    },
    {
      id: 9,
      type: 'revenue',
      title: 'Payment Processing Alert',
      message: 'Payment gateway experiencing minor delays',
      timestamp: '2024-02-23T09:15:00Z',
      isRead: false,
      priority: 'high'
    },
    {
      id: 10,
      type: 'user_feedback',
      title: 'Feature Request Submitted',
      message: 'Emma Wilson requested dark mode functionality',
      timestamp: '2024-02-22T18:30:00Z',
      isRead: true,
      priority: 'low',
      user: 'Emma Wilson'
    },
    {
      id: 11,
      type: 'system_alert',
      title: 'Server Performance Warning',
      message: 'CPU usage exceeded 85% threshold for 10 minutes',
      timestamp: '2024-02-22T14:20:00Z',
      isRead: false,
      priority: 'high'
    },
    {
      id: 12,
      type: 'security',
      title: 'Password Policy Update',
      message: 'New password requirements will take effect March 1st',
      timestamp: '2024-02-22T10:00:00Z',
      isRead: true,
      priority: 'medium'
    }
  ];

  // Pagination calculations
  const totalPages = Math.ceil(notifications.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentNotifications = notifications.slice(startIndex, endIndex);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'user_signup': return 'ri-user-add-line';
      case 'system_alert': return 'ri-alert-line';
      case 'security': return 'ri-shield-check-line';
      case 'revenue': return 'ri-money-dollar-circle-line';
      case 'user_feedback': return 'ri-feedback-line';
      default: return 'ri-notification-line';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'user_signup': return 'bg-blue-100 text-blue-600';
      case 'system_alert': return 'bg-orange-100 text-orange-600';
      case 'security': return 'bg-red-100 text-red-600';
      case 'revenue': return 'bg-green-100 text-green-600';
      case 'user_feedback': return 'bg-purple-100 text-purple-600';
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

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${diffInHours}h ago`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays}d ago`;
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const renderPageNumbers = () => {
    const pages = [];
    for (let i = 1; i <= totalPages; i++) {
      pages.push(
        <button
          key={i}
          onClick={() => handlePageChange(i)}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            currentPage === i
              ? 'bg-red-600 text-white'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          {i}
        </button>
      );
    }
    return pages;
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
              
              {/* Profile Dropdown */}
              {isProfileDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <button className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-3">
                    <i className="ri-user-line text-gray-500"></i>
                    Profile
                  </button>
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
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Notifications</h1>
              <p className="text-gray-600">Stay updated with system alerts and user activities</p>
            </div>

            {/* Notifications List */}
            <div className="space-y-4 mb-6">
              {currentNotifications.map((notification) => (
                <div 
                  key={notification.id} 
                  className={`bg-white rounded-xl shadow-sm border border-gray-200 p-6 ${
                    !notification.isRead ? 'border-l-4 border-l-red-500' : ''
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${getTypeColor(notification.type)}`}>
                      <i className={`${getTypeIcon(notification.type)} text-xl`}></i>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold text-gray-900">{notification.title}</h3>
                        {!notification.isRead && (
                          <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                        )}
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(notification.priority)}`}>
                          {notification.priority.charAt(0).toUpperCase() + notification.priority.slice(1)}
                        </span>
                      </div>
                      <p className="text-gray-700 mb-3">{notification.message}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>{formatTimestamp(notification.timestamp)}</span>
                        {notification.user && (
                          <span>by {notification.user}</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    Showing {startIndex + 1} to {Math.min(endIndex, notifications.length)} of {notifications.length} notifications
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    {renderPageNumbers()}
                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
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
  );
}
