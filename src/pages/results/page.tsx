
import { useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Header from '../../components/feature/Header';
import Footer from '../../components/feature/Footer';
import Button from '../../components/base/Button';
import type { ToolRecommendation, SwotAnalysis, BusinessAnalysisRequest } from '../../api/business';
import { compareTools } from '../../api/business';

// Interface for the data we receive from Analyze page
interface ResultsState {
  analysisResult: {
    topRecommendation: ToolRecommendation;
    recommendations: ToolRecommendation[];
    swot: SwotAnalysis;
    formData: BusinessAnalysisRequest;
  };
}

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Get the analysis result from navigation state
  const state = location.state as ResultsState | null;
  const analysisResult = state?.analysisResult;

  // If no data, redirect back to analyze page
  useEffect(() => {
    if (!analysisResult) {
      navigate('/analyze');
    }
  }, [analysisResult, navigate]);

  // Show nothing while redirecting
  if (!analysisResult) {
    return null;
  }

  const { topRecommendation, recommendations, swot, formData } = analysisResult;

  // State for tool comparison
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<Record<string, any> | null>(null);
  const [isLoadingComparison, setIsLoadingComparison] = useState(false);

  // Handle checkbox toggle
  const handleToolSelect = (toolName: string) => {
    setSelectedTools(prev => {
      if (prev.includes(toolName)) {
        // Unselect
        return prev.filter(t => t !== toolName);
      } else if (prev.length < 4) {
        // Select (max 4)
        return [...prev, toolName];
      }
      return prev; // Already 4 selected
    });
  };

  // Fetch comparison when tools are selected
  useEffect(() => {
    if (selectedTools.length >= 2) {
      setIsLoadingComparison(true);
      compareTools(selectedTools)
        .then(data => {
          setComparisonData(data);
          setIsLoadingComparison(false);
        })
        .catch(err => {
          console.error('Comparison error:', err);
          setIsLoadingComparison(false);
        });
    } else {
      setComparisonData(null);
    }
  }, [selectedTools]);

  // Helper function to assign priority based on similarity score
  const getPriorityFromScore = (score: number): string => {
    if (score > 0.4) return 'High';
    if (score > 0.25) return 'Medium';
    return 'Low';
  };

  // Helper function to generate realistic cost estimate
  const estimateCost = (priority: string): string => {
    const costs = {
      High: '$500-1500/month',
      Medium: '$200-800/month',
      Low: '$50-300/month',
    };
    return costs[priority as keyof typeof costs] || '$100-500/month';
  };

  // Helper function to estimate implementation timeline
  const estimateTimeline = (priority: string): string => {
    const timelines = {
      High: '3-6 weeks',
      Medium: '2-4 weeks',
      Low: '1-2 weeks',
    };
    return timelines[priority as keyof typeof timelines] || '2-4 weeks';
  };

  // Helper function to estimate ROI
  const estimateROI = (priority: string): string => {
    const roi = {
      High: '250% in 6 months',
      Medium: '180% in 8 months',
      Low: '120% in 12 months',
    };
    return roi[priority as keyof typeof roi] || '150% in 9 months';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'High':
        return 'bg-red-100 text-red-700';
      case 'Medium':
        return 'bg-yellow-100 text-yellow-700';
      case 'Low':
        return 'bg-green-100 text-green-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white">
      <Header />
      
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-orange-50 to-white py-10 sm:py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-6 sm:mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-green-100 rounded-full mb-4 sm:mb-6">
              <i className="ri-check-line text-green-500 text-2xl sm:text-3xl"></i>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-black mb-3 sm:mb-4 px-2">
              Your AI Strategy is Ready!
            </h1>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl mx-auto px-4">
              Based on your business profile, we've identified {recommendations.length} AI solutions 
              that can transform your operations and drive growth.
            </p>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mt-8 sm:mt-10">
            <div className="bg-white rounded-xl p-4 sm:p-6 shadow-lg border border-gray-100">
              <div className="text-2xl sm:text-3xl font-bold text-orange-500 mb-2">
                {recommendations.length + 1}
              </div>
              <div className="text-sm sm:text-base text-gray-600">AI Tools Recommended</div>
            </div>
            <div className="bg-white rounded-xl p-4 sm:p-6 shadow-lg border border-gray-100">
              <div className="text-2xl sm:text-3xl font-bold text-orange-500 mb-2">
                {formData.industry}
              </div>
              <div className="text-sm sm:text-base text-gray-600">Industry Focus</div>
            </div>
            <div className="bg-white rounded-xl p-4 sm:p-6 shadow-lg border border-gray-100">
              <div className="text-2xl sm:text-3xl font-bold text-orange-500 mb-2">
                {formData.companySize}
              </div>
              <div className="text-sm sm:text-base text-gray-600">Company Size</div>
            </div>
            <div className="bg-white rounded-xl p-4 sm:p-6 shadow-lg border border-gray-100">
              <div className="text-2xl sm:text-3xl font-bold text-orange-500 mb-2">
                {(topRecommendation.similarity_score * 100).toFixed(0)}%
              </div>
              <div className="text-sm sm:text-base text-gray-600">Top Match Score</div>
            </div>
          </div>
        </div>
      </section>

      {/* Top Recommendation - Hero Section */}
      <section className="py-10 sm:py-12 md:py-16 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-6 sm:mb-8">
            <div className="flex items-center gap-2 mb-3">
              <i className="ri-trophy-line text-3xl text-orange-500"></i>
              <h2 className="text-2xl sm:text-3xl font-bold text-black">
                #1 Recommended Solution
              </h2>
            </div>
            <p className="text-base sm:text-lg text-gray-600">
              Our AI has identified this as the perfect match for your business needs
            </p>
          </div>

          {/* Hero Card - Top Recommendation */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 lg:p-10 shadow-2xl border-2 border-orange-200 hover:shadow-3xl transition-all duration-300">
            <div className="flex flex-col lg:flex-row gap-6">
              {/* Left Side - Main Info */}
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-3 mb-4">
                  <span className="px-4 py-2 rounded-full text-sm font-bold bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg">
                    🏆 BEST MATCH
                  </span>
                  <span className="px-4 py-2 rounded-full text-sm font-semibold bg-green-100 text-green-700">
                    {(topRecommendation.similarity_score * 100).toFixed(0)}% Match Score
                  </span>
                  <span className={`px-4 py-2 rounded-full text-sm font-semibold ${getPriorityColor(getPriorityFromScore(topRecommendation.similarity_score))}`}>
                    {getPriorityFromScore(topRecommendation.similarity_score)} Priority
                  </span>
                </div>
                
                <h3 className="text-3xl sm:text-4xl font-bold text-black mb-4">
                  {topRecommendation.tool_name}
                </h3>
                
                <p className="text-base sm:text-lg text-gray-700 leading-relaxed mb-6">
                  {topRecommendation.description}
                </p>

                {/* Key Benefits */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0">
                      <i className="ri-rocket-line text-orange-600"></i>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">Quick Implementation</div>
                      <div className="text-sm text-gray-600">{estimateTimeline(getPriorityFromScore(topRecommendation.similarity_score))}</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                      <i className="ri-line-chart-line text-green-600"></i>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">Expected ROI</div>
                      <div className="text-sm text-gray-600">{estimateROI(getPriorityFromScore(topRecommendation.similarity_score))}</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                      <i className="ri-money-dollar-circle-line text-blue-600"></i>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">Estimated Cost</div>
                      <div className="text-sm text-gray-600">{estimateCost(getPriorityFromScore(topRecommendation.similarity_score))}</div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0">
                      <i className="ri-star-line text-purple-600"></i>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900">Priority Level</div>
                      <div className="text-sm text-gray-600">{getPriorityFromScore(topRecommendation.similarity_score)}</div>
                    </div>
                  </div>
                </div>

                <Button variant="primary" size="lg" className="w-full sm:w-auto">
                  <i className="ri-information-line mr-2"></i>
                  Learn More About {topRecommendation.tool_name}
                </Button>
              </div>

              {/* Right Side - Why This Tool Card */}
              <div className="lg:w-80 bg-gradient-to-br from-orange-50 to-orange-100 rounded-2xl p-6">
                <h4 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <i className="ri-lightbulb-line text-orange-600"></i>
                  Why This Tool?
                </h4>
                <ul className="space-y-3">
                  <li className="flex items-start gap-3">
                    <i className="ri-check-line text-green-600 text-xl flex-shrink-0 mt-0.5"></i>
                    <span className="text-sm text-gray-700">Perfect alignment with your {formData.industry} industry needs</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <i className="ri-check-line text-green-600 text-xl flex-shrink-0 mt-0.5"></i>
                    <span className="text-sm text-gray-700">Scales well for {formData.companySize} organizations</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <i className="ri-check-line text-green-600 text-xl flex-shrink-0 mt-0.5"></i>
                    <span className="text-sm text-gray-700">Addresses your key challenge: {formData.currentChallenges.substring(0, 80)}...</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <i className="ri-check-line text-green-600 text-xl flex-shrink-0 mt-0.5"></i>
                    <span className="text-sm text-gray-700">Supports your goal: {formData.goals.substring(0, 80)}...</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Other Recommendations - Comparison Section */}
      <section className="py-10 sm:py-12 md:py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8 sm:mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-black mb-3 sm:mb-4">
              Compare Alternative Solutions
            </h2>
            <p className="text-base sm:text-lg text-gray-600 mb-4">
              Select up to 4 tools to compare their features side-by-side
            </p>
            {selectedTools.length > 0 && (
              <div className="flex items-center gap-2 text-sm text-orange-600 font-medium">
                <i className="ri-checkbox-circle-line"></i>
                {selectedTools.length} tool{selectedTools.length > 1 ? 's' : ''} selected for comparison
              </div>
            )}
          </div>

          {/* Comparison Grid with Checkboxes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
            {recommendations.map((rec, index) => {
              const priority = getPriorityFromScore(rec.similarity_score);
              const cost = estimateCost(priority);
              const timeline = estimateTimeline(priority);
              const roi = estimateROI(priority);
              const isSelected = selectedTools.includes(rec.tool_name);
              const isDisabled = !isSelected && selectedTools.length >= 4;
              
              return (
                <div
                  key={`${rec.tool_name}-${index}`}
                  className={`bg-white rounded-2xl p-6 sm:p-8 shadow-lg border-2 transition-all duration-200 ${
                    isSelected 
                      ? 'border-orange-400 shadow-xl' 
                      : 'border-gray-100 hover:shadow-xl'
                  } ${isDisabled ? 'opacity-60' : ''}`}
                >
                  {/* Checkbox Header */}
                  <div className="flex items-start gap-4 mb-4">
                    <div className="flex items-center h-8">
                      <input
                        type="checkbox"
                        id={`tool-${rec.tool_name}`}
                        checked={isSelected}
                        onChange={() => handleToolSelect(rec.tool_name)}
                        disabled={isDisabled}
                        className="w-5 h-5 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 focus:ring-2 cursor-pointer disabled:cursor-not-allowed"
                      />
                    </div>
                    <label 
                      htmlFor={`tool-${rec.tool_name}`}
                      className={`flex-1 cursor-pointer ${isDisabled ? 'cursor-not-allowed' : ''}`}
                    >
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <span className={`px-3 py-1 rounded-full text-xs sm:text-sm font-medium ${getPriorityColor(priority)}`}>
                          {priority} Priority
                        </span>
                        <span className="px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-blue-100 text-blue-700">
                          {(rec.similarity_score * 100).toFixed(0)}% Match
                        </span>
                        {isSelected && (
                          <span className="px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-orange-100 text-orange-700">
                            <i className="ri-checkbox-circle-fill mr-1"></i>
                            Selected
                          </span>
                        )}
                      </div>
                      <h3 className="text-xl sm:text-2xl font-bold text-black mb-2">
                        {rec.tool_name}
                      </h3>
                    </label>
                  </div>

                  <p className="text-sm sm:text-base text-gray-600 leading-relaxed mb-6">
                    {rec.description}
                  </p>

                  {/* Quick Stats Grid */}
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-500 mb-1">Timeline</div>
                      <div className="text-sm font-semibold text-black">{timeline}</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-500 mb-1">ROI</div>
                      <div className="text-sm font-semibold text-black">{roi}</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-500 mb-1">Cost</div>
                      <div className="text-sm font-semibold text-black">{cost}</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="text-xs text-gray-500 mb-1">Impact</div>
                      <div className="text-sm font-semibold text-black">{priority}</div>
                    </div>
                  </div>

                  <Button 
                    variant="outline" 
                    size="md" 
                    className="w-full"
                  >
                    <i className="ri-information-line mr-2"></i>
                    Learn More
                  </Button>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Comparison Table Section - Shows when tools are selected */}
      {selectedTools.length >= 2 && (
        <section className="py-10 sm:py-12 md:py-16 bg-gradient-to-br from-blue-50 to-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-8">
              <h2 className="text-2xl sm:text-3xl font-bold text-black mb-3 flex items-center gap-3">
                <i className="ri-scales-line text-blue-600"></i>
                Side-by-Side Comparison
              </h2>
              <p className="text-base sm:text-lg text-gray-600">
                Comparing {selectedTools.length} selected tool{selectedTools.length > 1 ? 's' : ''}
              </p>
            </div>

            {isLoadingComparison ? (
              <div className="bg-white rounded-2xl p-12 shadow-lg text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading comparison data...</p>
              </div>
            ) : comparisonData ? (
              <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gradient-to-r from-orange-500 to-orange-600 text-white">
                      <tr>
                        <th className="px-6 py-4 text-left text-sm font-semibold">Feature</th>
                        {Object.keys(comparisonData).map((toolName) => (
                          <th key={toolName} className="px-6 py-4 text-left text-sm font-semibold">
                            {toolName}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {/* Pricing */}
                      <tr className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-gray-900">Pricing</td>
                        {Object.values(comparisonData).map((tool: any, idx) => (
                          <td key={idx} className="px-6 py-4 text-gray-700">
                            {tool.Pricing || 'N/A'}
                          </td>
                        ))}
                      </tr>

                      {/* Rating */}
                      <tr className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-gray-900">Rating</td>
                        {Object.values(comparisonData).map((tool: any, idx) => (
                          <td key={idx} className="px-6 py-4">
                            <span className="inline-flex items-center gap-1 text-orange-600 font-semibold">
                              <i className="ri-star-fill"></i>
                              {tool.Rating || 'N/A'}
                            </span>
                          </td>
                        ))}
                      </tr>

                      {/* Technical Level */}
                      <tr className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-gray-900">Technical Level</td>
                        {Object.values(comparisonData).map((tool: any, idx) => (
                          <td key={idx} className="px-6 py-4 text-gray-700">
                            {tool['Technical Level'] || 'N/A'}
                          </td>
                        ))}
                      </tr>

                      {/* Use Cases */}
                      <tr className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium text-gray-900">Use Cases</td>
                        {Object.values(comparisonData).map((tool: any, idx) => (
                          <td key={idx} className="px-6 py-4 text-gray-700 text-sm">
                            {tool['Use Cases'] || 'N/A'}
                          </td>
                        ))}
                      </tr>

                      {/* Feature Comparison - Boolean features */}
                      {['App Integrations', 'Workflow Automation', 'Triggers and Actions', 
                        'AI-powered Suggestions', 'AI Writing', 'Database', 'Project Tracking', 
                        'Team Collaboration'].map((feature) => (
                        <tr key={feature} className="hover:bg-gray-50">
                          <td className="px-6 py-4 font-medium text-gray-900">{feature}</td>
                          {Object.values(comparisonData).map((tool: any, idx) => (
                            <td key={idx} className="px-6 py-4 text-center">
                              {tool[feature] === 'Yes' || tool[feature] === true ? (
                                <i className="ri-check-line text-2xl text-green-600"></i>
                              ) : tool[feature] === 'No' || tool[feature] === false ? (
                                <i className="ri-close-line text-2xl text-red-400"></i>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Comparison Footer */}
                <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
                  <p className="text-sm text-gray-600 flex items-center gap-2">
                    <i className="ri-information-line text-blue-600"></i>
                    Select or deselect tools above to update this comparison
                  </p>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl p-8 shadow-lg text-center">
                <i className="ri-error-warning-line text-4xl text-gray-400 mb-3"></i>
                <p className="text-gray-600">Unable to load comparison data. Please try again.</p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* SWOT Analysis Section */}
      <section className="py-10 sm:py-12 md:py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-8 sm:mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-black mb-3 sm:mb-4">
              Business Analysis for {formData.industry}
            </h2>
            <p className="text-base sm:text-lg text-gray-600">
              Strategic insights tailored to your industry
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
            {/* Strengths */}
            <div className="bg-gradient-to-br from-green-50 to-white rounded-2xl p-6 sm:p-8 shadow-lg border border-green-100">
              <div className="flex items-center mb-4 sm:mb-6">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-500 rounded-full flex items-center justify-center mr-3 sm:mr-4">
                  <i className="ri-shield-check-line text-white text-lg sm:text-xl"></i>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-black">Strengths</h3>
              </div>
              <ul className="space-y-3">
                {swot.Strengths.slice(0, 3).map((item, index) => (
                  <li key={index} className="flex items-start text-sm sm:text-base text-gray-700">
                    <i className="ri-checkbox-circle-fill text-green-500 mr-2 mt-1 flex-shrink-0"></i>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Weaknesses */}
            <div className="bg-gradient-to-br from-red-50 to-white rounded-2xl p-6 sm:p-8 shadow-lg border border-red-100">
              <div className="flex items-center mb-4 sm:mb-6">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-red-500 rounded-full flex items-center justify-center mr-3 sm:mr-4">
                  <i className="ri-alert-line text-white text-lg sm:text-xl"></i>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-black">Weaknesses</h3>
              </div>
              <ul className="space-y-3">
                {swot.Weaknesses.slice(0, 3).map((item, index) => (
                  <li key={index} className="flex items-start text-sm sm:text-base text-gray-700">
                    <i className="ri-close-circle-fill text-red-500 mr-2 mt-1 flex-shrink-0"></i>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Opportunities */}
            <div className="bg-gradient-to-br from-blue-50 to-white rounded-2xl p-6 sm:p-8 shadow-lg border border-blue-100">
              <div className="flex items-center mb-4 sm:mb-6">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-500 rounded-full flex items-center justify-center mr-3 sm:mr-4">
                  <i className="ri-lightbulb-line text-white text-lg sm:text-xl"></i>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-black">Opportunities</h3>
              </div>
              <ul className="space-y-3">
                {swot.Opportunities.slice(0, 3).map((item, index) => (
                  <li key={index} className="flex items-start text-sm sm:text-base text-gray-700">
                    <i className="ri-arrow-up-circle-fill text-blue-500 mr-2 mt-1 flex-shrink-0"></i>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Threats */}
            <div className="bg-gradient-to-br from-orange-50 to-white rounded-2xl p-6 sm:p-8 shadow-lg border border-orange-100">
              <div className="flex items-center mb-4 sm:mb-6">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-orange-500 rounded-full flex items-center justify-center mr-3 sm:mr-4">
                  <i className="ri-error-warning-line text-white text-lg sm:text-xl"></i>
                </div>
                <h3 className="text-xl sm:text-2xl font-bold text-black">Threats</h3>
              </div>
              <ul className="space-y-3">
                {swot.Threats.slice(0, 3).map((item, index) => (
                  <li key={index} className="flex items-start text-sm sm:text-base text-gray-700">
                    <i className="ri-shield-cross-fill text-orange-500 mr-2 mt-1 flex-shrink-0"></i>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

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

      <Footer />
    </div>
  );
}