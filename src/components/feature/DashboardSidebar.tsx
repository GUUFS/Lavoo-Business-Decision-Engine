
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { User, BarChart3, Brain, BadgePlus, Database, Users, Star, Globe, Search,  Home, TrendingUp, AlertTriangle, DollarSign, Headphones } from 'lucide-react';

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
    label: 'AI Analyst',
    icon: <Search className="w-5 h-5" />,
    path: '/dashboard/analyze'
  },
   {
    id: 'alerts',
    label: 'Opportunity Alerts',
    icon: <AlertTriangle className="w-5 h-5" />,
    path: '/dashboard/alerts'
  },
   {
    id: 'insights',
    label: 'AI Insights',
    icon: <Brain className="w-5 h-5" />,
    path: '/dashboard/insights'
  },
  {
    id: 'earnings',
    label: 'Earnings',
    icon: <DollarSign className="w-5 h-5" />,
    path: '/dashboard/earnings'
  },
  {
    id: 'upgrade',
    label: 'Upgrade',
    icon: <BadgePlus className="w-5 h-5"/>,
    path:'/dashboard/upgrade'
  },
  {
    id: 'reviews',
    label: 'My Reviews',
    icon: <Star className="w-5 h-5" />,
    path: '/dashboard/reviews'
  },
  {
    id: 'ai_trends',
    label: 'AI Trends',
    icon: <Globe className="w-5 h-5" />,
    path: '/dashboard/ai_trends'
  },
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

export default function DashboardSidebar({  isMobileMenuOpen = false, 
  setIsMobileMenuOpen,
  isCollapsed = false,
  setIsCollapsed  }: DashboardSidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();

  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 768);
   
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  const handleItemClick = (path: string) => {
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
        <div className={`bg-white border-r border-gray-200 transition-transform duration-300 w-64 h-screen fixed left-0 top-0 z-50 flex flex-col md:hidden ${
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
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
                      onClick={() => handleItemClick(item.path)}
                      className={`w-full flex items-center px-3 py-3 rounded-lg transition-colors cursor-pointer ${
                        isActive
                          ? 'bg-orange-50 text-orange-600 border border-orange-200'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-orange-600'
                      }`}
                    >
                      <span className={`${isActive ? 'text-orange-600' : 'text-gray-500'}`}>
                        {item.icon}
                      </span>
                      <span className="ml-3 font-medium whitespace-nowrap">{item.label}</span>
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
      `}>      {/* Sidebar Header */}
      <div className="p-4 border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center justify-between">
          {!isCollapsed && (
            <div
            className="flex items-center cursor-pointer"
            
          >
            <div className="w-8 h-8 sm:w-10 sm:h-10 bg-orange-500 rounded-lg flex items-center justify-center mr-2 sm:mr-3">
              <i className="ri-brain-line text-white text-lg sm:text-xl"></i>
            </div>
            <span className="text-lg sm:text-xl font-bold text-black">
              Lavoo
            </span>
          </div>
            // <h2 className="text-lg font-semibold text-gray-800">Dashboard</h2>
          )}
          <button
            onClick={() => setIsCollapsed && setIsCollapsed(!isCollapsed)}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
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
                  onClick={() => handleItemClick(item.path)}
                  className={`w-full flex items-center px-3 py-3 rounded-lg transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-orange-50 text-orange-600 border border-orange-200'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-orange-600'
                  }`}
                  title={isCollapsed ? item.label : undefined}
                >
                  <span className={`${isActive ? 'text-orange-600' : 'text-gray-500'}`}>
                    {item.icon}
                  </span>
                  {!isCollapsed && (
                    <span className="ml-3 font-medium whitespace-nowrap">{item.label}</span>
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
