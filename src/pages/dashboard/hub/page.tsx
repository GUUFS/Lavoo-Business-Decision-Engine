
import { useState } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import Footer from '../../../components/feature/Footer';

export default function HubPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIndustry, setSelectedIndustry] = useState('all');

  const industries = [
    { id: 'all', name: 'All Industries', count: 6 },
    { id: 'technology', name: 'Technology', count: 1 },
    { id: 'retail', name: 'Retail', count: 1 },
    { id: 'healthcare', name: 'Healthcare', count: 1 },
    { id: 'education', name: 'Education', count: 1 },
    { id: 'automotive', name: 'Automotive', count: 1 },
    { id: 'fitness', name: 'Fitness', count: 1 }
  ];

  const businessAnalyses = [
    {
      id: 1,
      businessName: 'TechFlow Solutions',
      industry: 'technology',
      businessType: 'SaaS Platform',
      challenge: 'Struggling with customer retention and high churn rates despite strong initial user acquisition',
      strategies: [
        'Implement predictive analytics to identify at-risk customers',
        'Develop personalized onboarding sequences',
        'Create value-driven email campaigns'
      ],
      insights: [
        'Users who complete onboarding have 3x higher retention',
        'Feature adoption correlates strongly with subscription renewals',
        'Support response time directly impacts customer satisfaction'
      ],
      tools: [
        'Customer Success Platform (Gainsight)',
        'Predictive Analytics (Mixpanel)',
        'Email Automation (Intercom)'
      ],
      impact: 'High',
      implementationTime: '3-4 months',
      successProbability: '85%'
    },
    {
      id: 2,
      businessName: 'GreenLeaf Organics',
      industry: 'retail',
      businessType: 'E-commerce Store',
      challenge: 'Low conversion rates and difficulty in personalizing customer experience across multiple channels',
      strategies: [
        'Deploy AI-powered product recommendation engine',
        'Implement dynamic pricing optimization',
        'Create omnichannel customer journey mapping'
      ],
      insights: [
        'Personalized recommendations increase AOV by 35%',
        'Mobile users have different purchase patterns',
        'Seasonal trends significantly impact inventory needs'
      ],
      tools: [
        'Recommendation Engine (Dynamic Yield)',
        'Price Optimization (Prisync)',
        'Customer Journey Analytics (Hotjar)'
      ],
      impact: 'Medium',
      implementationTime: '2-3 months',
      successProbability: '78%'
    },
    {
      id: 3,
      businessName: 'HealthFirst Clinic',
      industry: 'healthcare',
      businessType: 'Medical Practice',
      challenge: 'Inefficient appointment scheduling and poor patient communication leading to high no-show rates',
      strategies: [
        'Implement AI-powered appointment optimization',
        'Deploy automated patient reminder system',
        'Create predictive no-show prevention model'
      ],
      insights: [
        'Automated reminders reduce no-shows by 40%',
        'Optimal appointment slots vary by patient demographics',
        'Patient satisfaction correlates with wait times'
      ],
      tools: [
        'Scheduling AI (Acuity Scheduling)',
        'Patient Communication (SimplePractice)',
        'Predictive Analytics (Tableau)'
      ],
      impact: 'High',
      implementationTime: '1-2 months',
      successProbability: '92%'
    },
    {
      id: 4,
      businessName: 'EduBright Academy',
      industry: 'education',
      businessType: 'Online Learning Platform',
      challenge: 'Low course completion rates and difficulty in measuring learning effectiveness across diverse student base',
      strategies: [
        'Implement adaptive learning algorithms',
        'Deploy student engagement analytics',
        'Create personalized learning path recommendations'
      ],
      insights: [
        'Micro-learning modules improve completion by 60%',
        'Peer interaction increases retention rates',
        'Progress tracking motivates continued learning'
      ],
      tools: [
        'Adaptive Learning (Knewton)',
        'Learning Analytics (Brightspace)',
        'Engagement Platform (Kahoot!)'
      ],
      impact: 'Medium',
      implementationTime: '4-5 months',
      successProbability: '73%'
    },
    {
      id: 5,
      businessName: 'AutoCare Express',
      industry: 'automotive',
      businessType: 'Auto Service Chain',
      challenge: 'Inefficient inventory management and unpredictable service demand leading to customer wait times',
      strategies: [
        'Deploy predictive maintenance scheduling',
        'Implement dynamic inventory optimization',
        'Create customer demand forecasting model'
      ],
      insights: [
        'Seasonal patterns affect service demand by 45%',
        'Predictive maintenance reduces emergency repairs',
        'Inventory turnover optimization saves 25% costs'
      ],
      tools: [
        'Inventory Management (TradeGecko)',
        'Predictive Maintenance (IBM Watson)',
        'Demand Forecasting (Oracle Analytics)'
      ],
      impact: 'High',
      implementationTime: '3-4 months',
      successProbability: '81%'
    },
    {
      id: 6,
      businessName: 'FitLife Gym Network',
      industry: 'fitness',
      businessType: 'Fitness Centers',
      challenge: 'High membership churn and difficulty in optimizing class schedules and equipment usage',
      strategies: [
        'Implement member engagement prediction model',
        'Deploy smart equipment utilization tracking',
        'Create personalized fitness journey recommendations'
      ],
      insights: [
        'Members who attend classes have 70% lower churn',
        'Peak hours vary significantly by location',
        'Personalized workouts increase satisfaction by 50%'
      ],
      tools: [
        'Member Analytics (Mindbody)',
        'Equipment IoT (Technogym)',
        'Fitness AI (MyFitnessPal API)'
      ],
      impact: 'Medium',
      implementationTime: '2-3 months',
      successProbability: '76%'
    }
  ];

  const filteredAnalyses = businessAnalyses.filter(analysis => {
    const matchesSearch = analysis.businessName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         analysis.challenge.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesIndustry = selectedIndustry === 'all' || analysis.industry === selectedIndustry;
    return matchesSearch && matchesIndustry;
  });

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'High':
        return 'bg-green-100 text-green-600';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-600';
      case 'Low':
        return 'bg-gray-100 text-gray-600';
      default:
        return 'bg-gray-100 text-gray-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
     <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-6 md:mb-8">
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Business Intelligence Hub</h1>
              <p className="text-gray-600">Explore AI analysis results and recommendations for various businesses across different industries</p>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6 mb-8">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-4">
                    <i className="ri-building-line text-blue-600 text-xl"></i>
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">6</h3>
                    <p className="text-gray-600 text-sm">Businesses Analyzed</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mr-4">
                    <i className="ri-pie-chart-line text-green-600 text-xl"></i>
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">6</h3>
                    <p className="text-gray-600 text-sm">Industries Covered</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mr-4">
                    <i className="ri-trophy-line text-orange-600 text-xl"></i>
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">81%</h3>
                    <p className="text-gray-600 text-sm">Avg Success Rate</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Search and Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
              <div className="flex flex-col lg:flex-row gap-4 mb-4">
                {/* Search */}
                <div className="flex-1">
                  <div className="relative">
                    <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input
                      type="text"
                      placeholder="Search businesses or challenges..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm"
                    />
                  </div>
                </div>

                {/* Export Button */}
                <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                  <i className="ri-download-line mr-2"></i>
                  Export Report
                </button>
              </div>

              {/* Industry Filter */}
              <div className="flex gap-2 overflow-x-auto pb-2">
                {industries.map((industry) => (
                  <button
                    key={industry.id}
                    onClick={() => setSelectedIndustry(industry.id)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                      selectedIndustry === industry.id
                        ? 'bg-orange-100 text-orange-600 border border-orange-200'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {industry.name} ({industry.count})
                  </button>
                ))}
              </div>
            </div>

            {/* Business Analysis Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 md:gap-8">
              {filteredAnalyses.map((analysis) => (
                <div key={analysis.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">{analysis.businessName}</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-600">{analysis.businessType}</span>
                        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded-full capitalize">
                          {analysis.industry}
                        </span>
                      </div>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600">
                      <i className="ri-more-line"></i>
                    </button>
                  </div>

                  {/* Challenge */}
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Challenge</h4>
                    <p className="text-gray-600 text-sm leading-relaxed">{analysis.challenge}</p>
                  </div>

                  {/* AI Recommendations */}
                  <div className="space-y-4 mb-6">
                    {/* Strategies */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">AI Strategies</h4>
                      <ul className="space-y-1">
                        {analysis.strategies.map((strategy, index) => (
                          <li key={index} className="text-sm text-gray-600 flex items-start">
                            <i className="ri-arrow-right-s-line text-orange-500 mt-0.5 mr-1 flex-shrink-0"></i>
                            {strategy}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Key Insights */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Key Insights</h4>
                      <ul className="space-y-1">
                        {analysis.insights.map((insight, index) => (
                          <li key={index} className="text-sm text-gray-600 flex items-start">
                            <i className="ri-lightbulb-line text-blue-500 mt-0.5 mr-1 flex-shrink-0"></i>
                            {insight}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Recommended Tools */}
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Recommended Tools</h4>
                      <div className="flex flex-wrap gap-2">
                        {analysis.tools.map((tool, index) => (
                          <span key={index} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-sm font-medium text-gray-700 mb-1">Impact</div>
                      <span className={`text-xs px-2 py-1 rounded-full ${getImpactColor(analysis.impact)}`}>
                        {analysis.impact}
                      </span>
                    </div>
                    <div className="text-center">
                      <div className="text-sm font-medium text-gray-700 mb-1">Timeline</div>
                      <div className="text-xs text-gray-600">{analysis.implementationTime}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm font-medium text-gray-700 mb-1">Success Rate</div>
                      <div className="text-xs text-green-600 font-medium">{analysis.successProbability}</div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      View Full Analysis
                    </button>
                    <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                      Share Report
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Empty State */}
            {filteredAnalyses.length === 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className="ri-search-line text-2xl text-gray-400"></i>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No analyses found</h3>
                <p className="text-gray-600 mb-6">Try adjusting your search terms or industry filters</p>
                <button 
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedIndustry('all');
                  }}
                  className="bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 transition-colors whitespace-nowrap"
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        </div>
    </div>
  );
}
