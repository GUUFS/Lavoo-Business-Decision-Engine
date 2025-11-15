
import { useNavigate } from 'react-router-dom';
import Header from '../../components/feature/Header';
import Footer from '../../components/feature/Footer';
import Button from '../../components/base/Button';
import { useState } from 'react';

export default function Home() {
  const navigate = useNavigate();
  const [currentSlide, setCurrentSlide] = useState(0);
  const [businessPrompt, setBusinessPrompt] = useState("")

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % 2);
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + 2) % 2);
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
    
    
      {/* Reviews Section */}
      <section className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white" >
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>  
          <div style={{ textAlign: 'center', marginBottom: '48px' }}>
            <h2 style={{ fontSize: window.innerWidth >= 768 ? '40px' : '32px', fontWeight: 'bold', color: '#111827',  marginBottom: '16px'}}>
              What Our Customers Say
            </h2> 
            <p style={{ fontSize: '20px', color: '#4b5563',maxWidth: '768px', margin: '0 auto 16px' }}>             
              Join thousands of businesses that trust our AI analyst for data-driven insights
            </p>
            <div style={{ display: 'flex',alignItems: 'center', justifyContent: 'center',gap: '8px', marginTop: '16px' }}> 
              <div style={{ display: 'flex' }}>
                {[...Array(5)].map((_, i) => (
                  <i key={i} className="ri-star-fill" style={{ color: '#fbbf24', fontSize: '20px' }}></i>
                ))}
              </div>
              <span style={{ fontSize: '18px', fontWeight: '600', color: '#111827' }}>4.9/5</span>
              <span style={{ color: '#4b5563' }}>(2,847+ reviews)</span>
            </div>
          </div>

          <div style={{ position: 'relative' }}>
            {/* Reviews Container */}
            <div style={{ overflow: 'hidden' }}>
              <div style={{ display: 'flex',transition: 'transform 0.5s ease-in-out',transform: `translateX(-${currentSlide * 100}%)`}}> 
                {/* Slide 1 */}
                <div style={{ width: '100%', flexShrink: 0 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: window.innerWidth >= 768 ? 'repeat(3, 1fr)' : '1fr', gap: '32px' }}>
                     <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px',
                         boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                          <div style={{  width: '48px', height: '48px',backgroundColor: '#fef2f2',borderRadius: '50%',display: 'flex',
                                alignItems: 'center', justifyContent: 'center', marginRight: '16px'}}>
                              <span style={{ color: '#dc2626', fontWeight: '600' }}>SJ</span>
                          </div>
                        <div>
                        <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>Sarah Johnson</h4>
                        <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>CEO, TechStart Inc.</p>
                      </div>
                    </div>
                    <div style={{ display: 'flex', marginBottom: '16px' }}>
                        {[...Array(5)].map((_, i) => (
                          <i key={i} className="ri-star-fill" style={{ color: '#fbbf24' }}></i>
                        ))}
                    </div>
                    <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                        "This AI analyst transformed our decision-making process. We increased revenue by 34% in just 3 months using the insights provided. Absolutely game-changing!"
                    </p>
                  </div>  
                  <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px',
                       boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb'}}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                      <div style={{ width: '48px', height: '48px', backgroundColor: '#fef2f2',borderRadius: '50%',
                           display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '16px' }}>
                          <span style={{ color: '#dc2626', fontWeight: '600' }}>MC</span>
                      </div>
                      <div>
                        <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>Michael Chen</h4>
                        <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>Marketing Director, GrowthCorp</p>
                      </div> 
                    </div>
                    <div style={{ display: 'flex', marginBottom: '16px' }}>
                        {[...Array(5)].map((_, i) => (
                          <i key={i} className="ri-star-fill" style={{ color: '#fbbf24' }}></i>
                        ))}
                    </div>
                    <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                        "The predictive analytics helped us identify market trends before our competitors. Our marketing ROI improved by 150%. Best investment we've made!"
                    </p>
                  </div>     
                  <div style={{  backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px',
                          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                      <div style={{  width: '48px',height: '48px', backgroundColor: '#fef2f2', borderRadius: '50%',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '16px' }}>
                        <span style={{ color: '#dc2626', fontWeight: '600' }}>ER</span>  
                      </div>    
                      <div>
                        <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>Emily Rodriguez</h4>
                        <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>Operations Manager, LogiFlow</p>
                      </div>     
                    </div>
                    <div style={{ display: 'flex', marginBottom: '16px' }}>
                      {[...Array(4)].map((_, i) => (
                        <i key={i} className="ri-star-fill" style={{ color: '#fbbf24' }}></i>
                      ))}
                      <i className="ri-star-line" style={{ color: '#fbbf24' }}></i>
                    </div>
                    <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                        "Streamlined our operations and reduced costs by 28%. The AI recommendations are incredibly accurate and easy to implement. Highly recommended!"
                    </p>
                  </div>
                </div>
              </div>       
               {/* Slide 2 */}
                <div style={{ width: '100%', flexShrink: 0 }}>
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: window.innerWidth >= 768 ? 'repeat(3, 1fr)' : '1fr', 
                    gap: '32px' 
                  }}>
                    <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px', 
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{ width: '48px', height: '48px', backgroundColor: '#fef2f2', borderRadius: '50%', display: 'flex', 
                          alignItems: 'center', justifyContent: 'center', marginRight: '16px' }}>
                          <span style={{ color: '#dc2626', fontWeight: '600' }}>DK</span>
                        </div>
                        <div>
                          <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>David Kim</h4>
                          <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>CFO, FinanceFirst</p>
                        </div>
                      </div>
                      <div style={{ display: 'flex', marginBottom: '16px' }}>
                        {[...Array(5)].map((_, i) => (
                          <i key={i} className="ri-star-fill" style={{ color: '#fbbf24' }}></i>
                        ))}
                      </div>
                      <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                        "The financial risk analysis saved us from a potentially disastrous investment. The AI's accuracy in predicting market volatility is remarkable."
                      </p>
                    </div>

                    <div style={{ backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px',
                                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{ width: '48px', height: '48px', backgroundColor: '#fef2f2', borderRadius: '50%', 
                          display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '16px' }}>
                          <span style={{ color: '#dc2626', fontWeight: '600' }}>LT</span>
                        </div>
                        <div>
                          <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>Lisa Thompson</h4>
                          <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>Product Manager, InnovateTech</p>
                        </div>
                      </div>
                      <div style={{ display: 'flex', marginBottom: '16px' }}>
                        {[...Array(5)].map((_, i) => (
                          <i key={i} className="ri-star-fill" style={{ color: '#fbbf24' }}></i>
                        ))}
                      </div>
                      <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                        "Customer behavior insights helped us redesign our product strategy. User engagement increased by 89% and customer satisfaction scores are at an all-time high."
                      </p>
                    </div>

                    <div style={{ 
                      backgroundColor: '#ffffff', borderRadius: '12px', padding: '24px', 
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', border: '1px solid #e5e7eb' }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
                        <div style={{ 
                          width: '48px', height: '48px', backgroundColor: '#fef2f2', borderRadius: '50%',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '16px'}}>
                          <span style={{ color: '#dc2626', fontWeight: '600' }}>JW</span>
                        </div>
                        <div>
                          <h4 style={{ fontWeight: '600', color: '#111827', margin: 0 }}>James Wilson</h4>
                          <p style={{ fontSize: '14px', color: '#4b5563', margin: 0 }}>Founder, StartupSuccess</p>
                        </div>
                      </div>
                      <div style={{ display: 'flex', marginBottom: '16px' }}>
                        {[...Array(5)].map((_, i) => (
                          <i key={i} className="ri-star-fill" style={{ color: '#fbbf24' }}></i>
                        ))}
                      </div>
                      <p style={{ color: '#374151', lineHeight: '1.6', margin: 0 }}>
                        "As a startup, we needed enterprise-level insights without the enterprise budget. This AI analyst delivered exactly that and helped us secure Series A funding."
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation Arrows */}
            <button
              onClick={prevSlide}
              style={{ 
                position: 'absolute', left: '-16px', top: '50%', transform: 'translateY(-50%)', width: '48px', height: '48px', backgroundColor: '#ffffff', borderRadius: '50%', 
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4b5563', 
                border: 'none', cursor: 'pointer', zIndex: 10, transition: 'color 0.3s ease'}}
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
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: '32px',  gap: '8px' }}>
              {[0, 1].map((slide) => (
              <button
                  key={slide}
                  onClick={() => setCurrentSlide(slide)}
                  style={{ 
                    width: '12px', height: '12px', borderRadius: '50%', border: 'none',cursor: 'pointer',
                    backgroundColor: currentSlide === slide ? '#dc2626' : '#d1d5db', transition: 'background-color 0.3s ease'
                    }}
              />
              ))}
            </div>
          </div>
        </div>
      </section>             

      {/* Blog Section */}
      <section id="blog" className="py-12 sm:py-16 md:py-20 bg-gradient-to-br from-orange-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10 sm:mb-12 md:mb-16">
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-black mb-3 sm:mb-4 px-2">
              Blog
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
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">AI News</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                Our AI engine provides timely news on AI innovations, products, news across various industries, from cutting-edge research to 
                real-world applications involving technologies transforming the future.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-shadow">
              <div className="w-14 h-14 sm:w-16 sm:h-16 bg-orange-100 rounded-2xl flex items-center justify-center mb-4 sm:mb-6">
                <i className="ri-tools-line text-orange-500 text-xl sm:text-2xl"></i>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-black mb-3 sm:mb-4">AI Learn</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">
                AItugo+ provides you with current trajectories in artificial intelligence, providing you with tailored research and 
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
          <div>
            <Button 
              variant="primary" 
              size="lg"
              onClick={() => navigate('/signup')}
              className="text-base sm:text-lg px-6 sm:px-8 py-3 sm:py-4 w-full sm:w-auto mx-4">
              <i className="ri-arrow-right-line mr-2"></i>
              Start your analyis now
            </Button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
