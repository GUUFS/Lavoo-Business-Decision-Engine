
import { useState } from 'react';
import AdminSidebar from '../../../components/feature/AdminSidebar';

export default function AdminContentManagement() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('insights');

  // Form states for each tab
  const [insightForm, setInsightForm] = useState({
    title: '',
    industry: '',
    priority: 'medium',
    whatChanged: '',
    whyItMatters: '',
    actionToTake: ''
  });

  const [alertForm, setAlertForm] = useState({
    priority: 'medium',
    whyActNow: '',
    title: '',
    potentialReward: '',
    actionRequired: '',
    industry: '',
    score: ''
  });

  const [trendForm, setTrendForm] = useState({
    title: '',
    industry: '',
    nature: '',
    score: '',
    hashtags: '',
    searchVolume: '',
    opportunity: '',
    description: '',
    actionItems: ''
  });

  const handleInsightSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Insight submitted:', insightForm);
    // Reset form
    setInsightForm({
      title: '',
      industry: '',
      priority: 'medium',
      whatChanged: '',
      whyItMatters: '',
      actionToTake: ''
    });
    alert('Insight uploaded successfully!');
  };

  const handleAlertSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Alert submitted:', alertForm);
    // Reset form
    setAlertForm({
      priority: 'medium',
      whyActNow: '',
      title: '',
      potentialReward: '',
      actionRequired: '',
      industry: '',
      score: ''
    });
    alert('Alert uploaded successfully!');
  };

  const handleTrendSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Trend submitted:', trendForm);
    // Reset form
    setTrendForm({
      title: '',
      industry: '',
      nature: '',
      score: '',
      hashtags: '',
      searchVolume: '',
      opportunity: '',
      description: '',
      actionItems: ''
    });
    alert('Trend uploaded successfully!');
  };

  const tabs = [
    { id: 'insights', label: 'Insights', icon: 'ri-lightbulb-line' },
    { id: 'alerts', label: 'Alerts', icon: 'ri-alarm-line' },
    { id: 'trends', label: 'Trends', icon: 'ri-trending-up-line' }
  ];

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
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Content Management</h1>
              <p className="text-gray-600">Upload and manage insights, alerts, and viral trends</p>
            </div>

            {/* Tabs */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-6">
              <div className="border-b border-gray-200">
                <nav className="flex space-x-8 px-6">
                  {tabs.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 transition-colors ${
                        activeTab === tab.id
                          ? 'border-red-500 text-red-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <i className={`${tab.icon} text-lg`}></i>
                      {tab.label}
                    </button>
                  ))}
                </nav>
              </div>

              <div className="p-6">
                {/* Insights Form */}
                {activeTab === 'insights' && (
                  <form onSubmit={handleInsightSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Insight Title
                        </label>
                        <input
                          type="text"
                          value={insightForm.title}
                          onChange={(e) => setInsightForm({...insightForm, title: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="Enter insight title"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Industry
                        </label>
                        <select
                          value={insightForm.industry}
                          onChange={(e) => setInsightForm({...insightForm, industry: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                          required
                        >
                          <option value="">Select industry</option>
                          <option value="technology">Technology</option>
                          <option value="healthcare">Healthcare</option>
                          <option value="finance">Finance</option>
                          <option value="retail">Retail</option>
                          <option value="manufacturing">Manufacturing</option>
                          <option value="education">Education</option>
                          <option value="real-estate">Real Estate</option>
                          <option value="automotive">Automotive</option>
                          <option value="entertainment">Entertainment</option>
                          <option value="food-beverage">Food & Beverage</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Priority
                      </label>
                      <select
                        value={insightForm.priority}
                        onChange={(e) => setInsightForm({...insightForm, priority: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                      >
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        What Changed
                      </label>
                      <textarea
                        value={insightForm.whatChanged}
                        onChange={(e) => setInsightForm({...insightForm, whatChanged: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Describe what has changed in the industry or market"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Why It Matters
                      </label>
                      <textarea
                        value={insightForm.whyItMatters}
                        onChange={(e) => setInsightForm({...insightForm, whyItMatters: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Explain why this change is significant and its impact"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Action to Take
                      </label>
                      <textarea
                        value={insightForm.actionToTake}
                        onChange={(e) => setInsightForm({...insightForm, actionToTake: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Recommend specific actions businesses should take"
                        required
                      />
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="submit"
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium whitespace-nowrap"
                      >
                        Upload Insight
                      </button>
                    </div>
                  </form>
                )}

                {/* Alerts Form */}
                {activeTab === 'alerts' && (
                  <form onSubmit={handleAlertSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Priority
                        </label>
                        <select
                          value={alertForm.priority}
                          onChange={(e) => setAlertForm({...alertForm, priority: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                        >
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                          <option value="urgent">Urgent</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Title
                        </label>
                        <input
                          type="text"
                          value={alertForm.title}
                          onChange={(e) => setAlertForm({...alertForm, title: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="Enter alert title"
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Industry
                        </label>
                        <select
                          value={alertForm.industry}
                          onChange={(e) => setAlertForm({...alertForm, industry: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                          required
                        >
                          <option value="">Select industry</option>
                          <option value="technology">Technology</option>
                          <option value="healthcare">Healthcare</option>
                          <option value="finance">Finance</option>
                          <option value="retail">Retail</option>
                          <option value="manufacturing">Manufacturing</option>
                          <option value="education">Education</option>
                          <option value="real-estate">Real Estate</option>
                          <option value="automotive">Automotive</option>
                          <option value="entertainment">Entertainment</option>
                          <option value="food-beverage">Food & Beverage</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Score
                        </label>
                        <input
                          type="number"
                          value={alertForm.score}
                          onChange={(e) => setAlertForm({...alertForm, score: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="Enter score (0-100)"
                          min="0"
                          max="100"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Why Act Now
                      </label>
                      <textarea
                        value={alertForm.whyActNow}
                        onChange={(e) => setAlertForm({...alertForm, whyActNow: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Explain the urgency and time-sensitive nature"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Potential Reward
                      </label>
                      <textarea
                        value={alertForm.potentialReward}
                        onChange={(e) => setAlertForm({...alertForm, potentialReward: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Describe the potential benefits and rewards"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Action Required
                      </label>
                      <textarea
                        value={alertForm.actionRequired}
                        onChange={(e) => setAlertForm({...alertForm, actionRequired: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Specify the exact actions that need to be taken"
                        required
                      />
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="submit"
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium whitespace-nowrap"
                      >
                        Create Alert
                      </button>
                    </div>
                  </form>
                )}

                {/* Trends Form */}
                {activeTab === 'trends' && (
                  <form onSubmit={handleTrendSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Title
                        </label>
                        <input
                          type="text"
                          value={trendForm.title}
                          onChange={(e) => setTrendForm({...trendForm, title: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="Enter trend title"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Industry
                        </label>
                        <select
                          value={trendForm.industry}
                          onChange={(e) => setTrendForm({...trendForm, industry: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                          required
                        >
                          <option value="">Select industry</option>
                          <option value="technology">Technology</option>
                          <option value="healthcare">Healthcare</option>
                          <option value="finance">Finance</option>
                          <option value="retail">Retail</option>
                          <option value="manufacturing">Manufacturing</option>
                          <option value="education">Education</option>
                          <option value="real-estate">Real Estate</option>
                          <option value="automotive">Automotive</option>
                          <option value="entertainment">Entertainment</option>
                          <option value="food-beverage">Food & Beverage</option>
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Nature
                        </label>
                        <select
                          value={trendForm.nature}
                          onChange={(e) => setTrendForm({...trendForm, nature: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 pr-8"
                          required
                        >
                          <option value="">Select nature</option>
                          <option value="viral">Viral Content</option>
                          <option value="hashtag">Hashtag Trend</option>
                          <option value="challenge">Challenge</option>
                          <option value="meme">Meme</option>
                          <option value="topic">Topic Trend</option>
                          <option value="technology">Technology Trend</option>
                          <option value="social">Social Movement</option>
                          <option value="cultural">Cultural Shift</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Score
                        </label>
                        <input
                          type="number"
                          value={trendForm.score}
                          onChange={(e) => setTrendForm({...trendForm, score: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="Enter viral score (0-100)"
                          min="0"
                          max="100"
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Hashtags
                        </label>
                        <input
                          type="text"
                          value={trendForm.hashtags}
                          onChange={(e) => setTrendForm({...trendForm, hashtags: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="#hashtag1 #hashtag2 #hashtag3"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Search Volume
                        </label>
                        <input
                          type="text"
                          value={trendForm.searchVolume}
                          onChange={(e) => setTrendForm({...trendForm, searchVolume: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                          placeholder="e.g., 1.2M searches/month"
                          required
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Opportunity
                      </label>
                      <input
                        type="text"
                        value={trendForm.opportunity}
                        onChange={(e) => setTrendForm({...trendForm, opportunity: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="e.g., 85% opportunity score"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description
                      </label>
                      <textarea
                        value={trendForm.description}
                        onChange={(e) => setTrendForm({...trendForm, description: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="Describe the trend, its origin, and why it's gaining popularity"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Action Items
                      </label>
                      <textarea
                        value={trendForm.actionItems}
                        onChange={(e) => setTrendForm({...trendForm, actionItems: e.target.value})}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                        placeholder="List specific action items businesses can take to leverage this trend"
                        required
                      />
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="submit"
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium whitespace-nowrap"
                      >
                        Upload Trend
                      </button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
