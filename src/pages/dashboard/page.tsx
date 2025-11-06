
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardSidebar from '../../components/feature/DashboardSidebar';
import Header from '../../components/feature/Header';
/*import Footer from '../../components/feature/Footer';*/
import Button from '../../components/base/Button';

export default function Dashboard() {
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const urgentOpportunities = [
    {
      title: 'LinkedIn Algorithm Favoring Long Posts - 72 Hour Window',
      description: 'LinkedIn just pushed an algorithm update favoring posts 1200+ characters. Early testers seeing 10-15x normal reach. This won\'t last - capitalize NOW.',
      score: 96,
      timeLeft: 'Until Feb 4',
      critical: true
    },
    {
      title: 'OpenAI DevDay Announcements Creating Tool Opportunity',
      description: 'OpenAI just announced new GPT-4 features that enable voice and vision capabilities. First movers who build tools leveraging these will dominate.',
      score: 96,
      timeLeft: 'Until Feb 14',
      critical: true
    },
    {
      title: 'Meta AI Studio Early Access - Build Your AI Twin Before Competition',
      description: 'Meta AI Studio is in early access (launched Oct 14, 2025). First 10,000 creators get priority features and promotional boost from Meta. Applications close October 31st.',
      score: 95,
      timeLeft: 'Until Oct 30',
      critical: true
    }
  ];

  const aiInsights = [
    {
      title: 'Content Performance Analysis',
      description: 'Your video content performs 340% better than text posts. Recommend increasing video production by 60%.',
      impact: 'High',
      category: 'Content Strategy'
    },
    {
      title: 'Audience Engagement Patterns',
      description: 'Peak engagement occurs Tuesday-Thursday 2-4 PM EST. Scheduling posts during this window increases reach by 180%.',
      impact: 'Medium',
      category: 'Timing Optimization'
    },
    {
      title: 'Competitor Gap Analysis',
      description: 'Identified 3 content gaps in your niche with low competition but high search volume. Potential for 50K+ monthly views.',
      impact: 'High',
      category: 'Market Opportunity'
    }
  ];

  const recentEarnings = [
    {
      source: 'Course Sales',
      amount: '$12,450',
      change: '+23%',
      period: 'This month'
    },
    {
      source: 'Affiliate Commissions',
      amount: '$8,920',
      change: '+15%',
      period: 'This month'
    },
    {
      source: 'Consulting Services',
      amount: '$3,210',
      change: '+8%',
      period: 'This month'
    }
  ];

  const recentReviews = [
    {
      platform: 'Google',
      rating: 5,
      author: 'Sarah Johnson',
      text: 'Exceptional AI consulting services. Helped transform our business strategy completely.',
      time: '2 hours ago'
    },
    {
      platform: 'LinkedIn',
      rating: 5,
      author: 'Michael Chen',
      text: 'Outstanding insights and practical recommendations. Highly recommend!',
      time: '1 day ago'
    },
    {
      platform: 'Trustpilot',
      rating: 4,
      author: 'Emma Davis',
      text: 'Great experience overall. Very knowledgeable and professional team.',
      time: '3 days ago'
    }
  ];

  const hubIntegrations = [
    {
      name: 'Google Analytics',
      status: 'Connected',
      lastSync: '2 minutes ago',
      icon: 'ri-google-line'
    },
    {
      name: 'Shopify Store',
      status: 'Connected',
      lastSync: '5 minutes ago',
      icon: 'ri-shopping-bag-line'
    },
    {
      name: 'Mailchimp',
      status: 'Connected',
      lastSync: '1 hour ago',
      icon: 'ri-mail-line'
    },
    {
      name: 'Slack Workspace',
      status: 'Pending',
      lastSync: 'Not synced',
      icon: 'ri-slack-line'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen}
        setIsMobileMenuOpen={setIsMobileMenuOpen}
      />
      
      <div className="flex-1 md:ml-64 flex flex-col">
        <div className="flex-1 p-4 md:p-6 lg:p-8">
          
          {/* Header */}
          <div className="mb-6 md:mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
              <div className="flex-1">
                <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 mb-2">
                  Welcome to Your Dashboard
                </h1>
                <p className="text-gray-600 text-sm md:text-base">
                  Get a complete overview of your business performance and access all tools from here.
                </p>
              </div>
              <div className="hidden lg:flex items-center space-x-4">
                <div className="bg-white rounded-lg px-4 py-2 shadow-sm border border-gray-200">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">All systems operational</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 md:mb-8">
            <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">Total Revenue</p>
                  <p className="text-xl md:text-2xl font-bold text-gray-900">$24,580</p>
                </div>
                <div className="w-10 h-10 md:w-12 md:h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                  <i className="ri-money-dollar-circle-line text-green-600 text-lg md:text-xl"></i>
                </div>
              </div>
              <div className="mt-3 flex items-center">
                <i className="ri-arrow-up-line text-green-500 text-sm"></i>
                <span className="text-green-500 text-sm font-medium ml-1">+12.5%</span>
                <span className="text-gray-500 text-sm ml-2">vs last month</span>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">Active Alerts</p>
                  <p className="text-xl md:text-2xl font-bold text-gray-900">8</p>
                </div>
                <div className="w-10 h-10 md:w-12 md:h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                  <i className="ri-alert-line text-orange-600 text-lg md:text-xl"></i>
                </div>
              </div>
              <div className="mt-3 flex items-center">
                <i className="ri-arrow-up-line text-orange-500 text-sm"></i>
                <span className="text-orange-500 text-sm font-medium ml-1">3 new</span>
                <span className="text-gray-500 text-sm ml-2">today</span>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">AI Insights</p>
                  <p className="text-xl md:text-2xl font-bold text-gray-900">156</p>
                </div>
                <div className="w-10 h-10 md:w-12 md:h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                  <i className="ri-brain-line text-purple-600 text-lg md:text-xl"></i>
                </div>
              </div>
              <div className="mt-3 flex items-center">
                <i className="ri-arrow-up-line text-purple-500 text-sm"></i>
                <span className="text-purple-500 text-sm font-medium ml-1">+8 today</span>
                <span className="text-gray-500 text-sm ml-2">this week</span>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 md:p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">Avg Rating</p>
                  <p className="text-xl md:text-2xl font-bold text-gray-900">4.8</p>
                </div>
                <div className="w-10 h-10 md:w-12 md:h-12 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0 ml-3">
                  <i className="ri-star-line text-yellow-600 text-lg md:text-xl"></i>
                </div>
              </div>
              <div className="mt-3 flex items-center">
                <i className="ri-arrow-up-line text-yellow-500 text-sm"></i>
                <span className="text-yellow-500 text-sm font-medium ml-1">+0.2</span>
                <span className="text-gray-500 text-sm ml-2">this month</span>
              </div>
            </div>
          </div>

          {/* Dashboard Sections */}
          <div className="space-y-6 md:space-y-8">
            {/* Urgent Opportunities */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-alert-line text-orange-600"></i>
                    </div>
                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">Urgent Opportunities</h3>
                  </div>
                  <Button
                    onClick={() => navigate('/dashboard/alerts')}
                    variant="outline"
                    size="sm"
                    className="whitespace-nowrap self-start sm:self-auto"
                  >
                    View All <i className="ri-arrow-right-line ml-1"></i>
                  </Button>
                </div>
              </div>
              <div className="p-4 md:p-6">
                <div className="space-y-4">
                  {urgentOpportunities.map((opportunity, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 md:p-6 hover:border-orange-200 hover:bg-orange-50/30 transition-all duration-200">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between space-y-3 sm:space-y-0 mb-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                            <i className="ri-fire-line text-red-600 text-sm"></i>
                          </div>
                          <span className="text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full font-medium">critical</span>
                        </div>
                        <div className="text-left sm:text-right">
                          <div className="text-sm font-medium text-gray-900">Score: {opportunity.score}</div>
                          <div className="text-xs text-gray-500">{opportunity.timeLeft}</div>
                        </div>
                      </div>
                      <h4 className="font-medium text-gray-900 mb-2 text-sm md:text-base">{opportunity.title}</h4>
                      <p className="text-sm text-gray-600 leading-relaxed">{opportunity.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* AI Insights */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-brain-line text-purple-600"></i>
                    </div>
                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">AI Insights</h3>
                  </div>
                  <Button
                    onClick={() => navigate('/dashboard/insights')}
                    variant="outline"
                    size="sm"
                    className="whitespace-nowrap self-start sm:self-auto"
                  >
                    View All <i className="ri-arrow-right-line ml-1"></i>
                  </Button>
                </div>
              </div>
              <div className="p-4 md:p-6">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
                  {aiInsights.map((insight, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-purple-200 hover:bg-purple-50/30 transition-all duration-200">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-2 sm:space-y-0 mb-3">
                        <span className={`text-xs px-2 py-1 rounded-full font-medium self-start ${
                          insight.impact === 'High' ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'
                        }`}>
                          {insight.impact} Impact
                        </span>
                        <span className="text-xs text-gray-500">{insight.category}</span>
                      </div>
                      <h4 className="font-medium text-gray-900 mb-2 text-sm md:text-base">{insight.title}</h4>
                      <p className="text-sm text-gray-600 leading-relaxed">{insight.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Earnings */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-money-dollar-circle-line text-green-600"></i>
                    </div>
                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">Earnings</h3>
                  </div>
                  <Button
                    onClick={() => navigate('/dashboard/earnings')}
                    variant="outline"
                    size="sm"
                    className="whitespace-nowrap self-start sm:self-auto"
                  >
                    View All <i className="ri-arrow-right-line ml-1"></i>
                  </Button>
                </div>
              </div>
              <div className="p-4 md:p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                  {recentEarnings.map((earning, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-green-200 hover:bg-green-50/30 transition-all duration-200">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-gray-900 text-sm md:text-base">{earning.source}</h4>
                        <span className="text-green-600 text-sm font-medium">{earning.change}</span>
                      </div>
                      <div className="text-xl md:text-2xl font-bold text-gray-900 mb-1">{earning.amount}</div>
                      <div className="text-sm text-gray-500">{earning.period}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Reviews */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-star-line text-yellow-600"></i>
                    </div>
                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">Recent Reviews</h3>
                  </div>
                  <Button
                    onClick={() => navigate('/dashboard/reviews')}
                    variant="outline"
                    size="sm"
                    className="whitespace-nowrap self-start sm:self-auto"
                  >
                    View All <i className="ri-arrow-right-line ml-1"></i>
                  </Button>
                </div>
              </div>
              <div className="p-4 md:p-6">
                <div className="space-y-4">
                  {recentReviews.map((review, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 md:p-5 hover:border-yellow-200 hover:bg-yellow-50/30 transition-all duration-200">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between space-y-2 sm:space-y-0 mb-3">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium text-gray-900">{review.author}</span>
                          <span className="text-xs text-gray-500">on {review.platform}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          {[...Array(5)].map((_, i) => (
                            <i key={i} className={`ri-star-${i < review.rating ? 'fill' : 'line'} text-yellow-400 text-sm`}></i>
                          ))}
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2 leading-relaxed">{review.text}</p>
                      <div className="text-xs text-gray-500">{review.time}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Hub */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
              <div className="p-4 md:p-6 border-b border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className="ri-global-line text-indigo-600"></i>
                    </div>
                    <h3 className="text-lg md:text-xl font-semibold text-gray-900">Hub Integrations</h3>
                  </div>
                  <Button
                    onClick={() => navigate('/dashboard/hub')}
                    variant="outline"
                    size="sm"
                    className="whitespace-nowrap self-start sm:self-auto"
                  >
                    Manage <i className="ri-arrow-right-line ml-1"></i>
                  </Button>
                </div>
              </div>
              <div className="p-4 md:p-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {hubIntegrations.map((integration, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all duration-200">
                      <div className="flex items-center space-x-3 mb-3">
                        <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <i className={`${integration.icon} text-gray-600`}></i>
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-gray-900 text-sm truncate">{integration.name}</h4>
                          <div className="flex items-center space-x-1 mt-1">
                            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                              integration.status === 'Connected' ? 'bg-green-500' : 'bg-yellow-500'
                            }`}></div>
                            <span className={`text-xs ${
                              integration.status === 'Connected' ? 'text-green-600' : 'text-yellow-600'
                            }`}>
                              {integration.status}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500">Last sync: {integration.lastSync}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
        
  
      </div>
    </div>
  );
}