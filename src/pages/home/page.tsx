
import { useNavigate } from 'react-router-dom';
import Header from '../../components/feature/Header';
import Footer from '../../components/feature/Footer';
import Button from '../../components/base/Button';
import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Interface for review data
interface Review {
  id: number;
  user_name: string;
  business_name: string;
  review_title: string;
  rating: number;
  review_text: string;
  date_submitted: string;
  verified: boolean;
}

export default function Home() {
  const navigate = useNavigate();
  const [currentSlide, setCurrentSlide] = useState(0);
  const [businessPrompt, setBusinessPrompt] = useState("");
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loadingReviews, setLoadingReviews] = useState(true);
  const [totalSlides, setTotalSlides] = useState(2); // Will be updated based on reviews count

  // Fetch displayed reviews from API
  useEffect(() => {
    const fetchDisplayedReviews = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/reviews/displayed`);
        setReviews(response.data);
        // Calculate number of slides based on reviews count (3 per slide)
        const slides = Math.ceil(response.data.length / 3) || 1;
        setTotalSlides(slides);
      } catch (error) {
        console.error('Failed to fetch reviews:', error);
        // Keep empty array if fetch fails
        setReviews([]);
      } finally {
        setLoadingReviews(false);
      }
    };

    fetchDisplayedReviews();
  }, []);

  // Get initials from name
  const getInitials = (name: string): string => {
    const names = name.split(' ');
    if (names.length >= 2) {
      return `${names[0][0]}${names[1][0]}`.toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  };

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % totalSlides);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + totalSlides) % totalSlides);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white">
      <Header />

      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-orange-50 to-white py-12 sm:py-16 md:py-20 lg:py-32 overflow-hidden">
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-black leading-tight mb-4 sm:mb-6 px-2">
              Turn Your Business Brief Into a
              <span className="text-orange-500"> Tailored AI Strategy</span>
            </h1>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 mb-6 sm:mb-8 leading-relaxed px-4">
              Describe your business and get a prioritized toolkit that boosts productivity,
              reduces friction, and scales with your vision, all in minutes, not months.
            </p>

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
                  className="w-full bg-transparent p-4 text-gray-700 text-base focus:outline-none resize-none placeholder:text-gray-400" />

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

            {/* Feature icons below */}
            <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-6 text-xs sm:text-sm text-gray-500 px-4">
              <div className="flex items-center">
                <i className="ri-check-line text-green-500 mr-2"></i>
                Free Analysis
              </div>
              <div className="flex items-center">
                <i className="ri-check-line text-green-500 mr-2"></i>
                Instant Results
              </div>
              <div className="flex items-center">
                <i className="ri-check-line text-green-500 mr-2"></i>
                No Credit Card
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* Features Section */}
      <section id="features" className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 sm:mb-12 md:mb-16">
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black mb-3 sm:mb-4 px-2">
              Why Choose Our AI Business Analyst?
            </h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl mx-auto px-4">
              Our intelligent platform analyzes your business needs and delivers personalized AI tool recommendations
              that drive real results.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 sm:gap-10 md:gap-8">
            <div className="text-center px-4">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-500 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
                <span className="text-xl sm:text-2xl font-bold text-white">1</span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">Describe Your Business</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Tell us about your operations, challenges and goals. Our form guides you through
                the key information we need to understand your business.
              </p>
            </div>

            <div className="text-center px-4">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-500 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
                <span className="text-xl sm:text-2xl font-bold text-white">2</span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">AI Analysis</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Our advanced AI engine processes your information and matches it against our
                comprehensive database of AI tools and solutions.
              </p>
            </div>

            <div className="text-center px-4">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-orange-500 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
                <span className="text-xl sm:text-2xl font-bold text-white">3</span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">Get Your Strategy</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Receive a detailed report with prioritized AI tool recommendations, implementation
                guides and expected ROI for each solution.
              </p>
            </div>
          </div>
        </div>
        <div className="text-center mt-20 flex items-center justify-center">
          <Button variant="primary" size="lg" onClick={() => navigate('/signup')}
            className="text-base sm:text-lg px-6 sm:px-8 py-3 sm:py-4 w-full sm:w-auto">
            Start Your Analysis Now
          </Button>
        </div>
      </section>


      {/* Reviews Section - Now Dynamic! */}
      <section className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white" >
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 16px' }}>
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2 style={{ fontSize: window.innerWidth >= 768 ? '40px' : '32px', fontWeight: 'bold', color: '#111827', marginBottom: '16px' }}>
              What Our Customers Say
            </h2>
            <p style={{ fontSize: '20px', color: '#4b5563', maxWidth: '768px', margin: '0 auto 16px' }}>
              Join thousands of businesses that trust our AI analyst for data-driven insights
            </p>
            {reviews.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '16px' }}>
                <div style={{ display: 'flex' }}>
                  {[...Array(5)].map((_, i) => (
                    <i key={i} className="ri-star-fill" style={{ color: '#fbbf24', fontSize: '20px' }}></i>
                  ))}
                </div>
                <span style={{ fontSize: '18px', fontWeight: '600', color: '#111827' }}>4.9/5</span>
                <span style={{ color: '#4b5563' }}>({reviews.length}+ reviews)</span>
              </div>
            )}
          </div>

          {loadingReviews ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <i className="ri-loader-4-line" style={{ fontSize: '48px', color: '#f97316', animation: 'spin 1s linear infinite' }}></i>
              <p style={{ marginTop: '16px', color: '#6b7280' }}>Loading reviews...</p>
            </div>
          ) : reviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <i className="ri-chat-smile-3-line" style={{ fontSize: '64px', color: '#d1d5db', marginBottom: '16px' }}></i>
              <p style={{ fontSize: '18px', color: '#6b7280' }}>No reviews yet. Be the first to share your experience!</p>
            </div>
          ) : (
            <div style={{ position: 'relative' }}>
              {/* Reviews Carousel */}
              <div style={{ overflow: 'hidden' }}>
                <div style={{ display: 'flex', transition: 'transform 0.5s ease-in-out', transform: `translateX(-${currentSlide * 100}%)` }}>
                  {Array.from({ length: totalSlides }).map((_, slideIndex) => (
                    <div key={slideIndex} style={{ width: '100%', flexShrink: 0 }}>
                      <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth >= 768 ? 'repeat(3, 1fr)' : '1fr', gap: '32px' }}>
                        {reviews.slice(slideIndex * 3, slideIndex * 3 + 3).map((review) => (
                          <div key={review.id} style={{
                            backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px',
                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb'
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                              <div style={{
                                width: '48px', height: '48px', backgroundColor: '#fef2f2', borderRadius: '50%', display: 'flex',
                                alignItems: 'center', justifyContent: 'center', marginRight: '16px'
                              }}>
                                <span style={{ color: '#dc2626', fontWeight: '600' }}>{getInitials(review.user_name)}</span>
                              </div>
                              <div>
                                <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>{review.user_name}</h4>
                                <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>{review.business_name}</p>
                              </div>
                            </div>
                            <div style={{ display: 'flex', marginBottom: '16px' }}>
                              {[...Array(5)].map((_, i) => (
                                <i key={i} className={`ri-star-${i < review.rating ? 'fill' : 'line'}`} style={{ color: '#fbbf24' }}></i>
                              ))}
                            </div>
                            <h5 style={{ fontWeight: '600', color: '#111827', marginBottom: '8px' }}>{review.review_title}</h5>
                            <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                              "{review.review_text}"
                            </p>
                            {review.verified && (
                              <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '4px', color: '#10b981' }}>
                                <i className="ri-checkbox-circle-fill"></i>
                                <span style={{ fontSize: '12px', fontWeight: '500' }}>Verified Customer</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Navigation Arrows - Only show if more than 1 slide */}
              {totalSlides > 1 && (
                <>
                  <button
                    onClick={prevSlide}
                    style={{
                      position: 'absolute', left: '-16px', top: '50%', transform: 'translateY(-50%)', width: '48px', height: '48px', backgroundColor: '#ffffff', borderRadius: '50%',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4b5563',
                      border: 'none', cursor: 'pointer', zIndex: 10, transition: 'color 0.3s ease'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.color = '#dc2626'}
                    onMouseOut={(e) => e.currentTarget.style.color = '#4b5563'}
                  >
                    <i className="ri-arrow-left-line" style={{ fontSize: '20px' }}></i>
                  </button>
                  <button
                    onClick={nextSlide}
                    style={{
                      position: 'absolute', right: '-16px', top: '50%', transform: 'translateY(-50%)', width: '48px', height: '48px', backgroundColor: '#ffffff', borderRadius: '50%',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: '#4b5563', border: 'none', cursor: 'pointer', zIndex: 10, transition: 'color 0.3s ease'
                    }}
                    onMouseOver={(e) => e.currentTarget.style.color = '#dc2626'}
                    onMouseOut={(e) => e.currentTarget.style.color = '#4b5563'}
                  >
                    <i className="ri-arrow-right-line" style={{ fontSize: '20px' }}></i>
                  </button>

                  {/* Slide Indicators */}
                  <div style={{ display: 'flex', justifyContent: 'center', marginTop: '32px', gap: '8px' }}>
                    {Array.from({ length: totalSlides }).map((_, slide) => (
                      <button
                        key={slide}
                        onClick={() => setCurrentSlide(slide)}
                        style={{
                          width: '12px', height: '12px', borderRadius: '50%', border: 'none', cursor: 'pointer',
                          backgroundColor: currentSlide === slide ? '#dc2626' : '#d1d5db', transition: 'background-color 0.3s ease'
                        }}
                      />
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Chopsticks Section */}
      <section id="blog" className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 sm:mb-12 md:mb-16">
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black mb-3 sm:mb-4 px-2">
              Chopsticks
            </h2>
            <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-3xl mx-auto px-4">
              Stay updated with the latest AI trends and business insights
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-14 h-14 sm:w-16 sm:h-16 bg-orange-100 rounded-2xl flex items-center justify-center mb-4 sm:mb-6">
                <i className="ri-brain-line text-orange-500 text-xl sm:text-2xl"></i>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">AI Insights</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Our AI engine provides timely news on AI innovations, products, news across various industries, from cutting-edge research to
                real-world applications involving technologies transforming the future.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-14 h-14 sm:w-16 sm:h-16 bg-orange-100 rounded-2xl flex items-center justify-center mb-4 sm:mb-6">
                <i className="ri-tools-line text-orange-500 text-xl sm:text-2xl"></i>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">Opportunity Alerts</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Lavoo provides you with current trajectories in artificial intelligence, providing you with tailored research and
                expert recommendations.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-14 h-14 sm:w-16 sm:h-16 bg-orange-100 rounded-2xl flex items-center justify-center mb-4 sm:mb-6">
                <i className="ri-rocket-line text-orange-500 text-xl sm:text-2xl"></i>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">AI Trends</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Stay informed on the evolving landscape of Artificial Intelligence. From automation breakthroughs to strategic industry adoption,
                we highlight the innovations shaping the future of work, technology and decision-making.
              </p>
            </div>
          </div>

        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 sm:gap-8 text-center">
            <div className="px-2">
              <div className="text-3xl sm:text-4xl font-bold text-orange-500 mb-2">800+</div>
              <div className="text-sm sm:text-base text-gray-600">AI Tools Analyzed</div>
            </div>
            <div className="px-2">
              <div className="text-3xl sm:text-4xl font-bold text-orange-500 mb-2">10K+</div>
              <div className="text-sm sm:text-base text-gray-600">Businesses Helped</div>
            </div>
            <div className="px-2">
              <div className="text-3xl sm:text-4xl font-bold text-orange-500 mb-2">85%</div>
              <div className="text-sm sm:text-base text-gray-600">Productivity Increase</div>
            </div>
            <div className="px-2">
              <div className="text-3xl sm:text-4xl font-bold text-orange-500 mb-2">2 Min</div>
              <div className="text-sm sm:text-base text-gray-600">Average Analysis Time</div>
            </div>
          </div>
        </div>
      </section>




































































      {/* CTA Section */}
      <section className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold mb-4 sm:mb-6 text-black px-2">
            Ready to Transform Your Business with AI?
          </h2>
          <p className="text-base sm:text-lg md:text-xl mb-6 sm:mb-8 text-gray-600 px-4">
            Join thousands of businesses that have already discovered their perfect AI strategy.
            Get started today and see results in minutes.
          </p>
          <div className="flex justify-center mt-8">
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate('/signup')}
              className="text-base sm:text-lg px-8 py-4 w-full sm:w-auto shadow-lg hover:shadow-xl transition-all">
              <i className="ri-arrow-right-line mr-2"></i>
              Start your analysis now
            </Button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
