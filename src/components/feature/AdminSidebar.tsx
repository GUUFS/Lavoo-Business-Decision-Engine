
import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface AdminSidebarProps {
  isMobileMenuOpen: boolean;
  setIsMobileMenuOpen: (open: boolean) => void;
  isCollapsed?: boolean;
  setIsCollapsed?: (collapsed: boolean) => void;
}

export default function AdminSidebar({
  isMobileMenuOpen,
  setIsMobileMenuOpen,
  isCollapsed = false,
  setIsCollapsed
}: AdminSidebarProps) {
  const location = useLocation();
  const [reportsUnreadCount, setReportsUnreadCount] = useState(0);
  const [reviewsUnreadCount, setReviewsUnreadCount] = useState(0);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    // 1. Initial Load from LocalStorage
    const loadFromStorage = () => {
      setReportsUnreadCount(parseInt(localStorage.getItem('adminReportsUnreadCount') || '0', 10));
      setReviewsUnreadCount(parseInt(localStorage.getItem('adminReviewsUnreadCount') || '0', 10));
    };
    loadFromStorage();

    // 2. Poll for updates
    const pollUnreadCounts = async () => {
      try {
        const token = document.cookie
          .split('; ')
          .find((row) => row.startsWith('access_token='))
          ?.split('=')[1];

        if (!token) return;

        const headers = { 'Authorization': `Bearer ${token} ` };

        // Poll Reports (Tickets)
        const reportsRes = await fetch('http://localhost:8000/api/customer-service/admin/unread-count', { headers });
        if (reportsRes.ok) {
          const data = await reportsRes.json();
          setReportsUnreadCount(data.count);
          localStorage.setItem('adminReportsUnreadCount', data.count.toString());
        }

        // You can also poll Reviews here if an endpoint exists
        // const reviewsRes = await fetch('/api/admin/reviews/unread-count', { headers }); ...

      } catch (error) {
        console.error('Error polling notifications:', error);
      }
    };

    // Poll immediately and then every 30s
    pollUnreadCounts();
    const interval = setInterval(pollUnreadCounts, 30000);

    // 3. Listen for internal events (optimistic updates)
    const handleReportsChange = (e: any) => {
      if (e.detail && typeof e.detail.count === 'number') {
        setReportsUnreadCount(e.detail.count);
        localStorage.setItem('adminReportsUnreadCount', e.detail.count.toString());
      }
    };

    const handleReviewsChange = (e: any) => {
      if (e.detail && typeof e.detail.count === 'number') {
        setReviewsUnreadCount(e.detail.count);
        localStorage.setItem('adminReviewsUnreadCount', e.detail.count.toString());
      }
    };

    window.addEventListener('adminReportsUnreadCountChanged', handleReportsChange);
    window.addEventListener('adminReviewsUnreadCountChanged', handleReviewsChange);

    return () => {
      clearInterval(interval);
      window.removeEventListener('adminReportsUnreadCountChanged', handleReportsChange);
      window.removeEventListener('adminReviewsUnreadCountChanged', handleReviewsChange);
    };
  }, []);

  const menuItems = [
    {
      name: 'Dashboard',
      href: '/admin',
      icon: 'ri-dashboard-line',
      current: location.pathname === '/admin'
    },
    {
      name: 'User Management',
      href: '/admin/users',
      icon: 'ri-user-line',
      current: location.pathname === '/admin/users'
    },
    {
      name: 'Analytics',
      href: '/admin/analytics',
      icon: 'ri-bar-chart-line',
      current: location.pathname === '/admin/analytics'
    },
    {
      name: 'Reviews',
      href: '/admin/reviews',
      icon: 'ri-star-line',
      current: location.pathname === '/admin/reviews'
    },
    {
      name: 'Reports',
      href: '/admin/reports',
      icon: 'ri-file-text-line',
      current: location.pathname === '/admin/reports'
    },
    {
      name: 'Revenue',
      href: '/admin/revenue',
      icon: 'ri-money-dollar-circle-line',
      current: location.pathname === '/admin/revenue'
    },
    {
      name: 'AI Analysis',
      href: '/admin/ai-analysis',
      icon: 'ri-robot-line',
      current: location.pathname === '/admin/ai-analysis'
    },
    {
      name: 'Content',
      href: '/admin/content-management',
      icon: 'ri-file-text-line',
      current: location.pathname === '/admin/content-management'
    },
    {
      name: 'System Health',
      href: '/admin/system-health',
      icon: 'ri-heart-pulse-line',
      current: location.pathname === '/admin/system-health'
    },
    {
      name: 'Security',
      href: '/admin/security',
      icon: 'ri-shield-line',
      current: location.pathname === '/admin/security'
    },
    {
      name: 'Database',
      href: '/admin/database',
      icon: 'ri-database-line',
      current: location.pathname === '/admin/database'
    },
    {
      name: 'Notifications',
      href: '/admin/notifications',
      icon: 'ri-notification-line',
      current: location.pathname === '/admin/notifications'
    },
    {
      name: 'Settings',
      href: '/admin/settings',
      icon: 'ri-settings-line',
      current: location.pathname === '/admin/settings'
    },
    {
      name: 'Profile',
      href: '/admin/profile',
      icon: 'ri-user-settings-line',
      current: location.pathname === '/admin/profile'
    }
  ];

  return (
    <>
      {/* Mobile menu overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed top-0 left-0 z-50 ${isCollapsed ? 'w-16' : 'w-64'} h-screen bg-white shadow-lg transform transition-all duration-300 ease-in-out md:translate-x-0 ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="h-20 flex items-center justify-between px-6 border-b border-gray-100">
            {!isCollapsed && (
              <Link to="/admin" className="flex items-center">
                <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center mr-3">
                  <i className="ri-admin-line text-white text-lg"></i>
                </div>
                <span className="text-xl font-bold text-gray-900">Admin Panel</span>
              </Link>
            )}
            <button
              onClick={() => isMobile ? setIsMobileMenuOpen(false) : setIsCollapsed?.(!isCollapsed)}
              className="p-2 rounded-lg text-gray-600 hover:bg-gray-100"
            >
              <i className={`${isCollapsed ? 'ri-menu-unfold-line' : 'ri-menu-fold-line'} text-xl`}></i>
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
            {menuItems.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center justify-between px-3 py-3 text-sm font-medium rounded-lg transition-colors ${item.current
                  ? 'bg-red-50 text-red-600 border-r-2 border-red-600'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                <div className="flex items-center">
                  <i className={`${item.icon} text-lg ${isCollapsed ? 'mr-0' : 'mr-3'}`}></i>
                  {!isCollapsed && item.name}
                </div>
                {!isCollapsed && item.name === 'Reports' && reportsUnreadCount > 0 && (
                  <span className="bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    {reportsUnreadCount}
                  </span>
                )}
                {!isCollapsed && item.name === 'Reviews' && reviewsUnreadCount > 0 && (
                  <span className="bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    {reviewsUnreadCount}
                  </span>
                )}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </>
  );
}
