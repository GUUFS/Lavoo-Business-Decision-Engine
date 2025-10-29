
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import Header from '../../components/feature/Header';
import Footer from '../../components/feature/Footer';
import Button from '../../components/base/Button';
import Input from '../../components/base/Input';
import Textarea from '../../components/base/Textarea';
import { analyzeBusinessQuery, type BusinessAnalysisRequest } from '../../api/business';

export default function Analyze() {
  const navigate = useNavigate();
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
    
    try {
      // Show user we're analyzing their business
      toast.info('Analyzing your business with AI... This may take a few seconds.');
      
      // Call the backend API with form data
      const analysisResult = await analyzeBusinessQuery(formData as BusinessAnalysisRequest);
      
      // Success! Navigate to results page with AI-generated data
      toast.success('Analysis complete! Generating your personalized strategy...');
      
      navigate('/results', { 
        state: { 
          analysisResult,  // Contains: recommendations, swot, formData
        } 
      });
      
    } catch (error) {
      // Handle errors gracefully
      console.error('Analysis error:', error);
      toast.error('Failed to analyze business. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white">
      <Header />
      
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
              <h2 className="text-xl sm:text-2xl font-bold text-black mb-4 sm:mb-6 flex items-center">
                <i className="ri-building-line text-orange-500 mr-2 sm:mr-3"></i>
                Company Information
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                <Input
                  label="Company Name"
                  name="companyName"
                  value={formData.companyName}
                  onChange={handleInputChange}
                  placeholder="Enter your company name"
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Industry <span className="text-orange-500 ml-1">*</span>
                  </label>
                  <select
                    name="industry"
                    value={formData.industry}
                    onChange={(e) => handleInputChange(e as any)}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm pr-8"
                  >
                    <option value="">Select your industry</option>
                    <option value="content_creation">Content creation</option>
                    <option value="saas">Saas</option>
                    <option value="advertising">Advertising</option>
                    <option value="ecommerce">Ecommerce</option>
                    <option value="technology">Technology</option>
                    <option value="healthcare">Healthcare</option>
                    <option value="finance">Finance</option>
                    <option value="retail">Retail</option>
                    <option value="manufacturing">Manufacturing</option>
                    <option value="education">Education</option>
                    <option value="consulting">Consulting</option>
                    <option value="real-estate">Real Estate</option>
                    <option value="marketing">Digital Marketing</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Company Size <span className="text-orange-500 ml-1">*</span>
                  </label>
                  <select
                    name="companySize"
                    value={formData.companySize}
                    onChange={(e) => handleInputChange(e as any)}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm pr-8"
                  >
                    <option value="">Select company size</option>
                    <option value="1-10">1-10 employees</option>
                    <option value="11-50">11-50 employees</option>
                    <option value="51-200">51-200 employees</option>
                    <option value="201-1000">201-1000 employees</option>
                    <option value="1000+">1000+ employees</option>
                  </select>
                </div>
                <Input
                  label="Email Address"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="your@email.com"
                  required
                />
              </div>
            </div>

            {/* Business Details */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-gray-100">
              <h2 className="text-xl sm:text-2xl font-bold text-black mb-4 sm:mb-6 flex items-center">
                <i className="ri-lightbulb-line text-orange-500 mr-2 sm:mr-3"></i>
                Business Details
              </h2>
              <div className="space-y-4 sm:space-y-6">
                <Textarea
                  label="Business Description"
                  name="businessDescription"
                  value={formData.businessDescription}
                  onChange={handleInputChange}
                  placeholder="Describe what your business does, your main products/services, and your target market..."
                  rows={4}
                  required
                />
                <Textarea
                  label="Current Challenges"
                  name="currentChallenges"
                  value={formData.currentChallenges}
                  onChange={handleInputChange}
                  placeholder="What are the main challenges or pain points your business is facing? (e.g., manual processes, customer service bottlenecks, data analysis difficulties...)"
                  rows={4}
                  required
                />
                <Textarea
                  label="Goals & Objectives"
                  name="goals"
                  value={formData.goals}
                  onChange={handleInputChange}
                  placeholder="What are your main business goals? What would you like to achieve with AI implementation? (e.g., increase efficiency, reduce costs, improve customer experience...)"
                  rows={4}
                  required
                />
              </div>
            </div>

            {/* Implementation Preferences */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-gray-100">
              <h2 className="text-xl sm:text-2xl font-bold text-black mb-4 sm:mb-6 flex items-center">
                <i className="ri-settings-line text-orange-500 mr-2 sm:mr-3"></i>
                Implementation Preferences
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Budget Range
                  </label>
                  <select
                    name="budget"
                    value={formData.budget}
                    onChange={(e) => handleInputChange(e as any)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm pr-8"
                  >
                    <option value="">Select budget range</option>
                    <option value="under-1k">Under $1,000/month</option>
                    <option value="1k-5k">$1,000 - $5,000/month</option>
                    <option value="5k-10k">$5,000 - $10,000/month</option>
                    <option value="10k-25k">$10,000 - $25,000/month</option>
                    <option value="25k+">$25,000+/month</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Implementation Timeline
                  </label>
                  <select
                    name="timeline"
                    value={formData.timeline}
                    onChange={(e) => handleInputChange(e as any)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors text-sm pr-8"
                  >
                    <option value="">Select timeline</option>
                    <option value="immediate">Immediate (1-2 weeks)</option>
                    <option value="short">Short-term (1-3 months)</option>
                    <option value="medium">Medium-term (3-6 months)</option>
                    <option value="long">Long-term (6+ months)</option>
                  </select>
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
                className="w-full sm:w-auto text-base sm:text-lg px-8 sm:px-12 py-3 sm:py-4"
              >
                {isSubmitting ? (
                  <>
                    <i className="ri-loader-4-line mr-2 animate-spin"></i>
                    Analyzing with AI...
                  </>
                ) : (
                  <>
                    <i className="ri-rocket-line mr-2"></i>
                    Generate My AI Strategy
                  </>
                )}
              </Button>
            </div>
          </form>
        </div>
      </section>

      <Footer />
    </div>
  );
}