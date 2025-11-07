
import { useState } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import Footer from '../../../components/feature/Footer';
import { useNavigate } from 'react-router-dom';

export default function InsightsPage() {
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isPremium] = useState(false); // This would come from user's subscription status

  const insights = [
    {
      id: 1,
      title: "Google's New AI Search Algorithm Prioritizes E-A-T Content",
      category: "SEO",
      readTime: "3 min read",
      publishedAt: "2 hours ago",
      source: "https://searchengineland.com/google-ai-search-algorithm-eat-content",
      isPremium: false,
      whatChanged: "Google's latest algorithm update now heavily weighs Expertise, Authoritativeness, and Trustworthiness (E-A-T) signals. Sites with verified author credentials and industry recognition are seeing 40% higher rankings.",
      whyItMatters: "This shift affects 73% of search results. Businesses without established authority are losing visibility, while those with strong E-A-T signals are capturing more organic traffic and leads.",
      actionToTake: "Audit your content for E-A-T signals. Add author bios with credentials, get industry certifications, and build authoritative backlinks. Update existing content with expert quotes and data sources."
    },
    {
      id: 2,
      title: "LinkedIn Introduces AI-Powered Lead Scoring for Sales Navigator",
      category: "Sales",
      readTime: "4 min read",
      publishedAt: "5 hours ago",
      source: "https://linkedin.com/business/sales/blog/ai-lead-scoring-sales-navigator",
      isPremium: false,
      whatChanged: "LinkedIn's new AI feature analyzes prospect behavior, engagement patterns, and buying signals to score leads from 1-100. Early users report 60% improvement in conversion rates.",
      whyItMatters: "Sales teams can now prioritize high-intent prospects automatically. This reduces time spent on cold leads and increases focus on prospects most likely to convert, improving ROI significantly.",
      actionToTake: "Upgrade to Sales Navigator Premium to access AI lead scoring. Train your sales team on interpreting scores and adjust outreach strategies based on lead temperature and engagement history."
    },
    {
      id: 3,
      title: "Meta Launches Advanced Retargeting Options for Small Businesses",
      category: "Advertising",
      readTime: "5 min read",
      publishedAt: "1 day ago",
      source: "https://business.facebook.com/advanced-retargeting-small-business",
      isPremium: true,
      whatChanged: "",
      whyItMatters: "",
      actionToTake: ""
    },
    {
      id: 4,
      title: "OpenAI Releases GPT-4 Turbo with Enhanced Business Applications",
      category: "AI",
      readTime: "6 min read",
      publishedAt: "1 day ago",
      source: "https://openai.com/gpt-4-turbo-business-applications",
      isPremium: true,
      whatChanged: "",
      whyItMatters: "",
      actionToTake: ""
    },
    {
      id: 5,
      title: "TikTok Shop Integration Now Available for E-commerce Platforms",
      category: "E-commerce",
      readTime: "4 min read",
      publishedAt: "2 days ago",
      source: "https://tiktok.com/business/shop-integration-ecommerce",
      isPremium: true,
      whatChanged: "",
      whyItMatters: "",
      actionToTake: ""
    }
  ];

  const [readArticles, setReadArticles] = useState<number[]>([]);

  const markAsRead = (articleId: number) => {
    if (!readArticles.includes(articleId)) {
      setReadArticles([...readArticles, articleId]);
    }
  };

  const filteredInsights = insights.filter(insight => {
    return selectedCategory === 'all' || insight.category.toLowerCase() === selectedCategory;
  });

  // Show only first 2 alerts + premium upgrade alert if not premium
  const displayedAlerts = isPremium ? filteredInsights : filteredInsights.slice(0, 2);
  const premiumAlertsCount = filteredInsights.filter(insight => insight.isPremium).length;

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'SEO': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Sales': return 'bg-green-100 text-green-800 border-green-200';
      case 'Advertising': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'AI': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'E-commerce': return 'bg-pink-100 text-pink-800 border-pink-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'SEO': return 'ri-search-line';
      case 'Sales': return 'ri-line-chart-line';
      case 'Advertising': return 'ri-megaphone-line';
      case 'AI': return 'ri-robot-line';
      case 'E-commerce': return 'ri-shopping-cart-line';
      default: return 'ri-article-line';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8 min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">AI Insights Feed</h1>
          <p className="text-sm sm:text-base text-gray-600">Stay ahead with AI-curated business intelligence</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-gray-900">{insights.length}</div>
              <div className="text-xs sm:text-sm text-gray-600">Total Articles</div>
            </div>
          </div>
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-green-600">{readArticles.length}</div>
              <div className="text-xs sm:text-sm text-gray-600">Read</div>
            </div>
          </div>
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-orange-600">{readArticles.length * 15}</div>
              <div className="text-xs sm:text-sm text-gray-600">Points Earned</div>
            </div>
          </div>
          <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
            <div className="text-center">
              <div className="text-xl sm:text-2xl font-bold text-blue-600">5</div>
              <div className="text-xs sm:text-sm text-gray-600">Categories</div>
            </div>
          </div>
        </div>

        {/* Filter */}
        <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm"
              >
                <option value="all">All Categories</option>
                <option value="seo">SEO</option>
                <option value="sales">Sales</option>
                <option value="advertising">Advertising</option>
                <option value="ai">AI</option>
                <option value="e-commerce">E-commerce</option>
              </select>
            </div>
          </div>
        </div>

        {/* Insights List */}
        <div className="space-y-6 sm:space-y-8">
          {displayedAlerts.map((insight, index) => (
            <div key={insight.id} className="bg-white rounded-lg sm:rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Article Header */}
              <div className="p-4 sm:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex items-start gap-3 sm:gap-4 flex-1">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className={`${getCategoryIcon(insight.category)} text-orange-600 text-lg sm:text-xl`}></i>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-3">{insight.title}</h3>
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getCategoryColor(insight.category)}`}>
                          {insight.category}
                        </span>
                        <span className="text-xs sm:text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          {insight.readTime}
                        </span>
                        <span className="text-xs sm:text-sm text-gray-500">
                          <i className="ri-calendar-line mr-1"></i>
                          {insight.publishedAt}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Article Content */}
              <div className="p-4 sm:p-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
                  {/* What Changed */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                        <i className="ri-refresh-line text-blue-600 text-sm"></i>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">What Changed</h4>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{insight.whatChanged}</p>
                  </div>

                  {/* Why It Matters */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-yellow-100 rounded-full flex items-center justify-center">
                        <i className="ri-lightbulb-line text-yellow-600 text-sm"></i>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">Why It Matters</h4>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{insight.whyItMatters}</p>
                  </div>

                  {/* Action to Take */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center">
                        <i className="ri-play-circle-line text-green-600 text-sm"></i>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-gray-900">Action to Take</h4>
                    </div>
                    <p className="text-sm sm:text-base text-gray-700 leading-relaxed">{insight.actionToTake}</p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="p-4 sm:p-6 border-t border-gray-200">
                <div className="flex flex-col sm:flex-row gap-3">
                  <button 
                    onClick={() => window.open(insight.source, '_blank')}
                    className="flex-1 flex items-center justify-center px-4 py-2 rounded-lg font-medium text-sm sm:text-base whitespace-nowrap transition-colors border border-gray-300 text-gray-700 hover:bg-gray-50 cursor-pointer"
                  >
                    <i className="ri-external-link-line mr-2"></i>
                    View Source
                  </button>
                  <button 
                    onClick={() => markAsRead(insight.id)}
                    disabled={readArticles.includes(insight.id)}
                    className={`flex-1 flex items-center justify-center px-4 py-2 rounded-lg font-medium text-sm sm:text-base whitespace-nowrap transition-colors cursor-pointer ${
                      readArticles.includes(insight.id)
                        ? 'bg-green-100 text-green-700 cursor-not-allowed'
                        : 'bg-orange-500 text-white hover:bg-orange-600'
                    }`}
                  >
                    <i className={`${readArticles.includes(insight.id) ? 'ri-check-line' : 'ri-star-line'} mr-2`}></i>
                    {readArticles.includes(insight.id) ? 'Read (+15 points)' : 'Mark as Read (+15 points)'}
                  </button>
                </div>
              </div>
            </div>
          ))}

          {/* Premium Upgrade Alert */}
          {!isPremium && premiumAlertsCount > 0 && (
            <div className="bg-white rounded-lg sm:rounded-xl border border-gray-200 shadow-sm overflow-hidden">
              {/* Alert Header */}
              <div className="p-4 sm:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex items-start gap-3 sm:gap-4 flex-1">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-orange-400 to-orange-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-vip-crown-line text-white text-lg sm:text-xl"></i>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900 mb-3">
                        {premiumAlertsCount} More Premium Insights Available
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-orange-100 to-orange-200 text-orange-800 border border-orange-300">
                          Premium Content
                        </span>
                        <span className="text-xs sm:text-sm text-gray-500">
                          <i className="ri-lock-line mr-1"></i>
                          Unlock with Premium
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Premium Content */}
              <div className="p-4 sm:p-6">
                <div className="text-center py-8 sm:py-12">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-orange-400 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-6">
                    <i className="ri-vip-crown-line text-white text-2xl sm:text-3xl"></i>
                  </div>
                  <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-3">Unlock Premium Insights</h3>
                  <p className="text-sm sm:text-base text-gray-600 mb-2 max-w-md mx-auto">
                    Get access to {premiumAlertsCount} additional premium insights with detailed analysis and actionable recommendations
                  </p>
                  <p className="text-xs sm:text-sm text-orange-600 font-medium mb-8">
                    Premium members get 3x more insights and exclusive content
                  </p>
                  
                  {/* Premium Features */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 max-w-2xl mx-auto">
                    <div className="text-center">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center mx-auto mb-2 shadow-sm">
                        <i className="ri-eye-line text-orange-600"></i>
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-gray-700">Detailed Analysis</p>
                    </div>
                    <div className="text-center">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center mx-auto mb-2 shadow-sm">
                        <i className="ri-lightbulb-line text-orange-600"></i>
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-gray-700">AI Insights</p>
                    </div>
                    <div className="text-center">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center mx-auto mb-2 shadow-sm">
                        <i className="ri-rocket-line text-orange-600"></i>
                      </div>
                      <p className="text-xs sm:text-sm font-medium text-gray-700">Action Plans</p>
                    </div>
                  </div>

                  <button 
                    onClick={() => navigate('/dashboard/upgrade')}
                    className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-8 py-3 rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all font-medium text-sm sm:text-base whitespace-nowrap shadow-lg cursor-pointer transform hover:scale-105"
                  >
                    Upgrade to Premium
                  </button>
                  <p className="text-xs text-gray-500 mt-3">Starting at $29/month • Cancel anytime</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Show message if no insights match filters */}
        {displayedAlerts.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="ri-article-line text-gray-400 text-2xl"></i>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No insights found</h3>
            <p className="text-gray-600">Try adjusting your filters to see more insights.</p>
          </div>
        )}
      </div>
    </div>
  );
}

