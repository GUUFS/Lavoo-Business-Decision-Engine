
import { useState } from 'react';

export default function AlertsPage() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPriority, setSelectedPriority] = useState('all');

  const alerts = [
    {
      id: 1,
      title: "LinkedIn Algorithm Update Opportunity",
      category: "Market",
      priority: "High",
      score: 92,
      timeRemaining: "2 days",
      whyActNow: "LinkedIn's new algorithm favors video content and carousel posts. Early adopters are seeing 3x higher engagement rates. This window typically lasts 2-3 weeks before competition catches up.",
      potentialReward: "Increase LinkedIn engagement by 300%, generate 50+ qualified leads monthly, establish thought leadership in your industry. Estimated revenue impact: $15,000-25,000 monthly.",
      actionRequired: "Create 5 video posts and 3 carousel posts this week. Focus on industry insights and behind-the-scenes content. Use trending hashtags #IndustryInsights #Leadership #Innovation."
    },
    {
      id: 2,
      title: "Content Gap in AI Strategy Market",
      category: "Content",
      priority: "High",
      score: 88,
      timeRemaining: "5 days",
      whyActNow: "Competitor analysis shows 73% of businesses lack AI implementation guides. Search volume for 'AI strategy for small business' increased 340% this month with low competition.",
      potentialReward: "Capture 15-20% market share in AI consulting niche. Potential for $50,000+ in consulting revenue. Build authority as AI strategy expert in your industry.",
      actionRequired: "Publish comprehensive AI strategy guide within 5 days. Include case studies, implementation timeline, and ROI calculator. Optimize for keywords: 'AI strategy', 'business automation', 'AI implementation'."
    },
    {
      id: 3,
      title: "Customer Churn Risk Alert",
      category: "Customer",
      priority: "Medium",
      score: 76,
      timeRemaining: "1 week",
      whyActNow: "15 high-value customers showing decreased engagement (40% drop in platform usage). Historical data shows 78% churn probability within 30 days without intervention.",
      potentialReward: "Retain $45,000 in annual recurring revenue. Improve customer lifetime value by 25%. Strengthen customer relationships and reduce acquisition costs.",
      actionRequired: "Launch personalized re-engagement campaign. Schedule 1-on-1 calls with at-risk customers. Offer exclusive training session or premium feature access. Send within 48 hours."
    },
    {
      id: 4,
      title: "New AI Tool Early Access Program",
      category: "Technology",
      priority: "Medium",
      score: 84,
      timeRemaining: "3 days",
      whyActNow: "OpenAI's new business API offers 50% discount for early adopters. Limited to first 1,000 businesses. Tool can automate 60% of customer service tasks.",
      potentialReward: "Save $8,000 monthly on customer service costs. Improve response time by 75%. Access premium features at 50% discount for 12 months.",
      actionRequired: "Apply for early access program immediately. Prepare integration plan for customer service automation. Allocate 2 developers for 1-week implementation sprint."
    },
    {
      id: 5,
      title: "Competitor Pricing Strategy Shift",
      category: "Competitive",
      priority: "High",
      score: 90,
      timeRemaining: "4 days",
      whyActNow: "Main competitor increased prices by 35% effective next week. Market research shows 40% of their customers are actively seeking alternatives. Perfect timing to capture market share.",
      potentialReward: "Acquire 200-300 new customers within 60 days. Increase market share by 12%. Generate additional $180,000 in quarterly revenue.",
      actionRequired: "Launch competitive pricing campaign highlighting value proposition. Create comparison chart showing cost savings. Offer limited-time migration incentive with 3 months free service."
    }
  ];

  const filteredAlerts = alerts.filter(alert => {
    const categoryMatch = selectedCategory === 'all' || alert.category.toLowerCase() === selectedCategory;
    const priorityMatch = selectedPriority === 'all' || alert.priority.toLowerCase() === selectedPriority;
    return categoryMatch && priorityMatch;
  });

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 80) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (score >= 70) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  const getPriorityColor = (priority: string) => {
    if (priority === 'High') return 'bg-red-100 text-red-800 border-red-200';
    if (priority === 'Medium') return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-green-100 text-green-800 border-green-200';
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Market': return 'ri-line-chart-line';
      case 'Content': return 'ri-article-line';
      case 'Customer': return 'ri-user-heart-line';
      case 'Technology': return 'ri-robot-line';
      case 'Competitive': return 'ri-sword-line';
      default: return 'ri-notification-line';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Opportunity Alerts</h1>
          <p className="text-sm sm:text-base text-gray-600">AI-powered opportunities to grow your business</p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">Total Alerts</p>
                <p className="text-xl sm:text-2xl font-bold text-gray-900">{alerts.length}</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <i className="ri-notification-line text-blue-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">High Priority</p>
                <p className="text-xl sm:text-2xl font-bold text-red-600">{alerts.filter(a => a.priority === 'High').length}</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-red-100 rounded-lg flex items-center justify-center">
                <i className="ri-alarm-warning-line text-red-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">Avg Score</p>
                <p className="text-xl sm:text-2xl font-bold text-green-600">86</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <i className="ri-trophy-line text-green-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm font-medium text-gray-600">This Week</p>
                <p className="text-xl sm:text-2xl font-bold text-orange-600">12</p>
              </div>
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <i className="ri-calendar-week-line text-orange-600 text-lg sm:text-xl"></i>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-6">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm"
              >
                <option value="all">All Categories</option>
                <option value="market">Market</option>
                <option value="content">Content</option>
                <option value="customer">Customer</option>
                <option value="technology">Technology</option>
                <option value="competitive">Competitive</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm"
              >
                <option value="all">All Priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>

        {/* Alerts List */}
        <div className="space-y-6 sm:space-y-8">
          {filteredAlerts.map((alert) => (
            <div key={alert.id} className="bg-white rounded-lg sm:rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Alert Header */}
              <div className="p-4 sm:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-3 sm:gap-4">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className={`${getCategoryIcon(alert.category)} text-orange-600 text-lg sm:text-xl`}></i>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-2">{alert.title}</h3>
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(alert.priority)}`}>
                          {alert.priority} Priority
                        </span>
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
                          {alert.category}
                        </span>
                        <span className="text-xs sm:text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          {alert.timeRemaining} remaining
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex-shrink-0">
                    <div className={`px-3 py-2 rounded-lg border text-center ${getScoreColor(alert.score)}`}>
                      <div className="text-lg sm:text-xl font-bold">{alert.score}</div>
                      <div className="text-xs font-medium">Score</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Alert Content */}
              <div className="p-4 sm:p-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
                  {/* Why Act Now */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center">
                        <i className="ri-time-line text-red-600 text-sm"></i>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">Why Act Now</h4>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{alert.whyActNow}</p>
                  </div>

                  {/* Potential Reward */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                        <i className="ri-money-dollar-circle-line text-green-600 text-sm"></i>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">Potential Reward</h4>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{alert.potentialReward}</p>
                  </div>

                  {/* Action Required */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                        <i className="ri-checkbox-circle-line text-blue-600 text-sm"></i>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">Action Required</h4>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{alert.actionRequired}</p>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row gap-3 mt-6 pt-6 border-t border-gray-200">
                  <button className="flex-1 bg-orange-500 text-white px-4 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium text-sm sm:text-base whitespace-nowrap">
                    Take Action
                  </button>
                  <button className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors font-medium text-sm sm:text-base whitespace-nowrap">
                    View Details
                  </button>
                  <button className="flex-1 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm sm:text-base whitespace-nowrap">
                    Remind Later
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
