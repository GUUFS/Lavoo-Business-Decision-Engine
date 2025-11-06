
import { useState } from 'react';

export default function CustomerServicePage() {
  const [issue, setIssue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issue.trim()) return;

    setIsSubmitting(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    setIsSubmitting(false);
    setIsSubmitted(true);
    setIssue('');

    // Reset success message after 3 seconds
    setTimeout(() => {
      setIsSubmitted(false);
    }, 3000);
  };

  const quickHelpOptions = [
    {
      title: 'Frequently Asked Questions',
      description: 'Find answers to common questions',
      icon: 'ri-question-line',
      action: 'Browse FAQ'
    },
    {
      title: 'Live Chat Support',
      description: 'Chat with our support team',
      icon: 'ri-chat-3-line',
      action: 'Start Chat'
    },
    {
      title: 'Documentation',
      description: 'Access user guides and tutorials',
      icon: 'ri-book-open-line',
      action: 'View Docs'
    },
    {
      title: 'Video Tutorials',
      description: 'Watch step-by-step guides',
      icon: 'ri-play-circle-line',
      action: 'Watch Videos'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Customer Service</h1>
          <p className="text-sm sm:text-base text-gray-600">Get help and support for your account</p>
        </div>

        {/* Quick Help Options */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
          {quickHelpOptions.map((option, index) => (
            <div key={index} className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
              <div className="text-center">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-orange-100 rounded-lg flex items-center justify-center mx-auto mb-3 sm:mb-4">
                  <i className={`${option.icon} text-orange-600 text-xl sm:text-2xl`}></i>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2 text-sm sm:text-base">{option.title}</h3>
                <p className="text-xs sm:text-sm text-gray-600 mb-3 sm:mb-4">{option.description}</p>
                <button className="w-full bg-orange-500 text-white px-3 py-2 rounded-lg hover:bg-orange-600 transition-colors font-medium text-xs sm:text-sm whitespace-nowrap">
                  {option.action}
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Support Form */}
        <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 lg:p-8 border border-gray-200 shadow-sm">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-6 sm:mb-8">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="ri-customer-service-line text-orange-600 text-2xl sm:text-3xl"></i>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">Describe Your Issue</h2>
              <p className="text-sm sm:text-base text-gray-600">
                Tell us about the problem you're experiencing and we'll help you resolve it
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="issue" className="block text-sm font-medium text-gray-700 mb-2">
                  Issue Description
                </label>
                <textarea
                  id="issue"
                  value={issue}
                  onChange={(e) => setIssue(e.target.value)}
                  placeholder="Please describe your issue in detail. Include any error messages, steps you took, and what you expected to happen..."
                  rows={8}
                  maxLength={500}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none text-sm sm:text-base"
                  required
                />
                <div className="flex justify-between items-center mt-2">
                  <p className="text-xs text-gray-500">
                    Please provide as much detail as possible to help us assist you better
                  </p>
                  <p className="text-xs text-gray-500">
                    {issue.length}/500 characters
                  </p>
                </div>
              </div>

              <div className="flex justify-center">
                <button
                  type="submit"
                  disabled={isSubmitting || !issue.trim()}
                  className="bg-orange-500 text-white px-8 py-3 rounded-lg hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm sm:text-base whitespace-nowrap min-w-[200px]"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center">
                      <i className="ri-loader-4-line animate-spin mr-2"></i>
                      Submitting...
                    </span>
                  ) : (
                    <span className="flex items-center justify-center">
                      <i className="ri-send-plane-line mr-2"></i>
                      Submit Issue
                    </span>
                  )}
                </button>
              </div>
            </form>

            {/* Success Message */}
            {isSubmitted && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center">
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center mr-3">
                    <i className="ri-check-line text-green-600"></i>
                  </div>
                  <div>
                    <h3 className="font-semibold text-green-800">Issue Submitted Successfully!</h3>
                    <p className="text-sm text-green-700">
                      We've received your request and will respond within 24 hours.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Contact Information */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-4 text-center">Other Ways to Reach Us</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                <div className="flex flex-col items-center">
                  <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-2">
                    <i className="ri-mail-line text-blue-600"></i>
                  </div>
                  <p className="text-sm font-medium text-gray-900">Email</p>
                  <p className="text-xs text-gray-600">support@aistrategy.com</p>
                </div>
                <div className="flex flex-col items-center">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-2">
                    <i className="ri-phone-line text-green-600"></i>
                  </div>
                  <p className="text-sm font-medium text-gray-900">Phone</p>
                  <p className="text-xs text-gray-600">1-800-AI-HELP</p>
                </div>
                <div className="flex flex-col items-center">
                  <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-2">
                    <i className="ri-time-line text-purple-600"></i>
                  </div>
                  <p className="text-sm font-medium text-gray-900">Hours</p>
                  <p className="text-xs text-gray-600">24/7 Support</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
