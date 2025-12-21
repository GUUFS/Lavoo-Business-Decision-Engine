
import { useState } from 'react';
// import DashboardSidebar from '../../../components/feature/DashboardSidebar';
// import Footer from '../../../components/feature/Footer';

export default function ReviewsPage() {
  // const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState('all');

  const filters = [
    { id: 'all', name: 'All Reviews', count: 156 },
    { id: '5', name: '5 Stars', count: 89 },
    { id: '4', name: '4 Stars', count: 34 },
    { id: '3', name: '3 Stars', count: 18 },
    { id: '2', name: '2 Stars', count: 9 },
    { id: '1', name: '1 Star', count: 6 }
  ];

  const reviews = [
    {
      id: 1,
      customerName: 'Sarah Johnson',
      customerEmail: 'sarah.j@email.com',
      rating: 5,
      title: 'Excellent AI Strategy Platform',
      content: 'This platform has completely transformed how we approach AI implementation in our business. The insights are incredibly valuable and the recommendations are spot-on. Highly recommend!',
      date: '2024-03-20',
      verified: true,
      helpful: 24,
      product: 'AI Strategy Pro'
    },
    {
      id: 2,
      customerName: 'Michael Chen',
      customerEmail: 'michael.c@company.com',
      rating: 4,
      title: 'Great tool with room for improvement',
      content: 'Really solid platform overall. The AI recommendations have helped us identify several optimization opportunities. Would love to see more customization options in the dashboard.',
      date: '2024-03-18',
      verified: true,
      helpful: 18,
      product: 'AI Strategy Basic'
    },
    {
      id: 3,
      customerName: 'Emily Rodriguez',
      customerEmail: 'emily.r@startup.co',
      rating: 5,
      title: 'Game-changer for our startup',
      content: 'As a startup, we needed clear direction on AI adoption. This platform provided exactly that. The step-by-step recommendations and tool suggestions have been invaluable.',
      date: '2024-03-15',
      verified: true,
      helpful: 31,
      product: 'AI Strategy Enterprise'
    },
    {
      id: 4,
      customerName: 'David Kim',
      customerEmail: 'david.k@enterprise.net',
      rating: 3,
      title: 'Good but could be better',
      content: 'The platform provides useful insights, but I found some of the recommendations too generic for our specific industry. More customization would make this perfect.',
      date: '2024-03-12',
      verified: false,
      helpful: 7,
      product: 'AI Strategy Pro'
    },
    {
      id: 5,
      customerName: 'Lisa Thompson',
      customerEmail: 'lisa.t@agency.com',
      rating: 5,
      title: 'Perfect for agencies',
      content: 'We use this for multiple clients and it consistently delivers great results. The reporting features are excellent and clients love the detailed insights.',
      date: '2024-03-10',
      verified: true,
      helpful: 22,
      product: 'AI Strategy Enterprise'
    },
    {
      id: 6,
      customerName: 'James Wilson',
      customerEmail: 'james.w@consulting.biz',
      rating: 2,
      title: 'Not what I expected',
      content: 'The platform is okay but didn\'t meet my expectations. The interface feels cluttered and some features are hard to find. Customer support was helpful though.',
      date: '2024-03-08',
      verified: true,
      helpful: 5,
      product: 'AI Strategy Basic'
    }
  ];

  const filteredReviews = reviews.filter(review => {
    if (selectedFilter === 'all') return true;
    return review.rating.toString() === selectedFilter;
  });

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, index) => (
      <i
        key={index}
        className={`ri-star-${index < rating ? 'fill' : 'line'} text-yellow-400`}
      ></i>
    ));
  };

  const averageRating = reviews.reduce((sum, review) => sum + review.rating, 0) / reviews.length;
  const totalReviews = reviews.length;

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <div className="flex-1 p-4 md:p-6 lg:p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6 md:mb-8">
            <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Customer Reviews</h1>
            <p className="text-gray-600">Monitor and manage customer feedback and ratings</p>
          </div>

          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 md:gap-6 mb-8">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Average Rating</span>
                <div className="flex">
                  {renderStars(Math.round(averageRating))}
                </div>
              </div>
              <div className="text-2xl font-bold text-gray-900">{averageRating.toFixed(1)}</div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Total Reviews</span>
                <i className="ri-chat-3-line text-blue-500"></i>
              </div>
              <div className="text-2xl font-bold text-gray-900">{totalReviews}</div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">5-Star Reviews</span>
                <i className="ri-star-fill text-yellow-400"></i>
              </div>
              <div className="text-2xl font-bold text-gray-900">89</div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-600">Response Rate</span>
                <i className="ri-reply-line text-green-500"></i>
              </div>
              <div className="text-2xl font-bold text-gray-900">94%</div>
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Filter Reviews</h3>
              <div className="flex gap-2">
                <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                  <i className="ri-download-line mr-2"></i>
                  Export
                </button>
                <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                  <i className="ri-settings-line mr-2"></i>
                  Settings
                </button>
              </div>
            </div>

            <div className="flex gap-2 overflow-x-auto pb-2">
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => setSelectedFilter(filter.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${selectedFilter === filter.id
                      ? 'bg-orange-100 text-orange-600 border border-orange-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                >
                  {filter.name} ({filter.count})
                </button>
              ))}
            </div>
          </div>

          {/* Reviews List */}
          <div className="space-y-6">
            {filteredReviews.map((review) => (
              <div key={review.id} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <span className="text-orange-600 font-medium">
                        {review.customerName.split(' ').map(n => n[0]).join('')}
                      </span>
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2 mb-2">
                        <h4 className="font-semibold text-gray-900">{review.customerName}</h4>
                        {review.verified && (
                          <span className="text-xs bg-green-100 text-green-600 px-2 py-1 rounded-full flex items-center w-fit">
                            <i className="ri-verified-badge-line mr-1"></i>
                            Verified
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="flex">
                          {renderStars(review.rating)}
                        </div>
                        <span className="text-sm text-gray-500">•</span>
                        <span className="text-sm text-gray-500">{review.date}</span>
                        <span className="text-sm text-gray-500">•</span>
                        <span className="text-sm text-gray-500">{review.product}</span>
                      </div>
                    </div>
                  </div>
                  <button className="text-gray-400 hover:text-gray-600 self-start">
                    <i className="ri-more-line"></i>
                  </button>
                </div>

                <div className="mb-4">
                  <h5 className="font-medium text-gray-900 mb-2">{review.title}</h5>
                  <p className="text-gray-600 leading-relaxed">{review.content}</p>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <button className="flex items-center hover:text-orange-600 transition-colors">
                      <i className="ri-thumb-up-line mr-1"></i>
                      Helpful ({review.helpful})
                    </button>
                    <button className="flex items-center hover:text-orange-600 transition-colors">
                      <i className="ri-reply-line mr-1"></i>
                      Reply
                    </button>
                    <button className="flex items-center hover:text-orange-600 transition-colors">
                      <i className="ri-share-line mr-1"></i>
                      Share
                    </button>
                  </div>
                  <div className="flex gap-2">
                    <button className="bg-orange-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors whitespace-nowrap">
                      Respond
                    </button>
                    <button className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors whitespace-nowrap">
                      Archive
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {filteredReviews.length === 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <i className="ri-star-line text-2xl text-gray-400"></i>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No reviews found</h3>
              <p className="text-gray-600 mb-6">No reviews match your current filter selection</p>
              <button
                onClick={() => setSelectedFilter('all')}
                className="bg-orange-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-orange-600 transition-colors whitespace-nowrap"
              >
                Show All Reviews
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
