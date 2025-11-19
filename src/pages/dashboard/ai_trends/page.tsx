
import { useState, useEffect } from 'react';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';

export default function TrendsPage() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1024);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Mark trends as viewed when page loads
  useEffect(() => {
    localStorage.setItem('trendsNewCount', '0');
    window.dispatchEvent(new CustomEvent('trendsNewCountChanged', { 
      detail: { count: 0 } 
    }));
  }, []);

  const isMobile = windowWidth < 640;
  const isTablet = windowWidth >= 640 && windowWidth < 1024;

  const viralTrends = [
    {
      id: 1,
      title: 'AI Avatars for Content Creation',
      industry: 'Technology',
      description: 'AI avatars are exploding on social media. Creators using tools like HeyGen and D-ID are getting 10x engagement. People love the novelty and production quality looks professional with zero camera work.',
      engagement: '12.5M',
      growth: '+245%',
      viralScore: 96,
      peakTime: '2:00 PM EST',
      hashtags: ['#AIAvatars', '#ContentCreation', '#DigitalInfluencer'],
      platforms: ['LinkedIn', 'Twitter', 'TikTok'],
      color: 'bg-blue-500',
      searchVolume: '450,000',
      competition: 'low',
      opportunity: '94%',
      nature: 'Explosive',
      actionItems: 'Create AI avatar version of yourself using HeyGen and D-ID, get 10x engagement, People love the novelty and production quality looks professional with zero camera work.'
    },
    {
      id: 2,
      title: 'AI Agents (Autonomous AI Workers)',
      industry: 'Technology', 
      description: 'AI agents that can complete tasks autonomously are THE hottest topic in AI. Companies are racing to build "AI employees" that can handle customer service, data analysis, and content creation without human intervention. This is bigger than chatbots.',
      engagement: '15.2M',
      growth: '+312%',
      viralScore: 94,
      peakTime: '10:00 AM EST',
      hashtags: ['#AIAgents', '#AutonomousAI', '#AIWorkers'],
      platforms: ['LinkedIn', 'Facebook', 'Twitter'],
      color: 'bg-red-500',
      searchVolume: '450,000',
      competition: 'low',
      opportunity: '92%',
      nature: 'Explosive',
      actionItems: 'Develop comprehensive AI roadmap, identify key use cases for your business, allocate budget for AI tools and training, and begin pilot programs within 30 days.'
    },
    {
      id: 3,
      title: 'Sustainable Fashion Revolution',
      industry: 'Retail',
      description: 'Eco-friendly fashion brands gaining massive traction with recycled materials and carbon-neutral production methods. Gen Z consumers are driving this shift with purchasing power.',
      engagement: '8.7M',
      growth: '+189%',
      viralScore: 87,
      peakTime: '6:00 PM EST',
      hashtags: ['#SustainableFashion', '#EcoStyle', '#GreenFashion'],
      platforms: ['Instagram', 'TikTok', 'Pinterest'],
      color: 'bg-green-500',
      searchVolume: '320,000',
      competition: 'medium',
      opportunity: '85%',
      nature: 'Growing',
      actionItems: 'Research sustainable materials, partner with eco-friendly suppliers, create transparent supply chain messaging, launch green product line.'
    },
    {
      id: 4,
      title: 'Immersive Learning Experiences',
      industry: 'Education',
      description: 'VR and AR technologies creating engaging educational content that boosts student retention by 300%. Educational institutions are rapidly adopting immersive learning platforms.',
      engagement: '6.3M',
      growth: '+156%',
      viralScore: 82,
      peakTime: '3:00 PM EST',
      hashtags: ['#EdTech', '#VRLearning', '#ImmersiveEducation'],
      platforms: ['YouTube', 'LinkedIn', 'Twitter'],
      color: 'bg-purple-500',
      searchVolume: '180,000',
      competition: 'low',
      opportunity: '78%',
      nature: 'Emerging',
      actionItems: 'Evaluate VR/AR platforms, create pilot educational content, measure engagement improvements, scale successful programs.'
    },
    {
      id: 5,
      title: 'Electric Vehicle Adoption',
      industry: 'Automotive',
      description: 'Massive surge in EV sales driven by improved battery technology and expanding charging infrastructure. Tesla competitors are gaining significant market share.',
      engagement: '11.8M',
      growth: '+278%',
      viralScore: 91,
      peakTime: '7:00 PM EST',
      hashtags: ['#ElectricVehicles', '#CleanEnergy', '#EVRevolution'],
      platforms: ['Twitter', 'YouTube', 'Instagram'],
      color: 'bg-yellow-500',
      searchVolume: '890,000',
      competition: 'high',
      opportunity: '88%',
      nature: 'Mainstream',
      actionItems: 'Research EV market opportunities, consider charging infrastructure investments, explore fleet electrification, partner with EV manufacturers.'
    },
    {
      id: 6,
      title: 'Smart Fitness Technology',
      industry: 'Fitness',
      description: 'AI-powered fitness apps and wearables providing personalized workout plans and real-time health monitoring. Home fitness market continues explosive growth.',
      engagement: '9.4M',
      growth: '+203%',
      viralScore: 85,
      peakTime: '5:00 AM EST',
      hashtags: ['#FitnessTech', '#SmartWorkouts', '#HealthMonitoring'],
      platforms: ['Instagram', 'TikTok', 'YouTube'],
      color: 'bg-orange-500',
      searchVolume: '275,000',
      competition: 'medium',
      opportunity: '82%',
      nature: 'Growing',
      actionItems: 'Develop AI fitness features, integrate wearable technology, create personalized workout algorithms, launch home fitness solutions.'
    }
  ];

  const industries = ['all', 'Technology', 'Retail', 'Healthcare', 'Education', 'Automotive', 'Fitness'];

  const filteredTrends = viralTrends.filter(trend => {
    const matchesIndustry = selectedIndustry === 'all' || trend.industry === selectedIndustry;
    const matchesSearch = trend.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         trend.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         trend.hashtags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchesIndustry && matchesSearch;
  });

  const getGrowthColor = (growth: string) => {
    const percentage = parseInt(growth.replace('+', '').replace('%', ''));
    if (percentage >= 250) return 'text-green-600 bg-green-100';
    if (percentage >= 200) return 'text-blue-600 bg-blue-100';
    if (percentage >= 150) return 'text-orange-600 bg-orange-100';
    return 'text-gray-600 bg-gray-100';
  };

  const getViralScoreColor = (score: number) => {
    if (score >= 90) return 'text-red-600 bg-red-100';
    if (score >= 80) return 'text-orange-600 bg-orange-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-gray-600 bg-gray-100';
  };

  const getOpportunityColor = (opportunity: string) => {
    const percentage = parseInt(opportunity.replace('%', ''));
    if (percentage >= 90) return 'text-green-600 bg-green-100';
    if (percentage >= 80) return 'text-blue-600 bg-blue-100';
    if (percentage >= 70) return 'text-orange-600 bg-orange-100';
    return 'text-gray-600 bg-gray-100';
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <DashboardSidebar 
        isMobileMenuOpen={isMobileMenuOpen} 
        setIsMobileMenuOpen={setIsMobileMenuOpen} 
      />
      
      {/* Main Content */}
      <div className={`flex-1 ${isMobile ? 'ml-0' : '0'} flex flex-col`}>
        <div className={`flex-1 ${isMobile ? 'p-4' : isTablet ? 'p-6' : 'p-8'}`}>
          <div className="max-w-7xl mx-auto">
            {/* Header */}
            <div className={`${isMobile ? 'mb-6' : 'mb-8'}`}>
              <h1 className={`${isMobile ? 'text-2xl' : isTablet ? 'text-3xl' : 'text-4xl'} font-bold text-gray-900 mb-2`}>
                Viral AI Trends
              </h1>
              <p className={`text-gray-600 ${isMobile ? 'text-sm' : 'text-base'}`}>
                Discover the hottest viral trends across technologies with real-time engagement metrics
              </p>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
              <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} gap-4`}>
                {/* Search */}
                <div className="flex-1">
                  <div className="relative">
                    <i className="ri-search-line absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input
                      type="text"
                      placeholder="Search trends, hashtags, or keywords..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none"
                    />
                  </div>
                </div>

                {/* Industry Filter */}
                <select
                  value={selectedIndustry}
                  onChange={(e) => setSelectedIndustry(e.target.value)}
                  className="border border-gray-300 text-gray-700 py-3 px-4 pr-8 rounded-lg text-sm font-medium bg-white hover:bg-gray-50 focus:ring-2 focus:ring-orange-200 focus:border-orange-500 outline-none"
                >
                  {industries.map(industry => (
                    <option key={industry} value={industry}>
                      {industry === 'all' ? 'All Industries' : industry}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Trends Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {filteredTrends.map((trend) => (
                <div key={trend.id} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                  {/* Trend Header */}
                  <div className="p-6 border-b border-gray-200">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`w-3 h-3 rounded-full ${trend.color}`}></div>
                          <span className="text-sm font-medium text-gray-600">{trend.industry}</span>
                          <span className="text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full font-medium">
                            VIRAL
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          {trend.title}
                        </h3>
                        <p className="text-gray-600 text-sm leading-relaxed">
                          {trend.description}
                        </p>
                      </div>
                    </div>

                    {/* Hashtags */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {trend.hashtags.map((hashtag, index) => (
                        <span key={index} className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded-full">
                          {hashtag}
                        </span>
                      ))}
                    </div>

                    {/* Platforms */}
                    <div className="flex items-center gap-2 mb-4">
                      <span className="text-xs text-gray-500">Trending on:</span>
                      {trend.platforms.map((platform, index) => (
                        <span key={index} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                          {platform}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="p-6">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900 mb-1">
                          {trend.engagement}
                        </div>
                        <div className="text-xs text-gray-500">Total Engagement</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gray-900 mb-1">
                          {trend.searchVolume}
                        </div>
                        <div className="text-xs text-gray-500">Search Volume</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="text-center">
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getGrowthColor(trend.growth)}`}>
                          {trend.growth}
                        </span>
                        <div className="text-xs text-gray-500 mt-1">Growth Rate</div>
                      </div>
                      <div className="text-center">
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getViralScoreColor(trend.viralScore)}`}>
                          {trend.viralScore}/100
                        </span>
                        <div className="text-xs text-gray-500 mt-1">Viral Score</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="text-center">
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getOpportunityColor(trend.opportunity)}`}>
                          {trend.opportunity}
                        </span>
                        <div className="text-xs text-gray-500 mt-1">Opportunity</div>
                      </div>
                      <div className="text-center">
                        <span className="inline-block px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-600">
                          {trend.nature}
                        </span>
                        <div className="text-xs text-gray-500 mt-1">Nature</div>
                      </div>
                    </div>

                    {/* Action Items */}
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      <h4 className="text-sm font-semibold text-orange-800 mb-2 flex items-center">
                        <i className="ri-flashlight-line mr-2"></i>
                        Action Items
                      </h4>
                      <p className="text-xs text-orange-700 leading-relaxed">
                        {trend.actionItems}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {filteredTrends.length === 0 && (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <i className="ri-trending-up-line text-2xl text-gray-400"></i>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  No trends found
                </h3>
                <p className="text-gray-600">
                  Try adjusting your search terms or industry filter
                </p>
              </div>
            )}

            {/* Live Updates Notice */}
            <div className="mt-8 bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-center">
                <i className="ri-live-line text-orange-600 mr-2"></i>
                <span className="text-sm text-orange-700 font-medium">
                  Live Updates: Trends are updated weekly with real-time engagement data
                </span>
              </div>
            </div>
          </div>
        </div>
      
      </div>
    </div>
  );
}
