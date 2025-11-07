
import Button from '../../components/base/Button';
import Header from '../../components/feature/Header';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';


export default function Results() {  

  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('bottlenecks');
  const [showToast, setShowToast] = useState(false);
  const [implementedSolutions, setImplementedSolutions] = useState<Set<number>>(new Set());
  const [selectedTools, setSelectedTools] = useState<{ [key: number]: number[] }>({
    1: [], // Low online visibility
    2: [], // Inefficient customer onboarding
    3: [], // Limited payment options
  });

  const [showComparison, setShowComparison] = useState<{ [key: number]: boolean }>({
    1: false,
    2: false,
    3: false,
  });

  const handleImplemented = (solutionId: number) => {
    setImplementedSolutions((prev) => new Set([...prev, solutionId]));
    setShowToast(true);
    setTimeout(() => setShowToast(false), 3000);
  };

  const handleToolSelection = (bottleneckId: number, toolId: number) => {
    setSelectedTools((prev) => {
      const currentTools = prev[bottleneckId] || [];
      const isSelected = currentTools.includes(toolId);
      const newTools = isSelected
        ? currentTools.filter((id) => id !== toolId)
        : [...currentTools, toolId];

      // Update comparison visibility
      setShowComparison((prevComp) => ({
        ...prevComp,
        [bottleneckId]: newTools.length >= 2,
      }));

      return { ...prev, [bottleneckId]: newTools };
    });
  };

   const bottlenecks = [
    {
      id: 1,
      title: 'Low online visibility',
      description:
        'Your business has limited presence in search results and social media platforms, making it difficult for potential customers to discover your services.',
      priority: 'HIGH',
      impact: 'Reduced customer acquisition and brand awareness',
    },
    {
      id: 2,
      title: 'Inefficient customer onboarding',
      description:
        'The current onboarding process is lengthy and confusing, leading to customer drop-offs and reduced satisfaction rates.',
      priority: 'MEDIUM',
      impact: 'Lower conversion rates and customer retention',
    },
    {
      id: 3,
      title: 'Limited payment options',
      description:
        'Customers can only pay through traditional methods, missing out on modern payment preferences and mobile transactions.',
      priority: 'MEDIUM',
      impact: 'Lost sales opportunities and customer inconvenience',
    },
  ];

    const businessStrategies = [
    {
      id: 1,
      bottleneckId: 1,
      title: 'Content Marketing Strategy',
      description:
        'Develop a comprehensive content marketing approach to improve organic visibility.',
      price: '$500-2000/month',
      rating: '88/100',
      features: ['Blog content creation', 'Social media campaigns', 'SEO optimization', 'Brand storytelling'],
      pros: ['Long-term organic growth', 'Builds brand authority', 'Cost-effective over time'],
      cons: ['Takes time to see results', 'Requires consistent effort'],
    },
    {
      id: 2,
      bottleneckId: 1,
      title: 'Influencer Partnership Program',
      description: 'Partner with industry influencers to expand reach and credibility.',
      price: '$1000-5000/month',
      rating: '85/100',
      features: [
        'Influencer identification',
        'Partnership negotiations',
        'Campaign management',
        'Performance tracking',
      ],
      pros: ['Quick visibility boost', 'Authentic endorsements', 'Access to new audiences'],
      cons: ['Dependent on influencer reputation', 'Can be expensive'],
    },
    {
      id: 3,
      bottleneckId: 2,
      title: 'Customer Journey Mapping',
      description:
        'Redesign the customer onboarding experience based on user behavior analysis.',
      price: '$2000-8000 one-time',
      rating: '92/100',
      features: [
        'User experience audit',
        'Journey optimization',
        'Touchpoint analysis',
        'Process streamlining',
      ],
      pros: ['Improves conversion rates', 'Reduces customer confusion', 'Data-driven approach'],
      cons: ['Requires initial investment', 'May need staff retraining'],
    },
    {
      id: 4,
      bottleneckId: 3,
      title: 'Payment Experience Optimization',
      description: 'Redesign checkout process to accommodate modern payment preferences.',
      price: '$1500-5000 one-time',
      rating: '89/100',
      features: [
        'Checkout flow redesign',
        'Mobile optimization',
        'Payment method integration',
        'Security enhancement',
      ],
      pros: ['Reduces cart abandonment', 'Improves user experience', 'Increases conversion rates'],
      cons: ['Implementation complexity', 'Requires testing period'],
    },
  ];

  const aiTools = [
    {
      id: 1,
      bottleneckId: 1,
      title: 'SEMrush',
      description: 'AI-powered SEO and online marketing tool for visibility optimization.',
      price: '$119.95/month',
      rating: '85/100',
      features: [
        'AI keyword research',
        'Automated site audit',
        'Competitor analysis',
        'Content optimization',
      ],
      pros: ['Comprehensive SEO features', 'AI-driven insights', 'User-friendly interface'],
      cons: ['Cost may be high for small businesses', 'Learning curve required'],
      comparison: {
        pricing: '$119.95/month',
        easeOfUse: '8/10',
        features: 'Comprehensive',
        support: '24/7 Chat',
        integration: '100+ tools',
        learningCurve: 'Medium',
      },
    },
    {
      id: 2,
      bottleneckId: 1,
      title: 'Jasper AI',
      description: 'AI content creation tool for marketing and social media.',
      price: '$49/month',
      rating: '87/100',
      features: [
        'AI content generation',
        'Brand voice training',
        'Multi-platform optimization',
        'SEO content creation',
      ],
      pros: ['Fast content creation', 'Consistent brand voice', 'Multiple content types'],
      cons: ['Requires human editing', 'May lack creativity'],
      comparison: {
        pricing: '$49/month',
        easeOfUse: '9/10',
        features: 'Content-focused',
        support: 'Email & Chat',
        integration: '50+ tools',
        learningCurve: 'Low',
      },
    },
    {
      id: 3,
      bottleneckId: 2,
      title: 'Intercom',
      description: 'AI-powered customer onboarding and support platform.',
      price: '$89/month',
      rating: '90/100',
      features: [
        'AI chatbot assistance',
        'Automated onboarding flows',
        'Smart user segmentation',
        'Predictive support',
      ],
      pros: ['24/7 automated support', 'Personalized experiences', 'Reduces support workload'],
      cons: ['Setup complexity', 'Monthly subscription cost'],
      comparison: {
        pricing: '$89/month',
        easeOfUse: '7/10',
        features: 'Customer-focused',
        support: '24/7 Phone',
        integration: '200+ tools',
        learningCurve: 'Medium',
      },
    },
    {
      id: 4,
      bottleneckId: 2,
      title: 'Pendo',
      description: 'AI-driven product analytics and user onboarding optimization.',
      price: '$2000/month',
      rating: '88/100',
      features: [
        'User behavior analytics',
        'AI-powered insights',
        'Automated user guides',
        'Feature adoption tracking',
      ],
      pros: ['Data-driven optimization', 'Improves user adoption', 'Comprehensive analytics'],
      cons: ['High cost for small businesses', 'Complex implementation'],
      comparison: {
        pricing: '$2000/month',
        easeOfUse: '6/10',
        features: 'Analytics-focused',
        support: 'Dedicated Manager',
        integration: '75+ tools',
        learningCurve: 'High',
      },
    },
    {
      id: 5,
      bottleneckId: 3,
      title: 'Stripe Radar',
      description: 'AI-powered fraud detection and payment optimization.',
      price: '$0.05 per transaction',
      rating: '94/100',
      features: [
        'AI fraud detection',
        'Payment optimization',
        'Risk scoring',
        'Automated blocking',
      ],
      pros: [
        'Reduces fraudulent transactions',
        'Improves payment success rates',
        'Machine learning adaptation',
      ],
      cons: ['Per-transaction fees', 'May block legitimate transactions'],
      comparison: {
        pricing: '$0.05/transaction',
        easeOfUse: '9/10',
        features: 'Security-focused',
        support: '24/7 Email',
        integration: 'Stripe ecosystem',
        learningCurve: 'Low',
      },
    },
    {
      id: 6,
      bottleneckId: 3,
      title: 'PayPal Advanced Checkout',
      description: 'AI-enhanced payment processing with smart recommendations.',
      price: '2.9% + $0.30 per transaction',
      rating: '86/100',
      features: [
        'Smart payment routing',
        'AI risk assessment',
        'Dynamic checkout',
        'Payment method optimization',
      ],
      pros: [
        'Wide payment method support',
        'AI-optimized conversion',
        'Global reach',
      ],
      cons: ['Transaction fees', 'Limited customization'],
      comparison: {
        pricing: '2.9% + $0.30/transaction',
        easeOfUse: '8/10',
        features: 'Payment-focused',
        support: 'Phone & Chat',
        integration: 'Global platforms',
        learningCurve: 'Low',
      },
    },
  ];

  const getCurrentStrategies = () => {
    if (activeTab === 'solutions') {
      return businessStrategies;
    }
    // default to showing strategies for the first bottleneck when on the bottlenecks tab
    return businessStrategies.filter((strategy) => strategy.bottleneckId === 1);
  };

  const getCurrentTools = () => {
    if (activeTab === 'efficiency-tools') {
      return aiTools;
    }
    // default to showing tools for the first bottleneck when on the bottlenecks tab
    return aiTools.filter((tool) => tool.bottleneckId === 1);
  };
  
  const getSelectedToolsForBottleneck = (bottleneckId: number) => {
    const selectedIds = selectedTools[bottleneckId] || [];
    return aiTools.filter((tool) => selectedIds.includes(tool.id));
  };

  const ComparisonTable = ({
    bottleneckId,
    tools,
  }: {
    bottleneckId: number;
    tools: any[];
  }) => {
    if (!showComparison[bottleneckId] || tools.length < 2) return null;
    return (
      <div className="mt-6 bg-orange-50 border border-orange-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-gray-900">Tool Comparison</h4>
          <button
            onClick={() =>
              setShowComparison((prev) => ({ ...prev, [bottleneckId]: false }))
            }
            className="text-orange-600 hover:text-orange-700 text-sm font-medium"
          >
            <i className="ri-close-line mr-1"></i>
            Collapse
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-orange-200">
                <th className="text-left py-3 px-4 font-semibold text-gray-900">
                  Feature
                </th>
                {tools.map((tool) => (
                  <th
                    key={tool.id}
                    className="text-left py-3 px-4 font-semibold text-gray-900"
                  >
                    {tool.title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Pricing</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison.pricing}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Ease of Use</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison.easeOfUse}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Features</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison.features}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Support</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison.support}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-orange-100">
                <td className="py-3 px-4 font-medium text-gray-700">Integration</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison.integration}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="py-3 px-4 font-medium text-gray-700">Learning Curve</td>
                {tools.map((tool) => (
                  <td
                    key={tool.id}
                    className="py-3 px-4 text-gray-600"
                  >
                    {tool.comparison.learningCurve}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* Toast Notification */}
      {showToast && (
        <div className="fixed top-4 right-4 z-50 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-fade-in">
          <i className="ri-check-circle-line text-xl"></i>
          <span className="font-medium">
            Solution implemented! +15 points added
          </span>
        </div>
      )}
    

      <div className="bg-gradient-to-br from-orange-50 to-white">

          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <p className="text-gray-600 mt-2 text-right">
              Generated on {new Date().toLocaleDateString()}
        </p>
      </div>
      <div className="flex space-x-3 justify-end">
        <button className="bg-orange-500 text-white px-6 py-2 rounded-lg hover:bg-orange-600 transition-colors duration-200 flex items-center space-x-2 whitespace-nowrap">
          <i className="ri-download-line"></i>
          <span>Download Report</span>
        </button>
        <button
          onClick={() => navigate('/analysis-history')}
          className="bg-white text-gray-700 border border-gray-300 px-6 py-2 rounded-lg hover:bg-gray-50 transition-colors duration-200 flex items-center space-x-2 whitespace-nowrap"
        >
          <i className="ri-history-line"></i>
          <span>Analysis History</span>
        </button>
      </div>
   
      
        {/* Hero Section */}
        <section className="bg-gradient-to-br from-orange-50 to-white pt-10 sm:pt-12 md:pt-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-6 sm:mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-green-100 rounded-full mb-4 sm:mb-6">
                <i className="ri-check-line text-green-500 text-2xl sm:text-3xl"></i>
              </div>
              <h1 className="text-3xl sm:text-4xl  font-bold text-black mb-3 sm:mb-4 px-2">
                Your AI Strategy is Ready!
              </h1>
              <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl mx-auto px-4">
                Based on your business profile, we've identified various AI solutions 
                that can transform your operations and drive growth.
              </p>
            </div>

          </div>
        </section>

        
       {/* Navigation Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-8">
          <div className="border-b border-gray-200">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'bottlenecks', label: 'Bottlenecks', icon: 'ri-error-warning-line' },
                { id: 'solutions', label: 'Solutions', icon: 'ri-lightbulb-line' },
                { id: 'efficiency-tools', label: 'Efficiency Tools', icon: 'ri-robot-line' },
                { id: 'roadmap', label: 'Roadmap', icon: 'ri-roadster-line' },
                { id: 'roi', label: 'ROI Impact', icon: 'ri-line-chart-line' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-orange-500 text-orange-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <i className={tab.icon}></i>
                  <span>{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          {/* Bottlenecks Tab */}
          {activeTab === 'bottlenecks' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Diagnosed Bottlenecks
              </h2>
              <div className="space-y-6">
                {bottlenecks.map((bottleneck, index) => (
                  <div
                    key={bottleneck.id}
                    className="border-l-4 border-orange-500 bg-orange-50 p-6 rounded-r-lg">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <span className="bg-orange-100 text-orange-800 text-sm font-medium px-2.5 py-0.5 rounded">
                            #{index + 1}
                          </span>
                          <span
                            className={`text-xs font-semibold px-2 py-1 rounded ${
                              bottleneck.priority === 'HIGH'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {bottleneck.priority} PRIORITY
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                          {bottleneck.title}
                        </h3>
                        <p className="text-gray-600 mb-3">{bottleneck.description}</p>
                        <div className="text-sm text-gray-500">
                          <strong>Impact:</strong> {bottleneck.impact}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Solutions Tab */}
          {activeTab === 'solutions' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Business Strategy Solutions
              </h2>

              {/* Iterate over each bottleneck */}
              {bottlenecks.map((b) => (
                <div key={b.id} className="mb-12">
                  <h3 className="text-xl font-semibold text-gray-800 mb-6">
                    Strategies for: {b.title}
                  </h3>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {getCurrentStrategies()
                      .filter((s) => s.bottleneckId === b.id)
                      .map((strategy) => (
                        <div
                          key={strategy.id}
                          className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow duration-200 bg-white"
                        >
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center space-x-2">
                              <i className="ri-strategy-line text-orange-500 text-xl"></i>
                              <h4 className="text-lg font-semibold text-gray-900">
                                {strategy.title}
                              </h4>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-orange-600">
                                {strategy.price}
                              </div>
                              <div className="text-sm text-orange-600 bg-orange-100 px-2 py-1 rounded mt-1">
                                {strategy.rating}
                              </div>
                            </div>
                          </div>

                          <p className="text-gray-600 mb-4">{strategy.description}</p>

                          <div className="mb-4">
                            <h5 className="font-medium text-gray-900 mb-2">
                              Features:
                            </h5>
                            <ul className="space-y-1">
                              {strategy.features.map((feature, idx) => (
                                <li
                                  key={idx}
                                  className="flex items-center space-x-2 text-sm text-gray-600"
                                >
                                  <i className="ri-check-line text-orange-500 text-xs"></i>
                                  <span>{feature}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                              <h5 className="font-medium text-gray-900 mb-2 text-sm">
                                Pros:
                              </h5>
                              <ul className="space-y-1">
                                {strategy.pros.map((pro, idx) => (
                                  <li key={idx} className="text-xs text-gray-600">
                                    • {pro}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <h5 className="font-medium text-gray-900 mb-2 text-sm">
                                Cons:
                              </h5>
                              <ul className="space-y-1">
                                {strategy.cons.map((con, idx) => (
                                  <li key={idx} className="text-xs text-gray-600">
                                    • {con}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>

                          <div className="flex space-x-3">
                            <button className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors duration-200 text-sm font-medium whitespace-nowrap">
                              Learn More
                            </button>
                            <button
                              onClick={() => handleImplemented(strategy.id)}
                              disabled={implementedSolutions.has(strategy.id)}
                              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors duration-200 whitespace-nowrap ${
                                implementedSolutions.has(strategy.id)
                                  ? 'bg-green-100 text-green-700 cursor-not-allowed'
                                  : 'bg-orange-500 text-white hover:bg-orange-600'
                              }`}
                            >
                              {implementedSolutions.has(strategy.id) ? (
                                <span className="flex items-center justify-center space-x-1">
                                  <i className="ri-check-line"></i>
                                  <span>Implemented</span>
                                </span>
                              ) : (
                                'Implement'
                              )}
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          )}


          {/* Efficiency Tools Tab */}
          {activeTab === 'efficiency-tools' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                AI Efficiency Tools
              </h2>

              {/* Iterate over each bottleneck */}
              {bottlenecks.map((b) => (
                <div key={b.id} className="mb-12">
                  <h3 className="text-xl font-semibold text-gray-800 mb-6">
                    AI Tools for: {b.title}
                  </h3>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {getCurrentTools()
                      .filter((tool) => tool.bottleneckId === b.id)
                      .map((tool) => (
                        <div
                          key={tool.id}
                          className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow duration-200 bg-white"
                        >
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                checked={selectedTools[b.id]?.includes(tool.id) || false}
                                onChange={() => handleToolSelection(b.id, tool.id)}
                                className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 focus:ring-2"
                              />
                              <i className="ri-robot-line text-orange-500 text-xl"></i>
                              <h4 className="text-lg font-semibold text-gray-900">
                                {tool.title}
                              </h4>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-orange-600">
                                {tool.price}
                              </div>
                              <div className="text-sm text-orange-600 bg-orange-100 px-2 py-1 rounded mt-1">
                                {tool.rating}
                              </div>
                            </div>
                          </div>

                          <p className="text-gray-600 mb-4">{tool.description}</p>

                          <div className="mb-4">
                            <h5 className="font-medium text-gray-900 mb-2">
                              Features:
                            </h5>
                            <ul className="space-y-1">
                              {tool.features.map((feature, idx) => (
                                <li
                                  key={idx}
                                  className="flex items-center space-x-2 text-sm text-gray-600"
                                >
                                  <i className="ri-check-line text-orange-500 text-xs"></i>
                                  <span>{feature}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                              <h5 className="font-medium text-gray-900 mb-2 text-sm">
                                Pros:
                              </h5>
                              <ul className="space-y-1">
                                {tool.pros.map((pro, idx) => (
                                  <li key={idx} className="text-xs text-gray-600">
                                    • {pro}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <h5 className="font-medium text-gray-900 mb-2 text-sm">
                                Cons:
                              </h5>
                              <ul className="space-y-1">
                                {tool.cons.map((con, idx) => (
                                  <li key={idx} className="text-xs text-gray-600">
                                    • {con}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>

                          <div className="flex space-x-3">
                            <button className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors duration-200 text-sm font-medium whitespace-nowrap">
                              Learn More
                            </button>
                            <button
                              onClick={() => handleImplemented(tool.id + 100)}
                              disabled={implementedSolutions.has(tool.id + 100)}
                              className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors duration-200 whitespace-nowrap ${
                                implementedSolutions.has(tool.id + 100)
                                  ? 'bg-green-100 text-green-700 cursor-not-allowed'
                                  : 'bg-orange-500 text-white hover:bg-orange-600'
                              }`}
                            >
                              {implementedSolutions.has(tool.id + 100) ? (
                                <span className="flex items-center justify-center space-x-1">
                                  <i className="ri-check-line"></i>
                                  <span>Implemented</span>
                                </span>
                              ) : (
                                'Implement'
                              )}
                            </button>
                          </div>
                        </div>
                      ))}
                  </div>

                  {/* Comparison Table */}
                  <ComparisonTable
                    bottleneckId={b.id}
                    tools={getSelectedToolsForBottleneck(b.id)}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Roadmap Tab */}
          {activeTab === 'roadmap' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                Implementation Roadmap
              </h2>
              <p className="text-gray-600 mb-8">
                Follow these steps in order for maximum impact based on your identified solutions and efficiency tools
              </p>

              <div className="space-y-6">
                {/* Step 1 - Content Marketing Strategy */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      1
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Implement Content Marketing Strategy
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          medium
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          2-3 weeks
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Set up blog content creation, social media campaigns, and SEO optimization to improve online visibility.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 2 - SEMrush Setup */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      2
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Deploy SEMrush for SEO Optimization
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          easy
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          1 week
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Set up SEMrush account, conduct keyword research, and implement automated site audit recommendations.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 3 - Jasper AI Content Creation */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      3
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Integrate Jasper AI for Content Creation
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          easy
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          1 week
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Set up Jasper AI, train brand voice, and create content calendar for consistent marketing output.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 4 - Customer Journey Mapping */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      4
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Redesign Customer Onboarding Journey
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          hard
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          3-4 weeks
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Conduct user experience audit, map customer touchpoints, and streamline onboarding process.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 5 - Intercom Implementation */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      5
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Deploy Intercom for Customer Support
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          medium
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          2 weeks
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Set up AI chatbot, create automated onboarding flows, and implement smart user segmentation.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 6 - Payment Optimization */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      6
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Optimize Payment Experience
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          medium
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          2-3 weeks
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Redesign checkout flow, integrate multiple payment methods, and enhance mobile optimization.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 7 - Stripe Radar & PayPal Setup */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      7
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Implement AI Payment Security
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          easy
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          1 week
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Deploy Stripe Radar for fraud detection and PayPal Advanced for payment optimization.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>

                {/* Step 8 - Monitor and Optimize */}
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-orange-500 text-white rounded-full flex items-center justify-center font-bold text-lg">
                      8
                    </div>
                  </div>
                  <div className="flex-1 bg-white border border-gray-200 rounded-lg p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Monitor Performance & Optimize
                      </h3>
                      <div className="flex items-center space-x-3">
                        <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">
                          easy
                        </span>
                        <div className="flex items-center text-sm text-gray-500">
                          <i className="ri-time-line mr-1"></i>
                          ongoing
                        </div>
                      </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                      Track KPIs, analyze performance data, and continuously optimize based on AI tool insights.
                    </p>
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      <i className="ri-check-line mr-1"></i>
                      Mark Complete (+25 pts)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ROI Tab */}
          {activeTab === 'roi' && (
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">
                ROI Impact Analysis
              </h2>
              <p className="text-gray-600 mb-8">
                Projected financial impact of implementing the recommended solutions and efficiency tools
              </p>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                {/* Revenue Impact Card */}
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <div className="flex items-center mb-4">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-line-chart-line text-green-600"></i>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900">Revenue Impact</h3>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Monthly Cost Savings</p>
                      <p className="text-2xl font-bold text-green-600">$200</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Monthly Revenue Increase</p>
                      <p className="text-2xl font-bold text-green-600">$1,000</p>
                    </div>
                    <div className="border-t border-gray-200 pt-4">
                      <p className="text-sm text-gray-600 mb-1">Total Monthly Impact</p>
                      <p className="text-3xl font-bold text-green-600">$1,200</p>
                    </div>
                  </div>
                </div>

                {/* Investment & ROI Card */}
                <div className="bg-white border border-gray-200 rounded-lg p-6">
                  <div className="flex items-center mb-4">
                    <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center mr-3">
                      <i className="ri-money-dollar-circle-line text-orange-600"></i>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900">Investment & ROI</h3>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-600 mb-1">Implementation Cost</p>
                      <p className="text-2xl font-bold text-orange-600">$500</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 mb-1">ROI Timeline</p>
                      <p className="text-2xl font-bold text-orange-600">3-6 months</p>
                    </div>
                    <div className="border-t border-gray-200 pt-4">
                      <p className="text-sm text-gray-600 mb-1">12-Month Projected Gain</p>
                      <p className="text-3xl font-bold text-orange-600">$13,900</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* AI Confidence Score */}
              <div className="bg-white border border-gray-200 rounded-lg p-8 text-center">
                <div className="w-24 h-24 bg-purple-500 text-white rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold">85%</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Confidence Score</h3>
                <p className="text-gray-600 max-w-2xl mx-auto">
                  Based on market data, competitor analysis, and implementation complexity, our AI is 85% confident these recommendations will deliver results.
                </p>
              </div>

              {/* Detailed Breakdown */}
              <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6">
                <h4 className="text-lg font-semibold text-gray-900 mb-4">Detailed ROI Breakdown</h4>
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-600">Content Marketing Strategy</span>
                    <span className="font-semibold text-green-600">+$400/month</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-600">SEMrush Implementation</span>
                    <span className="font-semibold text-green-600">+$300/month</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-600">Customer Journey Optimization</span>
                    <span className="font-semibold text-green-600">+$350/month</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-gray-600">Payment Experience Enhancement</span>
                    <span className="font-semibold text-green-600">+$150/month</span>
                  </div>
                  <div className="flex justify-between items-center py-2 pt-4 border-t-2 border-gray-200">
                    <span className="font-semibold text-gray-900">Total Monthly Impact</span>
                    <span className="font-bold text-green-600 text-lg">+$1,200/month</span>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

           {/* CTA Section */}
      <section className="py-10 sm:py-12 md:py-16 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4 sm:mb-6 text-black">
            Ready to Get Started?
          </h2>
          <p className="text-base sm:text-lg md:text-xl mb-6 sm:mb-8 text-gray-600 px-4">
            Our team of AI implementation experts is ready to help you bring these recommendations to life.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center">
            <Button variant="primary" size="lg" className="w-full sm:w-auto text-base sm:text-lg px-6 sm:px-8">
              <i className="ri-calendar-line mr-2"></i>
              Schedule Consultation
            </Button>
            <Button variant="outline" size="lg" className="w-full sm:w-auto text-base sm:text-lg px-6 sm:px-8">
              <i className="ri-download-line mr-2"></i>
              Download Report
            </Button>
          </div>
        </div>
      </section>
        </div>

    </div>
  );


          

       


  
}
