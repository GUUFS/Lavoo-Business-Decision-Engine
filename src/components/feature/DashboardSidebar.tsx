
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { User, BadgePlus, Star, Search, Home, AlertTriangle, DollarSign, Headphones } from 'lucide-react';

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

const sidebarItems: SidebarItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <Home className="w-5 h-5" />,
    path: '/dashboard'
  },
  {
    id: 'analyze',
    label: 'Decision Engine',
    icon: <Search className="w-5 h-5" />,
    path: '/dashboard/analyze'
  },
  {
    id: 'alerts',
    label: 'Opportunity Alerts',
    icon: <AlertTriangle className="w-5 h-5" />,
    path: '/dashboard/alerts'
  },
  // {
  // id: 'insights',
  // label: 'AI Insights',
  // icon: <Brain className="w-5 h-5" />,
  // path: '/dashboard/insights'
  // },
  {
    id: 'earnings',
    label: 'Earnings',
    icon: <DollarSign className="w-5 h-5" />,
    path: '/dashboard/earnings'
  },
  {
    id: 'upgrade',
    label: 'Upgrade',
    icon: <BadgePlus className="w-5 h-5" />,
    path: '/dashboard/upgrade'
  },
  {
    id: 'reviews',
    label: 'My Reviews',
    icon: <Star className="w-5 h-5" />,
    path: '/dashboard/reviews'
  },
  // {
  // id: 'ai_trends',
  // label: 'AI Trends',
  // icon: <Globe className="w-5 h-5" />,
  // path: '/dashboard/ai_trends'
  // },
  {
    id: 'customer-service',
    label: 'Customer Service',
    icon: <Headphones className="w-5 h-5" />,
    path: '/dashboard/customer-service'
  },
  {
    id: 'profile',
    label: 'Profile',
    icon: <User className="w-5 h-5" />,
    path: '/dashboard/profile'
  }

];

interface DashboardSidebarProps {
  isMobileMenuOpen?: boolean;
  setIsMobileMenuOpen?: (open: boolean) => void;
  isCollapsed?: boolean;
  setIsCollapsed?: (collapsed: boolean) => void;
}

export default function DashboardSidebar({ isMobileMenuOpen = false,
  setIsMobileMenuOpen,
  isCollapsed = false,
  setIsCollapsed }: DashboardSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const [isMobile, setIsMobile] = useState(false);
  const [unreadTickets, setUnreadTickets] = useState(0);

  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  // Poll for unread tickets and WebSocket connection
  useEffect(() => {
    // 1. Initial Poll (and fallback)
    const pollUnread = async () => {
      // Check for token first to avoid 401 spam
      const token = localStorage.getItem("auth_token") || localStorage.getItem("user_token") || localStorage.getItem("access_token");
      if (!token) return;

      try {
        // Use fetch with credentials AND Bearer token
        const headers: HeadersInit = {
          'Content-Type': 'application/json'
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch('http://localhost:8000/api/customer-service/tickets/unread-count', {
          credentials: 'include',
          headers: headers
        });

        if (response.ok) {
          const data = await response.json();
          setUnreadTickets(data.count);
        }
      } catch (error) {
        console.error('Error polling unread tickets', error);
      }
    };

    pollUnread();

    // 2. WebSocket Connection
    let ws: WebSocket | null = null;
    try {
      // Determine WS URL (assuming localhost for now or infer from window.location)
      const wsUrl = "ws://localhost:8000/api/customer-service/ws/notifications";
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("Connected to Notifications WS");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'new_reply') {
            // QUIET MODE: If user is actively viewing the conversation, don't ping them
            // We check the URL pathname
            const currentPath = window.location.pathname;
            // Expected format: /dashboard/customer-service/conversation/{id}
            if (currentPath.includes(`/conversation/${data.payload?.ticket_id}`)) {
              // User IS viewing this ticket. Do nothing?
              // Ideally update the UI but that's handled by the page's own polling/socket
              return;
            }

            // Refresh count immediately
            pollUnread();
          }
        } catch (e) {
          console.error("WS parse error", e);
        }
      };

      ws.onclose = () => {
        console.log("Notifications WS disconnected");
      };
    } catch (e) {
      console.error("WS Connection error", e);
    }

    // Still keep polling as backup (every 60s)
    const interval = setInterval(pollUnread, 60000);

    return () => {
      clearInterval(interval);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, []);

  const handleItemClick = (path: string, id: string) => {
    if (id === 'ai_trends') return; // Disable for "Coming soon" item
    navigate(path);
    if (isMobile && setIsMobileMenuOpen) {
      setIsMobileMenuOpen(false);
    }
  };

  const handleToggleCollapse = () => {
    if (isMobile && setIsMobileMenuOpen) {
      setIsMobileMenuOpen(!isMobileMenuOpen);
    }
  };

  // Mobile sidebar
  if (isMobile) {
    return (
      <>
        {/* Mobile Menu Button */}
        <button
          onClick={handleToggleCollapse}
          className="md:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-lg border border-gray-200 hover:bg-gray-50 transition-colors"
        >
          <i className={`${isMobileMenuOpen ? 'ri-close-line' : 'ri-menu-line'} text-xl text-gray-600`}></i>
        </button>

        {/* Mobile Overlay */}
        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
            onClick={() => setIsMobileMenuOpen && setIsMobileMenuOpen(false)}
          />
        )}

        {/* Mobile Sidebar */}
        <div className={`bg-white border-r border-gray-200 transition-transform duration-300 w-64 h-screen fixed left-0 top-0 z-50 flex flex-col md:hidden ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
          }`}>
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">Dashboard</h2>
              <button
                onClick={() => setIsMobileMenuOpen && setIsMobileMenuOpen(false)}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <i className="ri-close-line text-gray-600"></i>
              </button>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="p-4 flex-1 overflow-y-auto">
            <ul className="space-y-2">
              {sidebarItems.map((item) => {
                const isActive = location.pathname === item.path;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => handleItemClick(item.path, item.id)}
                      className={`w-full flex items-center px-3 py-3 rounded-lg transition-colors cursor-pointer ${isActive
                        ? 'bg-orange-50 text-orange-600 border border-orange-200'
                        : item.id === 'ai_trends'
                          ? 'text-gray-400 cursor-not-allowed italic'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-orange-600'
                        }`}
                      disabled={item.id === 'ai_trends'}
                    >
                      <span className={`${isActive ? 'text-orange-600' : item.id === 'ai_trends' ? 'text-gray-300' : 'text-gray-500'}`}>
                        {item.icon}
                      </span>
                      <div className="flex-1 flex items-center justify-between ml-3">
                        <div className="flex flex-col items-start">
                          <span className="font-medium whitespace-nowrap">{item.label}</span>
                          {item.id === 'ai_trends' && (
                            <span className="text-[10px] font-bold text-orange-400 -mt-1 uppercase tracking-tighter italic">Coming soon</span>
                          )}
                        </div>
                        {item.id === 'customer-service' && unreadTickets > 0 && (
                          <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                            {unreadTickets}
                          </span>
                        )}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* User Info at Bottom */}
          <div className="p-4 flex-shrink-0">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-orange-600" />
                </div>
                <div className="ml-3">

                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

  // Desktop sidebar
  return (
    <>
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setIsMobileMenuOpen && setIsMobileMenuOpen(false)}
        />
      )}

      {/* Mobile/Desktop Sidebar */}
      <div className={`bg-white border-r border-gray-200 transition-all duration-300 h-screen fixed left-0 top-0 flex flex-col
        md:z-40 z-50
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        ${isCollapsed ? 'md:w-16' : 'md:w-64'}
        w-64
      `}>      {/* Sidebar Header - Fixed height so logo size doesn't affect nav */}
        <div className="p-4 border-b border-gray-200 flex-shrink-0 h-[80px] overflow-hidden relative">
          <div className="flex items-center justify-between h-full">
            {!isCollapsed && (
              <div
                className="flex items-center cursor-pointer absolute left-4 top-1/2 -translate-y-1/2"

              >
                <img
                  src="/logo.png"
                  alt="Lavoo"
                  className="h-[120px] sm:h-[220px] w-auto object-contain max-h-[120px]"
                />
              </div>
              // <h2 className="text-lg font-semibold text-gray-800">Dashboard</h2>
            )}
            <button
              onClick={() => setIsCollapsed && setIsCollapsed(!isCollapsed)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors ml-auto"
            >
              <i className={`ri-menu-${isCollapsed ? 'unfold' : 'fold'}-line text-gray-600`}></i>
            </button>
          </div>
        </div>

        {/* Navigation Items - Scrollable */}
        <nav className="p-4 flex-1 overflow-y-auto">
          <ul className="space-y-2">
            {sidebarItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.id}>
                  <button
                    onClick={() => handleItemClick(item.path, item.id)}
                    className={`w-full flex items-center px-3 py-3 rounded-lg transition-colors cursor-pointer ${isActive
                      ? 'bg-orange-50 text-orange-600 border border-orange-200'
                      : item.id === 'ai_trends'
                        ? 'text-gray-400 cursor-not-allowed italic'
                        : 'text-gray-700 hover:bg-gray-50 hover:text-orange-600'
                      }`}
                    title={item.id === 'ai_trends' ? "Coming soon" : (isCollapsed ? item.label : undefined)}
                    disabled={item.id === 'ai_trends'}
                  >
                    <span className={`${isActive ? 'text-orange-600' : item.id === 'ai_trends' ? 'text-gray-300' : 'text-gray-500'}`}>
                      {item.icon}
                    </span>
                    {!isCollapsed && (
                      <div className="flex-1 flex items-center justify-between ml-3">
                        <div className="flex flex-col items-start">
                          <span className="font-medium whitespace-nowrap">{item.label}</span>
                          {item.id === 'ai_trends' && (
                            <span className="text-[10px] font-bold text-orange-400 -mt-1 uppercase tracking-tighter italic">Coming soon</span>
                          )}
                        </div>
                        {item.id === 'customer-service' && unreadTickets > 0 && (
                          <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                            {unreadTickets}
                          </span>
                        )}
                      </div>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>


      </div>
    </>
  );
}
