
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DashboardSidebar from '../../../components/feature/DashboardSidebar';

export default function UpgradePage() {
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isYearly, setIsYearly] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleUpgrade = async () => {
    setIsProcessing(true);
    // Simulate payment processing
    setTimeout(() => {
      setIsProcessing(false);
      setShowSuccess(true);
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    }, 3000);
  };

  const features = [
    {
      icon: 'ri-notification-line',
      title: 'Unlimited Opportunity Alerts',
      description: 'Get access to all business opportunities and market insights without any limits'
    },
    {
      icon: 'ri-brain-line',
      title: 'Advanced AI Insights',
      description: 'Deep AI analysis with predictive analytics and personalized recommendations'
    },
    {
      icon: 'ri-roadmap-line',
      title: 'Detailed Action Plans',
      description: 'Step-by-step implementation guides with timelines and resource requirements'
    },
    {
      icon: 'ri-star-line',
      title: 'Priority Scoring System',
      description: 'Advanced scoring algorithms to prioritize opportunities by potential ROI'
    },
    {
      icon: 'ri-time-line',
      title: 'Real-time Notifications',
      description: 'Instant alerts for time-sensitive opportunities and market changes'
    },
    {
      icon: 'ri-customer-service-line',
      title: 'Premium Support',
      description: '24/7 priority support with dedicated account manager and consultation calls'
    }
  ];

  const testimonials = [
    {
      name: 'Sarah Johnson',
      role: 'CEO, TechStart Inc.',
      rating: 5,
      text: 'The AI insights helped us identify a market opportunity that increased our revenue by 40% in just 3 months.'
    },
    {
      name: 'Michael Chen',
      role: 'Founder, GrowthLab',
      rating: 5,
      text: 'Premium alerts gave us the competitive edge we needed. The ROI has been incredible.'
    },
    {
      name: 'Emily Rodriguez',
      role: 'Director, InnovateCorp',
      rating: 5,
      text: 'The action plans are detailed and actionable. We\'ve implemented 5 recommendations with great success.'
    }
  ];

  const faqs = [
    {
      question: 'Can I cancel my subscription anytime?',
      answer: 'Yes, you can cancel your subscription at any time. You\'ll continue to have access to premium features until the end of your billing period.'
    },
    {
      question: 'What payment methods do you accept?',
      answer: 'We accept all major credit cards (Visa, MasterCard, American Express) and PayPal for your convenience.'
    },
    {
      question: 'Is there a money-back guarantee?',
      answer: 'Yes, we offer a 30-day money-back guarantee. If you\'re not satisfied, we\'ll refund your payment in full.'
    },
    {
      question: 'How quickly will I see results?',
      answer: 'Most users see actionable insights within 24 hours of upgrading, with significant business impact typically within 30 days.'
    }
  ];

  if (showSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
        <DashboardSidebar 
          isMobileMenuOpen={isMobileMenuOpen} 
          setIsMobileMenuOpen={setIsMobileMenuOpen} 
        />
        
        <div className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center p-4 md:p-6 lg:p-8">
            <div className="text-center max-w-md mx-auto">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <i className="ri-check-line text-green-600 text-3xl"></i>
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
                Welcome to Premium!
              </h1>
              <p className="text-lg text-gray-600 mb-6">
                Your upgrade was successful. You now have access to all premium features.
              </p>
              <div className="animate-spin w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full mx-auto"></div>
              <p className="text-sm text-gray-500 mt-4">Redirecting to dashboard...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
      
      <div className="flex-1 flex flex-col  min-h-screen bg-gradient-to-br from-orange-50 to-white px-4">
        <div className="flex-1 p-4 md:p-6 lg:p-8">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="text-center mb-8 md:mb-12">
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
                Upgrade to Premium
              </h1>
              <p className="text-lg md:text-xl text-gray-600 max-w-3xl mx-auto">
                Unlock the full power of AI-driven business insights and take your strategy to the next level
              </p>
            </div>

            {/* Pricing Cards */}
            <div className="mb-12 md:mb-16">
              {/* Billing Toggle */}
              <div className="flex items-center justify-center mb-8">
                <span className={`text-sm font-medium mr-3 transition-colors ${!isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
                  Monthly
                </span>
                <button
                  onClick={() => setIsYearly(!isYearly)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 ${
                    isYearly ? 'bg-orange-600' : 'bg-gray-200'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      isYearly ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <span className={`text-sm font-medium ml-3 transition-colors ${isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
                  Yearly
                </span>
                {isYearly && (
                  <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Save 17%
                  </span>
                )}
              </div>

              {/* Pricing Card */}
              <div className="max-w-lg mx-auto">
                <div className="bg-white rounded-2xl shadow-xl border-2 border-orange-200 p-6 md:p-8 relative overflow-hidden">
                  {/* Popular Badge */}
                  <div className="absolute top-0 right-0 bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-1 text-xs font-semibold rounded-bl-lg">
                    MOST POPULAR
                  </div>
                  
                  <div className="text-center mb-6">
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">Premium Plan</h3>
                    <div className="flex items-center justify-center mb-4">
                      <span className="text-4xl md:text-5xl font-bold text-gray-900">
                        ${isYearly ? '290' : '29'}
                      </span>
                      <span className="text-lg text-gray-600 ml-2">
                        /{isYearly ? 'year' : 'month'}
                      </span>
                    </div>
                    {isYearly && (
                      <p className="text-sm text-gray-500">
                        <span className="line-through">$348/year</span> - Save $58
                      </p>
                    )}
                  </div>

                  <button
                    onClick={handleUpgrade}
                    disabled={isProcessing}
                    className={`w-full py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-200 whitespace-nowrap ${
                      isProcessing
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 transform hover:scale-105 shadow-lg hover:shadow-xl'
                    }`}
                  >
                    {isProcessing ? (
                      <div className="flex items-center justify-center">
                        <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                        Processing...
                      </div>
                    ) : (
                      <>
                        <i className="ri-crown-line mr-2"></i>
                        Upgrade Now
                      </>
                    )}
                  </button>

                  <p className="text-xs text-gray-500 text-center mt-4">
                    30-day money-back guarantee • Cancel anytime
                  </p>
                </div>
              </div>
            </div>

            {/* Features Grid */}
            <div className="mb-12 md:mb-16">
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 text-center mb-8">
                Everything You Get with Premium
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                {features.map((feature, index) => (
                  <div key={index} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200">
                    <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
                      <i className={`${feature.icon} text-orange-600 text-xl`}></i>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {feature.title}
                    </h3>
                    <p className="text-gray-600 text-sm leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Testimonials */}
            <div className="mb-12 md:mb-16">
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 text-center mb-8">
                What Our Premium Users Say
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                {testimonials.map((testimonial, index) => (
                  <div key={index} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                    <div className="flex items-center mb-4">
                      {[...Array(testimonial.rating)].map((_, i) => (
                        <i key={i} className="ri-star-fill text-yellow-400 text-sm"></i>
                      ))}
                    </div>
                    <p className="text-gray-700 mb-4 italic leading-relaxed">
                      "{testimonial.text}"
                    </p>
                    <div className="flex items-center">
                      <div className="w-10 h-10 bg-gradient-to-r from-orange-400 to-orange-600 rounded-full flex items-center justify-center mr-3">
                        <span className="text-white font-semibold text-sm">
                          {testimonial.name.split(' ').map(n => n[0]).join('')}
                        </span>
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{testimonial.name}</p>
                        <p className="text-gray-600 text-xs">{testimonial.role}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* FAQ Section */}
            <div className="mb-8">
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900 text-center mb-8">
                Frequently Asked Questions
              </h2>
              <div className="max-w-3xl mx-auto space-y-4">
                {faqs.map((faq, index) => (
                  <div key={index} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                    <h3 className="font-semibold text-gray-900 mb-2 text-lg">
                      {faq.question}
                    </h3>
                    <p className="text-gray-600 leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Bottom CTA */}
            <div className="text-center bg-gradient-to-r from-orange-50 to-orange-100 rounded-2xl p-6 md:p-8">
              <h3 className="text-xl md:text-2xl font-bold text-gray-900 mb-4">
                Ready to Transform Your Business?
              </h3>
              <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
                Join thousands of successful businesses using AI Strategy Premium to unlock growth opportunities and stay ahead of the competition.
              </p>
              <button
                onClick={handleUpgrade}
                disabled={isProcessing}
                className={`py-3 px-8 rounded-xl font-semibold text-lg transition-all duration-200 whitespace-nowrap ${
                  isProcessing
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 transform hover:scale-105 shadow-lg hover:shadow-xl'
                }`}
              >
                {isProcessing ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
                    Processing...
                  </div>
                ) : (
                  <>
                    <i className="ri-crown-line mr-2"></i>
                    Start Your Premium Journey
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    
  );
}
