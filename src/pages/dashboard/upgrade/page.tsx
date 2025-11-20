import { useState, useEffect } from 'react';
import { useCurrentUser } from "./../../../api/user";
import PayPalCheckout from './paypal';
import FlutterwaveCheckout from './flutterwave';
import StripeCheckout from './stripe';

interface PayPalResponse {
  paymentId: string;
}

interface FlutterwaveResponse {
  transaction_id: string;
}

interface StripeResponse {
  paymentIntentId: string;
}

type PaymentResponse = PayPalResponse | FlutterwaveResponse | StripeResponse;

interface Feature {
  icon: string;
  title: string;
  description: string;
}

// PayPal Logo Component
const PayPalLogo = () => (
  <svg viewBox="0 0 124 33" className="h-5 w-auto" fill="currentColor">
    <path d="M46.211 6.749h-6.839a.95.95 0 0 0-.939.802l-2.766 17.537a.57.57 0 0 0 .564.658h3.265a.95.95 0 0 0 .939-.803l.746-4.73a.95.95 0 0 1 .938-.803h2.165c4.505 0 7.105-2.18 7.784-6.5.306-1.89.013-3.375-.872-4.415-.972-1.142-2.696-1.746-4.985-1.746zM47 13.154c-.374 2.454-2.249 2.454-4.062 2.454h-1.032l.724-4.583a.57.57 0 0 1 .563-.481h.473c1.235 0 2.4 0 3.002.704.359.42.469 1.044.332 1.906zM66.654 13.075h-3.275a.57.57 0 0 0-.563.481l-.145.916-.229-.332c-.709-1.029-2.29-1.373-3.868-1.373-3.619 0-6.71 2.741-7.312 6.586-.313 1.918.132 3.752 1.22 5.031.998 1.176 2.426 1.666 4.125 1.666 2.916 0 4.533-1.875 4.533-1.875l-.146.91a.57.57 0 0 0 .562.66h2.95a.95.95 0 0 0 .939-.803l1.77-11.209a.568.568 0 0 0-.561-.658zm-4.565 6.374c-.316 1.871-1.801 3.127-3.695 3.127-.951 0-1.711-.305-2.199-.883-.484-.574-.668-1.391-.514-2.301.295-1.855 1.805-3.152 3.67-3.152.93 0 1.686.309 2.184.892.499.589.697 1.411.554 2.317zM84.096 13.075h-3.291a.954.954 0 0 0-.787.417l-4.539 6.686-1.924-6.425a.953.953 0 0 0-.912-.678h-3.234a.57.57 0 0 0-.541.754l3.625 10.638-3.408 4.811a.57.57 0 0 0 .465.9h3.287a.949.949 0 0 0 .781-.408l10.946-15.8a.57.57 0 0 0-.468-.895z" fill="#003087"/>
    <path d="M94.992 6.749h-6.84a.95.95 0 0 0-.938.802l-2.766 17.537a.569.569 0 0 0 .562.658h3.51a.665.665 0 0 0 .656-.562l.785-4.971a.95.95 0 0 1 .938-.803h2.164c4.506 0 7.105-2.18 7.785-6.5.307-1.89.012-3.375-.873-4.415-.971-1.142-2.694-1.746-4.983-1.746zm.789 6.405c-.373 2.454-2.248 2.454-4.062 2.454h-1.031l.725-4.583a.568.568 0 0 1 .562-.481h.473c1.234 0 2.4 0 3.002.704.359.42.468 1.044.331 1.906zM115.434 13.075h-3.273a.567.567 0 0 0-.562.481l-.145.916-.23-.332c-.709-1.029-2.289-1.373-3.867-1.373-3.619 0-6.709 2.741-7.311 6.586-.312 1.918.131 3.752 1.219 5.031 1 1.176 2.426 1.666 4.125 1.666 2.916 0 4.533-1.875 4.533-1.875l-.146.91a.57.57 0 0 0 .564.66h2.949a.95.95 0 0 0 .938-.803l1.771-11.209a.571.571 0 0 0-.565-.658zm-4.565 6.374c-.314 1.871-1.801 3.127-3.695 3.127-.949 0-1.711-.305-2.199-.883-.484-.574-.666-1.391-.514-2.301.297-1.855 1.805-3.152 3.67-3.152.93 0 1.686.309 2.184.892.501.589.699 1.411.554 2.317zM119.295 7.23l-2.807 17.858a.569.569 0 0 0 .562.658h2.822c.469 0 .867-.34.939-.803l2.768-17.536a.57.57 0 0 0-.562-.659h-3.16a.571.571 0 0 0-.562.482z" fill="#009cde"/>
    <path d="M7.266 29.154l.523-3.322-1.165-.027H1.061L4.927 1.292a.316.316 0 0 1 .314-.268h9.38c3.114 0 5.263.648 6.385 1.927.526.6.861 1.227 1.023 1.917.17.724.173 1.589.007 2.644l-.012.077v.676l.526.298a3.69 3.69 0 0 1 1.065.812c.45.513.741 1.165.864 1.938.127.795.085 1.741-.123 2.812-.24 1.232-.628 2.305-1.152 3.183a6.547 6.547 0 0 1-1.825 2c-.696.494-1.523.869-2.458 1.109-.906.236-1.939.355-3.072.355h-.73c-.522 0-1.029.188-1.427.525a2.21 2.21 0 0 0-.744 1.328l-.055.299-.924 5.855-.042.215c-.011.068-.03.102-.058.125a.155.155 0 0 1-.096.035H7.266z" fill="#003087"/>
    <path d="M23.048 7.667c-.028.179-.06.362-.096.55-1.237 6.351-5.469 8.545-10.874 8.545H9.326c-.661 0-1.218.48-1.321 1.132L6.596 26.83l-.399 2.533a.704.704 0 0 0 .695.814h4.881c.578 0 1.069-.42 1.16-.99l.048-.248.919-5.832.059-.32c.09-.572.582-.992 1.16-.992h.73c4.729 0 8.431-1.92 9.513-7.476.452-2.321.218-4.259-.978-5.622a4.667 4.667 0 0 0-1.336-1.03z" fill="#009cde"/>
    <path d="M21.754 7.151a9.757 9.757 0 0 0-1.203-.267 15.284 15.284 0 0 0-2.426-.177h-7.352a1.172 1.172 0 0 0-1.159.992L8.05 17.605l-.045.289a1.336 1.336 0 0 1 1.321-1.132h2.752c5.405 0 9.637-2.195 10.874-8.545.037-.188.068-.371.096-.55a6.594 6.594 0 0 0-1.017-.429 9.045 9.045 0 0 0-.277-.087z" fill="#012169"/>
  </svg>
);

// Flutterwave Logo Component
const FlutterwaveLogo = () => (
  <svg viewBox="0 0 200 40" className="h-7 w-auto" fill="none" xmlns="http://www.w3.org/2000/svg">
    <g transform="translate(38, 12)">
      <text x="0" y="10" fontFamily="Arial, sans-serif" fontSize="20" fontWeight="400" fill="#1A1A1A">
        Flutter<tspan fontWeight="700">wave</tspan>
      </text>
    </g>
  </svg>
);

// Stripe Logo Component
const StripeLogo = () => (
  <svg viewBox="0 0 60 25" className="h-6 w-auto" fill="currentColor">
    <path d="M59.64 14.28h-8.06c.19 1.93 1.6 2.55 3.2 2.55 1.64 0 2.96-.37 4.05-.95v3.32a8.33 8.33 0 0 1-4.56 1.1c-4.01 0-6.83-2.5-6.83-7.48 0-4.19 2.39-7.52 6.3-7.52 3.92 0 5.96 3.28 5.96 7.5 0 .4-.04 1.26-.06 1.48zm-5.92-5.62c-1.03 0-2.17.73-2.17 2.58h4.25c0-1.85-1.07-2.58-2.08-2.58zM40.95 20.3c-1.44 0-2.32-.6-2.9-1.04l-.02 4.63-4.12.87V5.57h3.76l.08 1.02a4.7 4.7 0 0 1 3.23-1.29c2.9 0 5.62 2.6 5.62 7.4 0 5.23-2.7 7.6-5.65 7.6zM40 8.95c-.95 0-1.54.34-1.97.81l.02 6.12c.4.44.98.78 1.95.78 1.52 0 2.54-1.65 2.54-3.87 0-2.15-1.04-3.84-2.54-3.84zM28.24 5.57h4.13v14.44h-4.13V5.57zm0-4.7L32.37 0v3.36l-4.13.88V.88zm-4.32 9.35v9.79H19.8V5.57h3.7l.12 1.22c1-1.77 3.07-1.41 3.62-1.22v3.79c-.52-.17-2.29-.43-3.32.86zm-8.55 4.72c0 2.43 2.6 1.68 3.12 1.46v3.36c-.55.3-1.54.54-2.89.54a4.15 4.15 0 0 1-4.27-4.24l.01-13.17 4.02-.86v3.54h3.14V9.1h-3.13v5.85zm-4.91.7c0 2.97-2.31 4.66-5.73 4.66a11.2 11.2 0 0 1-4.46-.93v-3.93c1.38.75 3.1 1.31 4.46 1.31.92 0 1.53-.24 1.53-1C6.26 13.77 0 14.51 0 9.95 0 7.04 2.28 5.3 5.62 5.3c1.36 0 2.72.2 4.09.75v3.88a9.23 9.23 0 0 0-4.1-1.06c-.86 0-1.44.25-1.44.93 0 1.85 6.29.97 6.29 5.88z" fillRule="evenodd"/>
  </svg>
);

export default function UpgradePage() {
  const [isYearly, setIsYearly] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showPaymentOptions, setShowPaymentOptions] = useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<'stripe' | 'paypal' | 'flutterwave' | null>(null);

  const { data: user, isLoading, isError } = useCurrentUser();

  useEffect(() => {
    const timer = setTimeout(() => {
      window.scrollTo(0, 0);
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (showPaymentOptions) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [showPaymentOptions]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex items-center justify-center p-4">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (isError || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex items-center justify-center p-4">
        <div className="text-center max-w-md mx-auto bg-white p-8 rounded-2xl shadow-xl">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-red-600 text-4xl">🔒</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
            Please Log In
          </h1>
          <p className="text-lg text-gray-600 mb-6">
            You need to be logged in to upgrade your account.
          </p>
          <button
            onClick={() => window.location.href = '/login'}
            className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-6 py-3 rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  const userData = {
    email: user.email,
    name: user.name || 'User',
    id: user.id
  };

  const currentAmount = isYearly ? 290 : 29.95;
  const planType = isYearly ? 'yearly' : 'monthly';

  const handleUpgrade = () => {
    setShowPaymentOptions(true);
    setSelectedPaymentMethod(null);
  };

  const handlePaymentMethodSelect = (method: 'stripe' | 'paypal' | 'flutterwave') => {
    setSelectedPaymentMethod(method);
  };

  const handlePaymentSuccess = (response: PaymentResponse) => {
    setIsProcessing(false);
    setShowSuccess(true);
    
    setTimeout(() => {
      alert('Redirecting to dashboard...');
    }, 2000);
  };

  const handlePaymentError = (error: string) => {
    setIsProcessing(false);
    alert(`Payment failed: ${error}. Please try again.`);
  };

  const features: Feature[] = [
    {
      icon: '🔔',
      title: 'Unlimited Opportunity Alerts',
      description: 'Get access to all business opportunities and market insights without any limits'
    },
    {
      icon: '🧠',
      title: 'Advanced AI Insights',
      description: 'Deep AI analysis with predictive analytics and personalized recommendations'
    },
    {
      icon: '🗺️',
      title: 'Detailed Action Plans',
      description: 'Step-by-step implementation guides with timelines and resource requirements'
    },
    {
      icon: '⭐',
      title: 'Priority Scoring System',
      description: 'Advanced scoring algorithms to prioritize opportunities by potential ROI'
    },
    {
      icon: '⏰',
      title: 'Real-time Notifications',
      description: 'Instant alerts for time-sensitive opportunities and market changes'
    },
    {
      icon: '🎧',
      title: 'Premium Support',
      description: '24/7 priority support with dedicated account manager and consultation calls'
    }
  ];

  if (showSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex items-center justify-center p-4">
        <div className="text-center max-w-md mx-auto bg-white p-8 rounded-2xl shadow-xl">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-green-600 text-4xl">✓</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
            Welcome to Pro!
          </h1>
          <p className="text-lg text-gray-600 mb-8">
            Your upgrade was successful. You now have access to all pro features.
          </p>
          
          <a 
            href="/dashboard"
            className="inline-flex items-center justify-center px-8 py-3 
                       border border-transparent text-base font-medium rounded-xl 
                       text-white bg-orange-600 hover:bg-orange-700 
                       shadow-lg transition duration-150 ease-in-out 
                       transform hover:scale-105 active:scale-95 
                       focus:outline-none focus:ring-4 focus:ring-orange-500 focus:ring-opacity-50"
            role="button"
          >
            Enjoy Aitugo+
            <svg className="ml-2 -mr-1 w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd"></path>
            </svg>
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Upgrade to Pro
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Unlock the full power of AI-driven business insights and take your strategy to the next level
          </p>
        </div>

        <div className="mb-16">
          <div className="flex items-center justify-center mb-8">
            <span className={`text-sm font-medium mr-3 transition-colors ${!isYearly ? 'text-gray-900' : 'text-gray-500'}`}>
              Monthly
            </span>
            <button
              onClick={() => setIsYearly(!isYearly)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
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
              <span className="ml-3 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Save 17%
              </span>
            )}
          </div>

          <div className="max-w-lg mx-auto">
            <div className="bg-white rounded-2xl shadow-xl border-2 border-orange-200 p-8 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-1 text-xs font-semibold rounded-bl-lg">
                MOST POPULAR
              </div>
              
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">Pro Plan</h3>
                <div className="flex items-center justify-center mb-4">
                  <span className="text-5xl font-bold text-gray-900">
                    ${currentAmount}
                  </span>
                  <span className="text-lg text-gray-600 ml-2">
                    /{isYearly ? 'year' : 'month'}
                  </span>
                </div>
                {isYearly && (
                  <p className="text-sm text-gray-500">
                    <span className="line-through">$348/year</span>
                    <span className="text-green-600 font-semibold"> - Save $58</span>
                  </p>
                )}
              </div>

              {!showPaymentOptions ? (
                <button
                  onClick={handleUpgrade}
                  disabled={isProcessing}
                  className={`w-full py-4 px-6 rounded-xl font-semibold text-lg transition-all ${
                    isProcessing
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white hover:from-orange-600 hover:to-orange-700 transform hover:scale-105 shadow-lg'
                  }`}
                >
                 Upgrade Now
                </button>
              ) : (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900 text-center mb-4">
                    Choose Payment Method
                  </h3>
                  
                  <div className="grid grid-cols-3 gap-3 mb-6">
                    {/* Stripe */}
                    <button
                      onClick={() => handlePaymentMethodSelect('stripe')}
                      className={`group relative py-4 px-3 rounded-xl font-medium transition-all border-2 ${
                        selectedPaymentMethod === 'stripe'
                          ? 'bg-purple-50 border-purple-500 shadow-lg scale-105'
                          : 'bg-white border-gray-200 hover:border-purple-300 hover:shadow-md'
                      }`}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={`transition-colors ${
                          selectedPaymentMethod === 'stripe' ? 'text-purple-600' : 'text-gray-600 group-hover:text-purple-600'
                        }`}>
                          <StripeLogo />
                        </div>
                        {selectedPaymentMethod === 'stripe' && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                            </svg>
                          </div>
                        )}
                      </div>
                    </button>

                    {/* PayPal */}
                    <button
                      onClick={() => handlePaymentMethodSelect('paypal')}
                      className={`group relative py-4 px-3 rounded-xl font-medium transition-all border-2 ${
                        selectedPaymentMethod === 'paypal'
                          ? 'bg-blue-50 border-blue-500 shadow-lg scale-105'
                          : 'bg-white border-gray-200 hover:border-blue-300 hover:shadow-md'
                      }`}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={`transition-colors ${
                          selectedPaymentMethod === 'paypal' ? 'text-blue-600' : 'text-gray-600 group-hover:text-blue-600'
                        }`}>
                          <PayPalLogo />
                        </div>
                        {selectedPaymentMethod === 'paypal' && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                            </svg>
                          </div>
                        )}
                      </div>
                    </button>
                    
                    {/* Flutterwave */}
                    <button
                      onClick={() => handlePaymentMethodSelect('flutterwave')}
                      className={`group relative py-4 px-3 rounded-xl font-medium transition-all border-2 ${
                        selectedPaymentMethod === 'flutterwave'
                          ? 'bg-orange-50 border-orange-500 shadow-lg scale-105'
                          : 'bg-white border-gray-200 hover:border-orange-300 hover:shadow-md'
                      }`}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={`transition-colors ${
                          selectedPaymentMethod === 'flutterwave' ? 'text-orange-600' : 'text-gray-600 group-hover:text-orange-600'
                        }`}>
                          <FlutterwaveLogo />
                        </div>
                        {selectedPaymentMethod === 'flutterwave' && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-orange-600 rounded-full flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
                            </svg>
                          </div>
                        )}
                      </div>
                    </button>
                  </div>

                  <div className="min-h-[140px] bg-gray-50 rounded-xl p-6 border border-gray-200">
                    {selectedPaymentMethod === 'stripe' && (
                      <div key={`stripe-${currentAmount}`}>
                        <StripeCheckout
                          amount={currentAmount}
                          email={userData.email}
                          name={userData.name}
                          planType={planType}
                          userId={userData.id}
                          onSuccess={handlePaymentSuccess}
                          onError={handlePaymentError}
                        />
                      </div>
                    )}

                    {selectedPaymentMethod === 'paypal' && (
                      <div key={`paypal-${currentAmount}`}>
                        <PayPalCheckout
                          amount={currentAmount}
                          onSuccess={handlePaymentSuccess}
                          onError={handlePaymentError}
                        />
                      </div>
                    )}
                    
                    {selectedPaymentMethod === 'flutterwave' && (
                      <div key={`flutterwave-${currentAmount}`}>
                        <FlutterwaveCheckout
                          amount={currentAmount}
                          email={userData.email}
                          name={userData.name}
                          planType={planType}
                          onSuccess={handlePaymentSuccess}
                          onError={handlePaymentError}
                        />
                      </div>
                    )}

                    {!selectedPaymentMethod && (
                      <div className="text-center py-8">
                        <div className="text-4xl mb-3">🔒</div>
                        <p className="text-gray-500 font-medium">Select a payment method above</p>
                        <p className="text-sm text-gray-400 mt-1">Secure payment powered by industry leaders</p>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setShowPaymentOptions(false);
                      setSelectedPaymentMethod(null);
                    }}
                    className="w-full py-3 px-4 text-gray-600 hover:text-gray-800 font-medium transition-colors rounded-lg hover:bg-gray-100"
                  >
                    ← Back to Plan Selection
                  </button>
                </div>
              )}

              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
                  <div className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                    </svg>
                    Secure Payment
                  </div>
                  <span>•</span>
                  <div>30-day Money-back</div>
                  <span>•</span>
                  <div>Cancel Anytime</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-16">
          <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">
            Everything You Get with Pro
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <div key={index} className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div className="text-4xl mb-3">{feature.icon}</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 text-sm">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}