import { useState } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminSettings() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  const tabs = [
    { id: 'general', label: 'General', icon: 'ri-settings-line' },
    { id: 'ai', label: 'AI Configuration', icon: 'ri-robot-line' },
    { id: 'security', label: 'Security', icon: 'ri-shield-line' },
    { id: 'billing', label: 'Billing', icon: 'ri-money-dollar-circle-line' },
    { id: 'integrations', label: 'Integrations', icon: 'ri-plug-line' },
    { id: 'maintenance', label: 'Maintenance', icon: 'ri-tools-line' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />
      
      <div className="flex-1 flex flex-col">
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
              <button className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <i className="ri-user-line text-red-600"></i>
                </div>
                <span className="font-medium text-gray-900">Admin User</span>
                <i className="ri-arrow-down-s-line text-gray-400"></i>
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">System Settings</h1>
              <p className="text-gray-600">Configure platform settings, AI parameters, and system preferences</p>
            </div>

            {/* Tabs */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
              <div className="border-b border-gray-200">
                <nav className="flex space-x-8 px-6" aria-label="Tabs">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                        activeTab === tab.id
                          ? 'border-red-500 text-red-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <i className={`${tab.icon} mr-2`}></i>
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>

              <div className="p-6">
                {/* General Settings */}
                {activeTab === 'general' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Platform Configuration</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Platform Name</label>
                          <input
                            type="text"
                            defaultValue="AI Business Intelligence Analyst"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Support Email</label>
                          <input
                            type="email"
                            defaultValue="support@aianalyst.com"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Default Language</label>
                          <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8">
                            <option value="en">English</option>
                            <option value="es">Spanish</option>
                            <option value="fr">French</option>
                            <option value="de">German</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Timezone</label>
                          <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8">
                            <option value="UTC">UTC</option>
                            <option value="EST">Eastern Time</option>
                            <option value="PST">Pacific Time</option>
                            <option value="GMT">Greenwich Mean Time</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">User Limits</h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Max Analyses per User (Basic)</label>
                          <input
                            type="number"
                            defaultValue="10"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Max Analyses per User (Pro)</label>
                          <input
                            type="number"
                            defaultValue="50"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Max Analyses per User (Premium)</label>
                          <input
                            type="number"
                            defaultValue="200"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <button className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                        Save Changes
                      </button>
                    </div>
                  </div>
                )}

                {/* AI Configuration */}
                {activeTab === 'ai' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Model Settings</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Primary AI Model</label>
                          <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8">
                            <option value="gpt-4">GPT-4</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            <option value="claude-3">Claude 3</option>
                            <option value="gemini-pro">Gemini Pro</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Analysis Timeout (seconds)</label>
                          <input
                            type="number"
                            defaultValue="300"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Max Tokens per Analysis</label>
                          <input
                            type="number"
                            defaultValue="4000"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Temperature</label>
                          <input
                            type="number"
                            step="0.1"
                            min="0"
                            max="2"
                            defaultValue="0.7"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Analysis Features</h3>
                      <div className="space-y-4">
                        <label className="flex items-center">
                          <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Enable predictive analytics</span>
                        </label>
                        <label className="flex items-center">
                          <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Generate actionable recommendations</span>
                        </label>
                        <label className="flex items-center">
                          <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Include confidence scores</span>
                        </label>
                        <label className="flex items-center">
                          <input type="checkbox" className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Enable experimental features</span>
                        </label>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <button className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                        Save AI Settings
                      </button>
                    </div>
                  </div>
                )}

                {/* Security Settings */}
                {activeTab === 'security' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Authentication</h3>
                      <div className="space-y-4">
                        <label className="flex items-center">
                          <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Require two-factor authentication for admin accounts</span>
                        </label>
                        <label className="flex items-center">
                          <input type="checkbox" className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Force password reset every 90 days</span>
                        </label>
                        <label className="flex items-center">
                          <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                          <span className="ml-2 text-sm text-gray-700">Lock accounts after 5 failed login attempts</span>
                        </label>
                      </div>
                    </div>

                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Protection</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Data Retention Period (days)</label>
                          <input
                            type="number"
                            defaultValue="365"
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Backup Frequency</label>
                          <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8">
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <button className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                        Save Security Settings
                      </button>
                    </div>
                  </div>
                )}

                {/* Billing Settings */}
                {activeTab === 'billing' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Subscription Plan</h3>
                      <div className="max-w-md">
                        <div className="border border-gray-200 rounded-lg p-6">
                          <h4 className="font-medium text-gray-900 mb-4">Premium Plan</h4>
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">Monthly Price ($)</label>
                              <input
                                type="number"
                                defaultValue="149"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">Analyses Limit</label>
                              <input
                                type="number"
                                defaultValue="200"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">Features</label>
                              <div className="space-y-2">
                                <label className="flex items-center">
                                  <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                                  <span className="ml-2 text-sm text-gray-700">Advanced AI Analysis</span>
                                </label>
                                <label className="flex items-center">
                                  <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                                  <span className="ml-2 text-sm text-gray-700">Priority Support</span>
                                </label>
                                <label className="flex items-center">
                                  <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                                  <span className="ml-2 text-sm text-gray-700">Custom Reports</span>
                                </label>
                                <label className="flex items-center">
                                  <input type="checkbox" defaultChecked className="rounded border-gray-300 text-red-600 focus:ring-red-500" />
                                  <span className="ml-2 text-sm text-gray-700">API Access</span>
                                </label>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <button className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                        Update Pricing
                      </button>
                    </div>
                  </div>
                )}

                {/* Integrations */}
                {activeTab === 'integrations' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Third-party Integrations</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900">Stripe Payment Gateway</h4>
                            <span className="px-2 py-1 bg-green-100 text-green-600 text-xs rounded-full">Connected</span>
                          </div>
                          <p className="text-sm text-gray-600 mb-3">Process subscription payments and manage billing</p>
                          <button className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200 transition-colors whitespace-nowrap">
                            Configure
                          </button>
                        </div>
                        <div className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900">SendGrid Email</h4>
                            <span className="px-2 py-1 bg-green-100 text-green-600 text-xs rounded-full">Connected</span>
                          </div>
                          <p className="text-sm text-gray-600 mb-3">Send transactional emails and notifications</p>
                          <button className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded hover:bg-gray-200 transition-colors whitespace-nowrap">
                            Configure
                          </button>
                        </div>
                        <div className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900">Slack Notifications</h4>
                            <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">Not Connected</span>
                          </div>
                          <p className="text-sm text-gray-600 mb-3">Send alerts and notifications to Slack channels</p>
                          <button className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors whitespace-nowrap">
                            Connect
                          </button>
                        </div>
                        <div className="border border-gray-200 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="font-medium text-gray-900">Google Analytics</h4>
                            <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">Not Connected</span>
                          </div>
                          <p className="text-sm text-gray-600 mb-3">Track user behavior and platform analytics</p>
                          <button className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors whitespace-nowrap">
                            Connect
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Maintenance */}
                {activeTab === 'maintenance' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">System Maintenance</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="border border-gray-200 rounded-lg p-4">
                          <h4 className="font-medium text-gray-900 mb-2">Database Cleanup</h4>
                          <p className="text-sm text-gray-600 mb-3">Remove old analysis data and optimize database performance</p>
                          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap">
                            Run Cleanup
                          </button>
                        </div>
                        <div className="border border-gray-200 rounded-lg p-4">
                          <h4 className="font-medium text-gray-900 mb-2">Cache Clear</h4>
                          <p className="text-sm text-gray-600 mb-3">Clear system cache to improve performance</p>
                          <button className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors whitespace-nowrap">
                            Clear Cache
                          </button>
                        </div>
                        <div className="border border-gray-200 rounded-lg p-4">
                          <h4 className="font-medium text-gray-900 mb-2">System Backup</h4>
                          <p className="text-sm text-gray-600 mb-3">Create a full system backup</p>
                          <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors whitespace-nowrap">
                            Start Backup
                          </button>
                        </div>
                        <div className="border border-gray-200 rounded-lg p-4">
                          <h4 className="font-medium text-gray-900 mb-2">Maintenance Mode</h4>
                          <p className="text-sm text-gray-600 mb-3">Enable maintenance mode for system updates</p>
                          <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap">
                            Enable Mode
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}