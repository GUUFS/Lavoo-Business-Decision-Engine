
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
/*import Header from '../../../components/feature/Header';*/
/*import Footer from '../../../components/feature/Footer';*/
import Button from '../../../components/base/Button';

export default function Analyze() {
 
  const [activeTab, setActiveTab] = useState('New Analysis');

  const navigate = useNavigate();
  const [businessPrompt, setBusinessPrompt] = useState("")

  const [isSubmitting, setIsSubmitting] = useState(false);

 

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    setTimeout(() => {
      setIsSubmitting(false);
      navigate('/results', { state: { businessPrompt } });
    }, 2000);
  };

    // Mock previous analysis data
  const previousAnalyses = [
    {
      id: 1,
      title: 'Business Analysis - 11/5/2025',
      date: '11/5/2025',
      description: 'I sell soaps and would want to increase visibility and sales for my business',
      bottlenecks: 5,
      solutions: 3,
      confidence: '85%',
      status: 'completed'
    },
    {
      id: 2,
      title: 'Business Analysis - 11/5/2025',
      date: '11/5/2025',
      description: 'I am a content creator and I want to make my audience laugh',
      bottlenecks: 5,
      solutions: 5,
      confidence: '90%',
      status: 'completed'
    }
  ];

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
              <form onSubmit={handleSubmit} className="space-y-6 sm:space-y-8">
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
            </div>
          </section>

           {/* Previous Reports Section */}
            <div className="mb-8">
              <h2 className="text-xl font-bold text-gray-900 mb-6">Your Previous Reports</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {previousAnalyses.map((analysis) => (
                  <div key={analysis.id} className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="font-semibold text-gray-900 text-sm">{analysis.title}</h3>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        analysis.confidence === '85%' 
                          ? 'bg-purple-100 text-purple-700' 
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {analysis.confidence} confidence
                      </span>
                    </div>
                    <p className="text-gray-600 text-sm mb-4 line-clamp-2">{analysis.description}</p>
                    <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
                      <span>{analysis.date}</span>
                      <div className="flex items-center space-x-4">
                        <span>{analysis.bottlenecks} bottlenecks</span>
                        <span>{analysis.solutions} solutions</span>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate('/results', { state: { businessPrompt: analysis.description } })}
                      className="w-full text-orange-600 hover:text-orange-700 font-medium text-sm flex items-center justify-center py-2 border border-orange-200 rounded-md hover:bg-orange-50 transition-colors whitespace-nowrap"
                    >
                      View Report
                      <i className="ri-arrow-right-line ml-2"></i>
                    </button>
                  </div>
                ))}
              </div>
            </div>
        </div>
    </div>
  );
}

