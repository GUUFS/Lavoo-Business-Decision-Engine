
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../../../components/base/Button';
import { analyzeBusinessGoal, getUserAnalyses } from '../../../api/business-analyzer';
import toast from 'react-hot-toast';

export default function Analyze() {

  const [activeTab, setActiveTab] = useState('New Analysis');

  const navigate = useNavigate();
  const [businessPrompt, setBusinessPrompt] = useState("")

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [previousAnalyses, setPreviousAnalyses] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  // Fetch previous analyses on mount
  useEffect(() => {
    const fetchPreviousAnalyses = async () => {
      try {
        const analyses = await getUserAnalyses(4); // Get last 4 analyses
        console.log('📊 Fetched analyses:', analyses);
        console.log('📊 First analysis structure:', analyses[0]);
        setPreviousAnalyses(analyses);
      } catch (error) {
        console.error('Error fetching previous analyses:', error);
      } finally {
        setLoadingHistory(false);
      }
    };

    fetchPreviousAnalyses();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!businessPrompt.trim() || businessPrompt.trim().length < 10) {
      toast.error('Please provide more details about your business (at least 10 characters)');
      return;
    }

    setIsSubmitting(true);

    try {
      // Call the backend API to analyze the business goal
      const analysisResult = await analyzeBusinessGoal(businessPrompt);

      toast.success('Analysis completed successfully!');

      // Navigate to results page with the analysis data
      navigate('/results', {
        state: { analysis: analysisResult }
      });
    } catch (error: any) {
      console.error('Analysis error:', error);

      // Handle authentication errors
      if (error.message.includes('Not authenticated') || error.message.includes('login')) {
        toast.error('Session expired. Please login again.');
        // Redirect to login after a delay
        setTimeout(() => {
          navigate('/login', { state: { from: '/dashboard/analyze' } });
        }, 2000);
      } else {
        toast.error(error.message || 'Failed to analyze business goal. Please try again.');
      }

      setIsSubmitting(false);
    }
  };



  return (
        <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
       <div className="flex-1">
          {/* Hero Section */}
          <section className="bg-gradient-to-br from-orange-50 to-white py-10 sm:py-12 md:py-16">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-black mb-4 sm:mb-6 px-2">
                Tell Us About Your Business
              </h1>
              <p className="text-base sm:text-lg md:text-xl text-gray-600 mb-6 sm:mb-8 px-4">
                The more details you provide, the more accurate and personalized your AI strategy will be.
                This analysis takes just 2-3 minutes to complete.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6 text-xs sm:text-sm text-gray-500">
                <div className="flex items-center">
                  <i className="ri-shield-check-line text-green-500 mr-2"></i>
                  100% Secure
                </div>
                <div className="flex items-center">
                  <i className="ri-time-line text-green-500 mr-2"></i>
                  2-3 Minutes
                </div>
                <div className="flex items-center">
                  <i className="ri-gift-line text-green-500 mr-2"></i>
                  Completely Free
                </div>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex justify-center mt-8" >
              <div className="flex space-x-1 bg-white rounded-lg p-1 shadow-sm border border-gray-200">
                <button
                  onClick={() => setActiveTab('New Analysis')}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap ${
                    activeTab === 'New Analysis'
                      ? 'bg-orange-500 text-white'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  New Analysis
                </button>
                <button
                  onClick={() => navigate('/analysis-history')}
                  className="px-4 py-2 text-sm font-medium rounded-md text-gray-600 hover:text-gray-900 transition-colors whitespace-nowrap"
                >
                  Analysis History
                </button>
              </div>
            </div>
          </section>

          {/* Form Section */}
          <section className="py-10 sm:py-12 md:pb-16 md:pt-0">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
              <form onSubmit={handleSubmit} className="space-y-6 sm:space-y-8 mb-12">
                {/* Company Information */}
                <div className="bg-white rounded-2xl  shadow-lg border border-gray-100">
                  {/* Business Details */}
                  {/* ChatGPT-like Input Box */}
                  <div className="w-full flex flex-col items-center">
                    <div className="w-full  bg-white  rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200">
                      <textarea
                        value={businessPrompt}
                        onChange={(e) => setBusinessPrompt(e.target.value)}
                        placeholder="Example: I run a digital marketing agency with 5 clients. My biggest challenges include; scaling client acquisition without
                                     increasing ad spend, automating repetitive reporting tasks that take 10+ hours/week and improving content creation speed for
                                     social media. Current monthly revenue is $10k and I would love this to increase to about $50k within 3 months. How can i
                                     make this happen?"
                        rows={5}
                        className="w-full bg-transparent p-4 text-gray-700 text-base focus:outline-none resize-none placeholder:text-gray-400"/>

                        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                          <div className="text-sm text-gray-400">
                            {businessPrompt.length} characters
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                {/* Submit Button */}
                <div className="flex flex-col sm:flex-row justify-center gap-4 pt-4">
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    disabled={isSubmitting}
                    className="w-full sm:w-auto text-base sm:text-lg px-8 sm:px-12 py-3 sm:py-4">
                    {isSubmitting ? (
                      <>
                        <i className="ri-loader-4-line mr-2 animate-spin"></i>
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <i className="ri-rocket-line mr-2"></i>
                        Generate My Strategy
                      </>
                    )}
                  </Button>
                </div>
              </form>

              {/* Previous Reports Section */}
              {loadingHistory && (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500 mx-auto"></div>
                  <p className="text-gray-600 mt-2">Loading previous analyses...</p>
                </div>
              )}

              {!loadingHistory && previousAnalyses.length > 0 && (
                <div className="mt-8">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-gray-900">Your Previous Reports</h2>
                    <button
                      onClick={() => navigate('/analysis-history')}
                      className="text-orange-600 hover:text-orange-700 font-medium text-sm flex items-center"
                    >
                      View All
                      <i className="ri-arrow-right-line ml-1"></i>
                    </button>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {previousAnalyses.map((analysis) => {
                      const analysisDate = new Date(analysis.created_at || Date.now()).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      });

                      // Calculate metrics from analysis data
                      const bottlenecksCount = analysis.bottlenecks?.length || 0;
                      const solutionsCount = (analysis.business_strategies?.length || 0) + (analysis.ai_tools?.length || 0);
                      const confidenceScore = analysis.ai_confidence_score || 85;
                      const analysisId = analysis.analysis_id || analysis.id;

                      return (
                        <div key={analysisId} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
                          onClick={() => navigate(`/results?id=${analysisId}`)}>
                          <div className="flex items-start justify-between mb-3">
                            <h3 className="font-semibold text-gray-900 text-sm">
                              Business Analysis
                            </h3>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              confidenceScore >= 90 ? 'bg-green-100 text-green-700' :
                              confidenceScore >= 85 ? 'bg-blue-100 text-blue-700' :
                              'bg-yellow-100 text-yellow-700'
                            }`}>
                              {confidenceScore}% confidence
                            </span>
                          </div>
                          <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                            {analysis.objective || analysis.business_goal || 'Business analysis report'}
                          </p>
                          <div className="flex items-center justify-between text-xs text-gray-500 mb-4 pb-4 border-b border-gray-100">
                            <span className="flex items-center">
                              <i className="ri-calendar-line mr-1"></i>
                              {analysisDate}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center space-x-4 text-gray-600">
                              <span className="flex items-center">
                                <i className="ri-alert-line mr-1 text-orange-500"></i>
                                {bottlenecksCount} issues
                              </span>
                              <span className="flex items-center">
                                <i className="ri-lightbulb-line mr-1 text-blue-500"></i>
                                {solutionsCount} solutions
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {!loadingHistory && previousAnalyses.length === 0 && (
                <div className="text-center py-12 bg-white border border-gray-200 rounded-lg mt-8">
                  <i className="ri-file-list-3-line text-4xl text-gray-400 mb-3"></i>
                  <p className="text-gray-600 mb-2">No previous analyses yet</p>
                  <p className="text-sm text-gray-500">Your analysis reports will appear here once you create them</p>
                </div>
              )}
            </div>
          </section>
        </div>
    </div>
  );
}

