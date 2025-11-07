
import { useNavigate } from 'react-router-dom';

export default function Footer() {
  const navigate = useNavigate();

  return (
    <footer className="bg-gradient-to-br from-orange-50 to-white text-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12 md:py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 sm:gap-10 lg:gap-12">
          {/* Company Info */}
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="flex items-center mb-4 sm:mb-6">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-orange-500 rounded-lg flex items-center justify-center mr-2 sm:mr-3">
                <i className="ri-brain-line text-white text-lg sm:text-xl"></i>
              </div>
              <span className="text-lg sm:text-xl font-bold">AI Strategy</span>
            </div>
            <p className="text-sm sm:text-base text-gray-600 leading-relaxed mb-4 sm:mb-6">
              Transform your business with AI-powered insights and personalized tool recommendations.
            </p>
            <div className="flex space-x-4">
              <button className="w-9 h-9 sm:w-10 sm:h-10 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-orange-500 hover:text-white hover:border-orange-500 transition-colors">
                <i className="ri-twitter-fill text-base sm:text-lg"></i>
              </button>
              <button className="w-9 h-9 sm:w-10 sm:h-10 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-orange-500 hover:text-white hover:border-orange-500 transition-colors">
                <i className="ri-linkedin-fill text-base sm:text-lg"></i>
              </button>
              <button className="w-9 h-9 sm:w-10 sm:h-10 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-orange-500 hover:text-white hover:border-orange-500 transition-colors">
                <i className="ri-facebook-fill text-base sm:text-lg"></i>
              </button>
              <button className="w-9 h-9 sm:w-10 sm:h-10 bg-white border border-gray-200 rounded-lg flex items-center justify-center hover:bg-orange-500 hover:text-white hover:border-orange-500 transition-colors">
                <i className="ri-instagram-fill text-base sm:text-lg"></i>
              </button>
            </div>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-base sm:text-lg font-bold mb-3 sm:mb-4">Product</h3>
            <ul className="space-y-2 sm:space-y-3">
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Features
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Pricing
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Case Studies
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Reviews
                </button>
              </li>
            </ul>
          </div>

          {/* Company */}
          <div>
            <h3 className="text-base sm:text-lg font-bold mb-3 sm:mb-4">Company</h3>
            <ul className="space-y-2 sm:space-y-3">
            <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  About Us
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:textorange-500 transition-colors">
                  Careers
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Blog
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Contact
                </button>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h3 className="text-base sm:text-lg font-bold mb-3 sm:mb-4">Resources</h3>
            <ul className="space-y-2 sm:space-y-3">
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Documentation
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Help Center
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  Community
                </button>
              </li>
              <li>
                <button className="text-sm sm:text-base text-gray-600 hover:text-orange-500 transition-colors">
                  API
                </button>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-gray-200 mt-10 sm:mt-12 pt-6 sm:pt-8">
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <p className="text-xs sm:text-sm text-gray-600 text-center sm:text-left">
              © {new Date().getFullYear()} AItugo+. All rights reserved.
            </p>
            <div className="flex flex-wrap justify-center gap-4 sm:gap-6">
              <a 
                href="#" 
                className="text-xs sm:text-sm text-orange-500 hover:text-orange-400 transition-colors whitespace-nowrap"
              >
                Powered by GUUFS
              </a>
            </div>
          </div>
        </div>

      </div>
    </footer>
  );
}


