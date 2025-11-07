
import { useNavigate } from 'react-router-dom';
import Header from '../../components/feature/Header';
import Footer from '../../components/feature/Footer';
import Button from '../../components/base/Button';
import { useState } from 'react';

export default function Home() {
  const navigate = useNavigate();
  const [businessPrompt, setBusinessPrompt] = useState("")

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
