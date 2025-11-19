
import { useState } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import { useCurrentUser } from "../../../api/user";

export default function ProfilePage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { data: user, isLoading } = useCurrentUser();

  return (
    <div className="min-h-screen bg-gray-50 flex min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
      <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Profile Settings</h1>
              <p className="text-gray-600">Manage your account information and preferences</p>
            </div>

            {/* Profile Form */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              {/* Profile Header */}
              <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-6 py-8 md:px-8 md:py-12">
                <div className="flex flex-col md:flex-row items-center gap-6">
                  <div className="w-20 h-20 md:w-24 md:h-24 bg-white rounded-full flex items-center justify-center">
                    <i className="ri-user-line text-3xl md:text-4xl text-orange-500"></i>
                  </div>
                  <div className="text-center md:text-left">
                    <h2 className="text-xl md:text-2xl font-bold text-white mb-2">{user?.name}</h2>
                    <p className="text-orange-100 mb-3">Premium Member since March 2024</p>
                    <button className="bg-white text-orange-600 px-4 py-2 rounded-lg font-medium hover:bg-orange-50 transition-colors whitespace-nowrap">
                      Change Photo
                    </button>
                  </div>
                </div>
              </div>

              {/* Form Content */}
              <div className="p-6 md:p-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Personal Information */}
                  <div className="md:col-span-2">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Personal Information</h3>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                    <input
                      type="text"
                      defaultValue={user?.name.split(" ")[0]}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                    <input
                      type="text"
                      defaultValue={user?.name.split(" ")[1]}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                    <input
                      type="email"
                      defaultValue={user?.email}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                    <input
                      type="tel"
                      defaultValue="+1 (555) 123-4567"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Company</label>
                    <input
                      type="text"
                      defaultValue="TechCorp Inc."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                    />
                  </div>

                  {/* Account Settings */}
                  <div className="md:col-span-2 mt-8">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Account Settings</h3>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Bio</label>
                    <textarea
                      rows={4}
                      defaultValue="AI Strategy enthusiast with 10+ years of experience in business transformation and digital innovation."
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors resize-none"
                    />
                  </div>

                  {/* Notification Preferences */}
                  <div className="md:col-span-2 mt-6">
                    <h4 className="text-base font-medium text-gray-900 mb-4">Notification Preferences</h4>
                    <div className="space-y-4">
                      <label className="flex items-center">
                        <input type="checkbox" defaultChecked className="w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500" />
                        <span className="ml-3 text-sm text-gray-700">Email notifications for new insights</span>
                      </label>
                      <label className="flex items-center">
                        <input type="checkbox" defaultChecked className="w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500" />
                        <span className="ml-3 text-sm text-gray-700">Weekly performance reports</span>
                      </label>
                      <label className="flex items-center">
                        <input type="checkbox" className="w-4 h-4 text-orange-600 border-gray-300 rounded focus:ring-orange-500" />
                        <span className="ml-3 text-sm text-gray-700">Marketing updates and promotions</span>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-4 mt-8 pt-6 border-t border-gray-200">
                  <button className="bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                    Save Changes
                  </button>
                  <button className="border border-gray-300 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                    Cancel
                  </button>
                  <button className="text-red-600 px-6 py-3 rounded-lg font-medium hover:bg-red-50 transition-colors whitespace-nowrap sm:ml-auto">
                    Deactivate Account
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
    </div>
  );
}
