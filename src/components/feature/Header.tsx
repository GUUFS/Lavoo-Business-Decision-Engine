import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Cookies from "js-cookie";

import Button from "../base/Button";
import { useCurrentUser } from "../../api/user";

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const { data: user, isLoading } = useCurrentUser();

  const isLoggedIn = !!user;
  const isAnalyzePage = location.pathname === "/analyze";
  const isLoginPage = location.pathname === "/login";
  const isSignUpPage = location.pathname === "/signup";

  const handleLogout = () => {
    Cookies.remove("access_token");
    navigate("/login", { replace: true });
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

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-20">
          {/* Logo */}
          <div
            className="flex items-center cursor-pointer"
            onClick={() => navigate("/")}
          >
            <div className="w-8 h-8 sm:w-10 sm:h-10 bg-orange-500 rounded-lg flex items-center justify-center mr-2 sm:mr-3">
              <i className="ri-brain-line text-white text-lg sm:text-xl"></i>
            </div>
            <span className="text-lg sm:text-xl font-bold text-black">
              AItugo+
            </span>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6 lg:space-x-8">
            {(isLoginPage || isSignUpPage) ? (
              <button
                onClick={() => navigate("/")}
                className="text-gray-700 hover:text-orange-500 font-medium transition-colors whitespace-nowrap"
              >
                Home
              </button>
            ) : (
              <button
                onClick={() => scrollToSection("features")}
                className="text-gray-700 hover:text-orange-500 font-medium transition-colors whitespace-nowrap"
              >
                Features
              </button>
            )}
            <button
              onClick={() => scrollToSection("blog")}
              className="text-gray-700 hover:text-orange-500 font-medium transition-colors whitespace-nowrap"
            >
              Blog
            </button>

            {/* Show login/signup if NOT logged in */}
            {!isAnalyzePage && !isLoggedIn && (
              <>
                {!isLoginPage && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate("/login")}
                    className="whitespace-nowrap"
                  >
                    Log In
                  </Button>
                )}
                {!isSignUpPage && (
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
                    className={`ri-arrow-down-s-line transition-transform ${
                      isDropdownOpen ? "rotate-180" : ""
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
                  </div>
                )}
              </div>
            )}
          </nav>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-gray-700 hover:text-orange-500 transition-colors"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            <i
              className={`${
                isMobileMenuOpen ? "ri-close-line" : "ri-menu-line"
              } text-2xl`}
            ></i>
          </button>
        </div>
      </div>
    </header>
  );
}