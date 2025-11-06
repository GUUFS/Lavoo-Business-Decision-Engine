
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
/*import Header from '../../../components/feature/Header';*/
/*import Footer from '../../../components/feature/Footer';*/
import DashboardSidebar from '../../../components/feature/DashboardSidebar';
import Button from '../../../components/base/Button';
import Input from '../../../components/base/Input';
import Textarea from '../../../components/base/Textarea';
import axios from "axios";

export default function Analyze() {
  const navigate = useNavigate();
  const [businessPrompt, setBusinessPrompt] = useState("")
  const [formData, setFormData] = useState({
    companyName: '',
    industry: '',
    companySize: '',
    businessDescription: '',
    currentChallenges: '',
    goals: '',
    budget: '',
    timeline: '',
    email: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    setTimeout(() => {
      setIsSubmitting(false);
      navigate('/results', { state: { formData } });
    }, 2000);
  };

  return (
        <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white">
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
          </section>

          {/* Form Section */}
          <section className="py-10 sm:py-12 md:py-16">
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
              <form onSubmit={handleSubmit} className="space-y-6 sm:space-y-8">
                {/* Company Information */}
                <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-gray-100">
                  {/* Business Details */}
                  {/* ChatGPT-like Input Box */}
                  <div className="w-full flex flex-col items-center">
                    <div className="w-full max-w-2xl bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200">
                      <textarea
                        value={businessPrompt}
                        onChange={(e) => setBusinessPrompt(e.target.value)}
                        placeholder="Example: I run a digital marketing agency with 5 clients. My biggest challenges include; scaling client acquisition without
                                     increasing ad spend, automating repetitive reporting tasks that take 10+ hours/week and improving content creation speed for 
                                     social media. Current monthly revenue is $10k and I would love this to increase to about $50k within 3 months. How can i 
                                     make this happen?"
                        rows={2}
                        className="w-full bg-transparent p-4 text-gray-700 text-base focus:outline-none resize-none placeholder:text-gray-400"/>
                    
                        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                          <div className="text-sm text-gray-400">
                            {businessPrompt.length} characters
                          </div>
                      
                          <Button
                            variant="primary"
                            size="lg"
                            onClick={() => navigate('/signup')}
                            disabled={!businessPrompt.trim()}
                            className="text-sm px-5 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed">
                            <i className="ri-rocket-line mr-2"></i>
                              Start Analysis
                          </Button>
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
        </div>
    </div>
  );
}

