import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Cookies from "js-cookie";
import { useQueryClient } from "@tanstack/react-query";

import Button from "../base/Button";
import { useCurrentUser } from "../../api/user";

interface HeaderProps {
  onMobileMenuClick?: () => void;
}

interface Notification {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
}

export default function Header({ onMobileMenuClick }: HeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [, setIsMobileMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([
    {
      id: "1",
      title: "Welcome to Lavoo",
      message: "Get started by watching our demo video.",
      time: "2 mins ago",
      read: false,
    },
    {
      id: "2",
      title: "Analysis Complete",
      message: "Your latest business analysis is ready to view.",
      time: "1 hour ago",
      read: false,
    },
    {
      id: "3",
      title: "New Feature",
      message: "Try our new comprehensive market scanner.",
      time: "1 day ago",
      read: false,
    }
  ]);

  const queryClient = useQueryClient();
  const notificationRef = useRef<HTMLDivElement>(null);

  const { data: user, isLoading } = useCurrentUser();

  const isLoggedIn = !!user;
  const isAnalyzePage = location.pathname === "/analyze";
  const isLoginPage = location.pathname === "/login";
  const isSignUpPage = location.pathname === "/signup";
  const isDashboard = location.pathname.includes("dashboard") ||
    location.pathname.includes("/results") ||
    location.pathname.includes("/analysis-history");
  const isAdmin = location.pathname.includes("/admin");

  // Derived state for unread count
  const unreadCount = notifications.filter(n => !n.read).length;

  const handleLogout = () => {
    // Clear the cookies
    Cookies.remove("access_token");
    Cookies.remove("auth_token");
    Cookies.remove("user_token");

    // Clear local storage
    localStorage.clear();

    // Invalidate queries
    queryClient.invalidateQueries({ queryKey: ["currentUser"] });
    queryClient.removeQueries({ queryKey: ["currentUser"] });

    // Navigate and force state reset
    navigate("/login", { replace: true });
    window.location.reload(); // Force full reload to clear all in-memory states
  };

  const scrollToSection = (sectionId: string) => {
    if (location.pathname !== "/") {
      navigate("/");
      setTimeout(() => {
        document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } else {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth" });
    }
    setIsMobileMenuOpen(false);
  };

  const handleNotificationClick = () => {
    if (!isNotificationsOpen) {
      // When opening, mark all as read logic is usually done here or just purely visual "disappear count"
      // User rq: "When the user clicks on the notification icon and views the notifications, then the count disappears."
      // So we will mark them as read in the state.
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    }
    setIsNotificationsOpen(!isNotificationsOpen);
  };

  // Close notifications when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setIsNotificationsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);


  if (!isAdmin)

    return (
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`flex justify-between items-center h-16 sm:h-20 ${isDashboard ? "!justify-end w-full" : ""}`}>
            {/* Logo */}
            {/* Mobile Menu Button - Show hamburger in dashboard */}
            {isDashboard ? (
              <button
                className="md:hidden p-2 text-gray-700 hover:text-orange-500 transition-colors"
                onClick={onMobileMenuClick}
              >
                <i className="ri-menu-line text-2xl"></i>
              </button>
            ) : (
              /* Logo for non-dashboard pages */
              <div
                className="flex items-center cursor-pointer"
                onClick={() => {
                  if (isDashboard || isLoginPage || isSignUpPage) return;
                  navigate("/");
                }}
              >
                <img
                  src="/logo.png"
                  alt="Lavoo"
                  className="h-[150px] sm:h-[200px] w-auto object-contain"
                />
                {/* Removed text and icon as requested to replace with logo image */}
              </div>
            )}

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-6 lg:space-x-8">
              {!isLoggedIn && !isDashboard && location.pathname !== '/' && (
                <>
                  <button
                    onClick={() => navigate("/")}
                    className="text-gray-700 hover:text-orange-500 font-medium transition-colors whitespace-nowrap"
                  >
                    Home
                  </button>
                </>
              )}

              {/* Dashboard navigation for logged-in users */}
              {isLoggedIn && isDashboard && !isAdmin && (
                <>
                  {/* Notification Bell */}
                  <div className="relative" ref={notificationRef}>
                    <button
                      onClick={handleNotificationClick}
                      className="p-2 text-gray-600 hover:text-orange-500 transition-colors relative"
                    >
                      <i className="ri-notification-3-line text-xl"></i>
                      {unreadCount > 0 && (
                        <span className="absolute top-0 right-0 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white transform translate-x-1/4 -translate-y-1/4 bg-red-500 rounded-full">
                          {unreadCount}
                        </span>
                      )}
                    </button>

                    {/* Notification Popover */}
                    {isNotificationsOpen && (
                      <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-200 origin-top-right">
                        <div className="px-4 py-3 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                          <h3 className="font-semibold text-gray-900">Notifications</h3>
                          {/* <span className="text-xs text-gray-500">Mark all as read</span> */}
                        </div>
                        <div className="max-h-96 overflow-y-auto">
                          {notifications.length === 0 ? (
                            <div className="px-4 py-6 text-center text-gray-500 text-sm">
                              No notifications
                            </div>
                          ) : (
                            <div className="divide-y divide-gray-100">
                              {notifications.map((notification) => (
                                <div key={notification.id} className={`px-4 py-3 hover:bg-gray-50 transition-colors ${!notification.read ? 'bg-orange-50/30' : ''}`}>
                                  <div className="flex items-start">
                                    <div className="flex-shrink-0 mt-1">
                                      <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600">
                                        <i className="ri-information-line text-sm"></i>
                                      </div>
                                    </div>
                                    <div className="ml-3 w-0 flex-1">
                                      <p className="text-sm font-medium text-gray-900">{notification.title}</p>
                                      <p className="mt-1 text-sm text-gray-500">{notification.message}</p>
                                      <p className="mt-1 text-xs text-gray-400">{notification.time}</p>
                                    </div>
                                    {!notification.read && (
                                      <div className="flex-shrink-0 ml-2">
                                        <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                          <button className="text-xs text-orange-600 hover:text-orange-700 font-medium w-full text-center">
                            View all notifications
                          </button>
                        </div>
                      </div>
                    )}
                  </div>


                  <button
                    onClick={() => scrollToSection("features")}
                    className="text-gray-700 hover:text-orange-500 font-medium transition-colors whitespace-nowrap"
                  >
                    <i className="ri-play-circle-line mr-2"></i>
                    Watch a Demo
                  </button>

                </>
              )}

              {/* Show login/signup if NOT logged in and NOT on dashboard */}
              {!isAnalyzePage && !isLoggedIn && !isDashboard && (
                <>
                  {(!isLoginPage || isAdmin) && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate("/login")}
                      className="whitespace-nowrap"
                    >
                      Log In
                    </Button>
                  )}
                  {(!isSignUpPage || isAdmin) && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => navigate("/signup")}
                      className="whitespace-nowrap"
                    >
                      Sign Up
                    </Button>
                  )}
                </>
              )}

              {/* Show user dropdown if logged in */}
              {isLoggedIn && !isLoading && (
                <div className="relative">
                  <button
                    onClick={() => setIsDropdownOpen((prev) => !prev)}
                    className="flex items-center space-x-2 bg-gray-100 px-3 py-1.5 rounded-lg hover:bg-gray-200 transition"
                  >
                    <i className="ri-user-line text-gray-700"></i>
                    <span className="font-medium text-gray-800">
                      {user?.name || user?.email}
                    </span>
                    <i
                      className={`ri-arrow-down-s-line transition-transform ${isDropdownOpen ? "rotate-180" : ""
                        }`}
                    ></i>
                  </button>

                  {isDropdownOpen && (
                    <div className="absolute right-0 mt-2 w-40 bg-white border rounded-lg shadow-md py-2">
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
                      >
                        Logout
                      </button>
                      <div>
                        <button className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
                          onClick={() => navigate('/dashboard/profile')}>
                          Profile
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </nav>

            {/* Mobile Menu Button */}
            {/* <button
            className="md:hidden p-2 text-gray-700 hover:text-orange-500 transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            <i
              className={`${
                isMobileMenuOpen ? "ri-close-line" : "ri-menu-line"
              } text-2xl`}
            ></i>
          </button> */}
          </div>
        </div>
      </header>
    );

  return null;
}

