import { useState, useEffect } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';
import AdminHeader from '../../../components/feature/AdminHeader';
import Toast from '../../../components/ui/Toast';
import { getAuthHeaders } from '../../../utils/auth';

interface SystemSettings {
  site_name: string;
  support_email: string;
  default_language: string;
  timezone: string;
  max_analyses_basic: number;
  max_analyses_pro: number;
  max_analyses_premium: number;
  primary_ai_model: string;
  analysis_timeout: number;
  max_tokens: number;
  temperature: number;
  enable_predictive_analytics: boolean;
  generate_recommendations: boolean;
  include_confidence_scores: boolean;
  enable_experimental_features: boolean;
  require_mfa_admin: boolean;
  force_password_reset_90: boolean;
  lock_accounts_after_failed_attempts: boolean;
  data_retention_days: number;
  backup_frequency: string;
  monthly_price: number;
  yearly_price: number;
}

const defaultSettings: SystemSettings = {
  site_name: "AI Business Intelligence Analyst",
  support_email: "support@aianalyst.com",
  default_language: "en",
  timezone: "UTC",
  max_analyses_basic: 10,
  max_analyses_pro: 50,
  max_analyses_premium: 200,
  primary_ai_model: "gpt-4",
  analysis_timeout: 300,
  max_tokens: 4000,
  temperature: 0.7,
  enable_predictive_analytics: true,
  generate_recommendations: true,
  include_confidence_scores: true,
  enable_experimental_features: false,
  require_mfa_admin: false,
  force_password_reset_90: false,
  lock_accounts_after_failed_attempts: true,
  data_retention_days: 365,
  backup_frequency: "daily",
  monthly_price: 29.95,
  yearly_price: 290.00
};

export default function AdminSettings() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState<SystemSettings>(defaultSettings);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editSection, setEditSection] = useState<'general' | 'ai' | 'security' | null>(null);
  const [formData, setFormData] = useState<SystemSettings>(defaultSettings);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/control/settings`, {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        const merged = { ...defaultSettings, ...data }; // Ensure all fields exist
        setSettings(merged);
        setFormData(merged);
      }
    } catch (error) {
      console.error("Error fetching settings:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (section: 'general' | 'ai' | 'security') => {
    setEditSection(section);
    setFormData({ ...settings }); // Load current settings
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditSection(null);
  };

  const handleChange = (field: keyof SystemSettings, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (isBilling = false) => {
    try {
      // If billing, we save 'formData' which might just be updated from inputs
      // Check if billing is calling this directly
      const dataToSend = isBilling ? settings : formData;

      const response = await fetch(`${API_BASE_URL}/api/control/settings`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(dataToSend)
      });

      if (response.ok) {
        const updated = await response.json();
        setSettings(updated);
        if (!isBilling) handleCloseModal();
        setToast({ message: isBilling ? "Pricing updated successfully!" : "Settings updated successfully!", type: 'success' });
      } else {
        setToast({ message: "Failed to update settings", type: 'error' });
      }
    } catch (error) {
      console.error("Error updating settings:", error);
      setToast({ message: "Error updating settings", type: 'error' });
    }
  };

  // Billing specific handler for direct input changes
  const handleBillingChange = (field: keyof SystemSettings, value: any) => {
    setSettings(prev => ({ ...prev, [field]: value }));
  };

  const tabs = [
    { id: 'general', label: 'General', icon: 'ri-settings-line' },
    { id: 'ai', label: 'AI Configuration', icon: 'ri-robot-line' },
    { id: 'billing', label: 'Billing', icon: 'ri-money-dollar-circle-line' },
    { id: 'integrations', label: 'Integrations', icon: 'ri-plug-line' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
      <AdminSidebar
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />

      <div className="flex-1 flex flex-col">
        <AdminHeader setIsMobileMenuOpen={setIsMobileMenuOpen} />

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
                <nav className="flex space-x-8 px-6 overflow-x-auto" aria-label="Tabs">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${activeTab === tab.id
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
                {loading ? (
                  <div className="text-center py-10">Loading settings...</div>
                ) : (
                  <>
                    {/* General Settings */}
                    {activeTab === 'general' && (
                      <div className="space-y-6">
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900 mb-4">Platform Configuration</h3>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4 bg-gray-50 rounded-lg">
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Platform Name</label>
                              <p className="text-gray-900 font-medium">{settings.site_name}</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Support Email</label>
                              <p className="text-gray-900 font-medium">{settings.support_email}</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Default Language</label>
                              <p className="text-gray-900 font-medium">{settings.default_language === 'en' ? 'English' : settings.default_language}</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Timezone</label>
                              <p className="text-gray-900 font-medium">{settings.timezone}</p>
                            </div>
                          </div>
                        </div>

                        <div>
                          <h3 className="text-lg font-semibold text-gray-900 mb-4">User Limits</h3>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 bg-gray-50 rounded-lg">
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Basic Users Limit</label>
                              <p className="text-gray-900 font-medium">{settings.max_analyses_basic} analyses</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Pro Users Limit</label>
                              <p className="text-gray-900 font-medium">{settings.max_analyses_pro} analyses</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Premium Users Limit</label>
                              <p className="text-gray-900 font-medium">{settings.max_analyses_premium} analyses</p>
                            </div>
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <button
                            onClick={() => handleOpenModal('general')}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap"
                          >
                            Edit System
                          </button>
                        </div>
                      </div>
                    )}

                    {/* AI Configuration */}
                    {activeTab === 'ai' && (
                      <div className="space-y-6">
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Model Settings</h3>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-4 bg-gray-50 rounded-lg">
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Primary Model</label>
                              <p className="text-gray-900 font-medium">{settings.primary_ai_model}</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Timeout</label>
                              <p className="text-gray-900 font-medium">{settings.analysis_timeout}s</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Max Tokens</label>
                              <p className="text-gray-900 font-medium">{settings.max_tokens}</p>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-500 mb-1">Temperature</label>
                              <p className="text-gray-900 font-medium">{settings.temperature}</p>
                            </div>
                          </div>
                        </div>

                        <div>
                          <h3 className="text-lg font-semibold text-gray-900 mb-4">Feature Flags</h3>
                          <div className="space-y-2 p-4 bg-gray-50 rounded-lg">
                            <div className="flex items-center">
                              <i className={`ri-checkbox-${settings.enable_predictive_analytics ? 'circle-fill text-green-500' : 'blank-circle-line text-gray-400'} mr-2`}></i>
                              <span>Predictive Analytics</span>
                            </div>
                            <div className="flex items-center">
                              <i className={`ri-checkbox-${settings.generate_recommendations ? 'circle-fill text-green-500' : 'blank-circle-line text-gray-400'} mr-2`}></i>
                              <span>Recommendations</span>
                            </div>
                            <div className="flex items-center">
                              <i className={`ri-checkbox-${settings.include_confidence_scores ? 'circle-fill text-green-500' : 'blank-circle-line text-gray-400'} mr-2`}></i>
                              <span>Confidence Scores</span>
                            </div>
                            <div className="flex items-center">
                              <i className={`ri-checkbox-${settings.enable_experimental_features ? 'circle-fill text-green-500' : 'blank-circle-line text-gray-400'} mr-2`}></i>
                              <span>Experimental Features</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <button
                            onClick={() => handleOpenModal('ai')}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap"
                          >
                            Edit AI Settings
                          </button>
                        </div>
                      </div>
                    )}



                    {/* Billing Settings */}
                    {activeTab === 'billing' && (
                      <div className="space-y-6">
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900 mb-4">Pricing Configuration</h3>
                          <div className="max-w-md">
                            <div className="border border-gray-200 rounded-lg p-6">
                              <h4 className="font-medium text-gray-900 mb-4">Standard Pricing</h4>
                              <div className="space-y-4">
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-2">Monthly Price ($)</label>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={settings.monthly_price}
                                    onChange={(e) => handleBillingChange('monthly_price', parseFloat(e.target.value))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                                  />
                                </div>
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 mb-2">Yearly Price ($)</label>
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={settings.yearly_price}
                                    onChange={(e) => handleBillingChange('yearly_price', parseFloat(e.target.value))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div className="flex justify-end">
                          <button
                            onClick={() => handleSave(true)}
                            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors whitespace-nowrap"
                          >
                            Update Pricing
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Integrations (Kept as is) */}
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
                            {/* ... other items kept static for now ... */}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Maintenance (Kept as is) */}
                    {activeTab === 'maintenance' && (
                      <div className="space-y-6">
                        {/* Maintenance content... */}
                        <div className="text-center p-10 text-gray-500">Maintenance options available</div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-900">
                {editSection === 'general' ? 'Edit System Settings' :
                  editSection === 'ai' ? 'Edit AI Configuration' : 'Edit Security Settings'}
              </h3>
              <button onClick={handleCloseModal} className="text-gray-400 hover:text-gray-600">
                <i className="ri-close-line text-2xl"></i>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {editSection === 'general' && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Platform Name</label>
                      <input type="text" value={formData.site_name} onChange={e => handleChange('site_name', e.target.value)} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Support Email</label>
                      <input type="email" value={formData.support_email} onChange={e => handleChange('support_email', e.target.value)} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Default Language</label>
                      <select value={formData.default_language} onChange={e => handleChange('default_language', e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                        <option value="en">English</option>
                        <option value="es">Spanish</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
                      <select value={formData.timezone} onChange={e => handleChange('timezone', e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                        <option value="UTC">UTC</option>
                        <option value="EST">Eastern Time</option>
                      </select>
                    </div>
                  </div>
                  <h4 className="font-semibold mt-4 mb-2">Limits</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Basic Limit</label>
                      <input type="number" value={formData.max_analyses_basic} onChange={e => handleChange('max_analyses_basic', parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Pro Limit</label>
                      <input type="number" value={formData.max_analyses_pro} onChange={e => handleChange('max_analyses_pro', parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Premium Limit</label>
                      <input type="number" value={formData.max_analyses_premium} onChange={e => handleChange('max_analyses_premium', parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                  </div>
                </>
              )}

              {editSection === 'ai' && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Primary Model</label>
                      <select value={formData.primary_ai_model} onChange={e => handleChange('primary_ai_model', e.target.value)} className="w-full px-3 py-2 border rounded-lg">
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (s)</label>
                      <input type="number" value={formData.analysis_timeout} onChange={e => handleChange('analysis_timeout', parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Max Tokens</label>
                      <input type="number" value={formData.max_tokens} onChange={e => handleChange('max_tokens', parseInt(e.target.value))} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                      <input type="number" step="0.1" value={formData.temperature} onChange={e => handleChange('temperature', parseFloat(e.target.value))} className="w-full px-3 py-2 border rounded-lg" />
                    </div>
                  </div>
                  <div className="space-y-3 mt-4">
                    <label className="flex items-center">
                      <input type="checkbox" checked={formData.enable_predictive_analytics} onChange={e => handleChange('enable_predictive_analytics', e.target.checked)} className="rounded text-red-600" />
                      <span className="ml-2">Enable Predictive Analytics</span>
                    </label>
                    <label className="flex items-center">
                      <input type="checkbox" checked={formData.generate_recommendations} onChange={e => handleChange('generate_recommendations', e.target.checked)} className="rounded text-red-600" />
                      <span className="ml-2">Generate Recommendations</span>
                    </label>
                    <label className="flex items-center">
                      <input type="checkbox" checked={formData.include_confidence_scores} onChange={e => handleChange('include_confidence_scores', e.target.checked)} className="rounded text-red-600" />
                      <span className="ml-2">Include Confidence Scores</span>
                    </label>
                    <label className="flex items-center">
                      <input type="checkbox" checked={formData.enable_experimental_features} onChange={e => handleChange('enable_experimental_features', e.target.checked)} className="rounded text-red-600" />
                      <span className="ml-2">Enable Experimental Features</span>
                    </label>
                  </div>
                </>
              )}


            </div>

            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Close
              </button>
              <button
                onClick={() => handleSave(false)}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Update
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}