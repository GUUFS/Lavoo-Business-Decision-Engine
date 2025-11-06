
import { useState } from 'react';

export default function ReviewsPage() {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [reviewTitle, setReviewTitle] = useState('');
  const [reviewContent, setReviewContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rating || !reviewTitle.trim() || !reviewContent.trim()) return;

    setIsSubmitting(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    setIsSubmitting(false);
    setIsSubmitted(true);
    
    // Reset form
    setRating(0);
    setReviewTitle('');
    setReviewContent('');

    // Reset success message after 3 seconds
    setTimeout(() => {
      setIsSubmitted(false);
    }, 3000);
  };

  const reviewStats = [
    { label: 'Total Reviews', value: '1,247', icon: 'ri-star-line', color: 'bg-yellow-100 text-yellow-600' },
    { label: 'Average Rating', value: '4.8', icon: 'ri-heart-line', color: 'bg-red-100 text-red-600' },
    { label: 'This Month', value: '89', icon: 'ri-calendar-line', color: 'bg-blue-100 text-blue-600' },
    { label: 'Response Rate', value: '98%', icon: 'ri-chat-3-line', color: 'bg-green-100 text-green-600' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">Write a Review</h1>
          <p className="text-sm sm:text-base text-gray-600">Share your experience and help us improve our service</p>
        </div>

        {/* Review Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8">
          {reviewStats.map((stat, index) => (
            <div key={index} className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm font-medium text-gray-600">{stat.label}</p>
                  <p className="text-xl sm:text-2xl font-bold text-gray-900">{stat.value}</p>
                </div>
                <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg flex items-center justify-center ${stat.color}`}>
                  <i className={`${stat.icon} text-lg sm:text-xl`}></i>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Review Form */}
        <div className="bg-white rounded-lg sm:rounded-xl p-4 sm:p-6 lg:p-8 border border-gray-200 shadow-sm">
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-6 sm:mb-8">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="ri-star-line text-orange-600 text-2xl sm:text-3xl"></i>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">Rate Your Experience</h2>
              <p className="text-sm sm:text-base text-gray-600">
                Your feedback helps us provide better service to all our users
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Star Rating */}
              <div className="text-center">
                <label className="block text-sm font-medium text-gray-700 mb-4">
                  How would you rate our service?
                </label>
                <div className="flex justify-center gap-2 mb-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setRating(star)}
                      onMouseEnter={() => setHoveredRating(star)}
                      onMouseLeave={() => setHoveredRating(0)}
                      className="text-3xl sm:text-4xl transition-colors focus:outline-none"
                    >
                      <i className={`ri-star-${
                        star <= (hoveredRating || rating) ? 'fill' : 'line'
                      } ${
                        star <= (hoveredRating || rating) ? 'text-yellow-400' : 'text-gray-300'
                      }`}></i>
                    </button>
                  ))}
                </div>
                <p className="text-sm text-gray-500">
                  {rating === 0 && 'Click to rate'}
                  {rating === 1 && 'Poor'}
                  {rating === 2 && 'Fair'}
                  {rating === 3 && 'Good'}
                  {rating === 4 && 'Very Good'}
                  {rating === 5 && 'Excellent'}
                </p>
              </div>

              {/* Review Title */}
              <div>
                <label htmlFor="reviewTitle" className="block text-sm font-medium text-gray-700 mb-2">
                  Review Title
                </label>
                <input
                  type="text"
                  id="reviewTitle"
                  value={reviewTitle}
                  onChange={(e) => setReviewTitle(e.target.value)}
                  placeholder="Summarize your experience in a few words..."
                  maxLength={100}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 text-sm sm:text-base"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  {reviewTitle.length}/100 characters
                </p>
              </div>

              {/* Review Content */}
              <div>
                <label htmlFor="reviewContent" className="block text-sm font-medium text-gray-700 mb-2">
                  Your Review
                </label>
                <textarea
                  id="reviewContent"
                  value={reviewContent}
                  onChange={(e) => setReviewContent(e.target.value)}
                  placeholder="Tell us about your experience. What did you like? What could be improved? Your detailed feedback helps us serve you better..."
                  rows={6}
                  maxLength={500}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 resize-none text-sm sm:text-base"
                  required
                />
                <div className="flex justify-between items-center mt-2">
                  <p className="text-xs text-gray-500">
                    Share specific details about your experience
                  </p>
                  <p className="text-xs text-gray-500">
                    {reviewContent.length}/500 characters
                  </p>
                </div>
              </div>

              <div className="flex justify-center">
                <button
                  type="submit"
                  disabled={isSubmitting || !rating || !reviewTitle.trim() || !reviewContent.trim()}
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
                      Submit Review
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
                    <h3 className="font-semibold text-green-800">Review Submitted Successfully!</h3>
                    <p className="text-sm text-green-700">
                      Thank you for your feedback. Your review will be published after moderation.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Guidelines */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-4">Review Guidelines</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-gray-600">
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <i className="ri-check-line text-green-600 mt-0.5 flex-shrink-0"></i>
                    <span>Be honest and specific about your experience</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <i className="ri-check-line text-green-600 mt-0.5 flex-shrink-0"></i>
                    <span>Focus on the service and features you used</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <i className="ri-check-line text-green-600 mt-0.5 flex-shrink-0"></i>
                    <span>Include both positives and areas for improvement</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <i className="ri-close-line text-red-600 mt-0.5 flex-shrink-0"></i>
                    <span>Avoid personal attacks or inappropriate language</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <i className="ri-close-line text-red-600 mt-0.5 flex-shrink-0"></i>
                    <span>Don't include personal information</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <i className="ri-close-line text-red-600 mt-0.5 flex-shrink-0"></i>
                    <span>Keep it relevant to our service</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
