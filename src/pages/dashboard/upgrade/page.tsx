import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
// import FlutterwaveCheckout from './flutterwave';
import StripeCheckoutWithSavedCard from './checkoutForm';

export default function UpgradePage() {
  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly'>('monthly');
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);
  const [paymentError, setPaymentError] = useState('');
  const [userData, setUserData] = useState<any>(null);
  const [showPayoutSetup, setShowPayoutSetup] = useState(false);
  const [payoutMethod, setPayoutMethod] = useState<'stripe' | 'flutterwave' | null>(null);
  const [payoutAccount, setPayoutAccount] = useState<any>(null);
  const [loadingPayoutAccount, setLoadingPayoutAccount] = useState(false);
  const [showCheckout, setShowCheckout] = useState(false);


  // Flutterwave bank details
  const [bankDetails, setBankDetails] = useState({
    bank_name: '',
    account_number: '',
    account_name: '',
    bank_code: '',
  });
  const [verifyingAccount, setVerifyingAccount] = useState(false);
  const [savingBankDetails, setSavingBankDetails] = useState(false);
  const [accountVerifyError, setAccountVerifyError] = useState('');

  // Dynamic Pricing State
  const [pricing, setPricing] = useState({
    monthly: 29.95,
    yearly: 290.00
  });

  const plans = {
    monthly: { price: pricing.monthly, name: 'Monthly Plan' },
    yearly: { price: pricing.yearly, name: 'Yearly Plan' }
  };

  useEffect(() => {
    fetchUserData();
    fetchPayoutAccount();
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      // We don't need auth for this specific read in many apps, but here we might.
      // However, settings might be public or require user auth. 
      // Using existing token from document.cookie as in other methods here
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch('http://localhost:8000/api/control/settings', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        // Update pricing if data exists
        if (data.monthly_price || data.yearly_price) {
          setPricing({
            monthly: data.monthly_price || 29.95,
            yearly: data.yearly_price || 290.00
          });
        }
      }
    } catch (error) {
      console.error("Error fetching settings for pricing:", error);
    }
  };

  const fetchUserData = async () => {
    try {
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch('http://localhost:8000/user/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setUserData(data);
      }
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  };

  const fetchPayoutAccount = async () => {
    try {
      setLoadingPayoutAccount(true);
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch('http://localhost:8000/api/commissions/payout-account', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setPayoutAccount(data.data);
        }
      }
    } catch (error) {
      console.error('Error fetching payout account:', error);
    } finally {
      setLoadingPayoutAccount(false);
    }
  };

  const connectStripe = async () => {
    try {
      setIsProcessing(true);
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch('http://localhost:8000/api/stripe/connect/onboard', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to initiate Stripe Connect');
      }

      const data = await response.json();
      window.location.href = data.onboarding_url;
    } catch (error: any) {
      setPaymentError(error.message || 'Failed to connect Stripe account');
      setIsProcessing(false);
    }
  };

  const verifyBankAccount = async () => {
    if (!bankDetails.account_number || !bankDetails.bank_code) {
      setAccountVerifyError('Please enter account number and bank code');
      return;
    }

    try {
      setVerifyingAccount(true);
      setAccountVerifyError('');

      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      console.log('Verifying account:', {
        account_number: bankDetails.account_number,
        bank_code: bankDetails.bank_code.toString()
      });

      const response = await fetch('http://localhost:8000/api/payments/flutterwave/verify-account', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          account_number: bankDetails.account_number,
          bank_code: bankDetails.bank_code,
        }),
      });

      const data = await response.json();
      console.log('Verification response:', data);

      if (response.ok && data.status === 'success') {
        setBankDetails(prev => ({
          ...prev,
          account_name: data.account_name
        }));
        setAccountVerifyError('');
        toast.success(`Account verified: ${data.account_name}`);
      } else {
        const errorMsg = data.detail || 'Account verification failed';
        setAccountVerifyError(errorMsg);
        console.error('Verification failed:', errorMsg);
      }
    } catch (error: any) {
      console.error('Error verifying account:', error);
      const errorMsg = error.message || 'Failed to verify account. Please try again.';
      setAccountVerifyError(errorMsg);
    } finally {
      setVerifyingAccount(false);
    }
  };

  const saveBankDetails = async () => {
    if (!bankDetails.bank_name || !bankDetails.account_number || !bankDetails.account_name) {
      toast.error('Please fill in all required fields and verify your account');
      return;
    }

    try {
      setSavingBankDetails(true);
      const token = document.cookie
        .split('; ')
        .find((row) => row.startsWith('access_token='))
        ?.split('=')[1];

      const response = await fetch('/api/commissions/payout-account', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          payment_method: 'flutterwave',
          ...bankDetails
        }),
      });

      if (response.ok) {
        toast.success('Bank details saved successfully!');
        setShowPayoutSetup(false);
        setPayoutMethod(null);
        fetchPayoutAccount();
        // Reset form
        setBankDetails({
          bank_name: '',
          account_number: '',
          account_name: '',
          bank_code: '',
        });
        setAccountVerifyError('');
      } else {
        const errorData = await response.json();
        toast.error(`Failed to save: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error saving bank details:', error);
      toast.error('Failed to save bank details');
    } finally {
      setSavingBankDetails(false);
    }
  };

  const handlePaymentSuccess = (response: any) => {
    console.log('Payment successful:', response);
    setPaymentSuccess(true);
    setIsProcessing(false);
    setPaymentError('');

    setTimeout(() => {
      window.location.href = '/dashboard';
    }, 3000);
  };

  const handlePaymentError = (error: string) => {
    console.error('Payment error:', error);
    setPaymentError(error);
    setIsProcessing(false);
  };

  if (!userData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (paymentSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <i className="ri-check-line text-3xl text-green-600"></i>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h2>
          <p className="text-gray-600 mb-6">
            Your subscription has been activated. Redirecting to dashboard...
          </p>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-2">
            Upgrade Your Plan
          </h1>
          <p className="text-gray-600">
            Choose the plan that works best for you
          </p>
        </div>

        {/* Payout Setup Banner */}
        {!loadingPayoutAccount && !payoutAccount && (
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-xl p-6 mb-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <i className="ri-bank-line text-purple-600 text-xl"></i>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">Set Up Payout Account</h3>
                  <p className="text-sm text-gray-600">
                    Earn 50% commission on referrals! Set up your payout method to receive earnings.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowPayoutSetup(true)}
                className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700 transition-colors font-medium whitespace-nowrap"
              >
                Set Up Now
              </button>
            </div>
          </div>
        )}

        {/* Payout Account Status */}
        {payoutAccount && (
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6 mb-8">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <i className="ri-check-line text-green-600 text-xl"></i>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-1">Payout Account Active</h3>
                <p className="text-sm text-gray-600 mb-2">
                  {payoutAccount.payment_method === 'stripe' && 'Connected with Stripe Connect'}
                  {payoutAccount.payment_method === 'flutterwave' && `Bank: ${payoutAccount.bank_name}`}
                </p>
                <button
                  onClick={() => setShowPayoutSetup(true)}
                  className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                >
                  Update payout method →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Payout Setup Modal */}
        {showPayoutSetup && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Set Up Payout Account</h2>
                <button
                  onClick={() => {
                    setShowPayoutSetup(false);
                    setPayoutMethod(null);
                    setAccountVerifyError('');
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <i className="ri-close-line text-2xl"></i>
                </button>
              </div>

              <div className="p-6">
                {!payoutMethod ? (
                  <div className="space-y-4">
                    <p className="text-gray-600 mb-6">
                      Choose how you'd like to receive your referral commissions (50% of each subscription):
                    </p>

                    {/* Stripe Option */}
                    <button
                      onClick={() => setPayoutMethod('stripe')}
                      className="w-full border-2 border-gray-200 rounded-xl p-6 hover:border-purple-500 hover:bg-purple-50 transition-all text-left group"
                    >
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-purple-200 transition-colors">
                          <i className="ri-bank-card-line text-purple-600 text-2xl"></i>
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">Stripe Connect</h3>
                          <p className="text-sm text-gray-600 mb-2">
                            Connect your bank account securely through Stripe. Fast, automated payouts.
                          </p>
                          <div className="flex flex-wrap gap-2">
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">Automated</span>
                            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">Secure</span>
                            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">International</span>
                          </div>
                        </div>
                        <i className="ri-arrow-right-line text-gray-400 text-xl group-hover:text-purple-600 transition-colors"></i>
                      </div>
                    </button>

                    {/* Flutterwave Option */}
                    <button
                      onClick={() => setPayoutMethod('flutterwave')}
                      className="w-full border-2 border-gray-200 rounded-xl p-6 hover:border-orange-500 hover:bg-orange-50 transition-all text-left group"
                    >
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-orange-200 transition-colors">
                          <i className="ri-bank-line text-orange-600 text-2xl"></i>
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-1">Bank Transfer (Flutterwave)</h3>
                          <p className="text-sm text-gray-600 mb-2">
                            Provide your bank details for direct transfers. Perfect for African banks.
                          </p>
                          <div className="flex flex-wrap gap-2">
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">Direct Transfer</span>
                            <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">Africa-Friendly</span>
                          </div>
                        </div>
                        <i className="ri-arrow-right-line text-gray-400 text-xl group-hover:text-orange-600 transition-colors"></i>
                      </div>
                    </button>
                  </div>
                ) : payoutMethod === 'stripe' ? (
                  <div className="space-y-6">
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <div className="flex gap-3">
                        <i className="ri-information-line text-purple-600 text-xl"></i>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-1">Stripe Connect Onboarding</h4>
                          <p className="text-sm text-gray-600">
                            You'll be redirected to Stripe to securely connect your bank account.
                            This usually takes 2-3 minutes.
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-start gap-2">
                        <i className="ri-check-line text-green-600 mt-1"></i>
                        <span className="text-sm text-gray-700">Secure bank verification by Stripe</span>
                      </div>
                      <div className="flex items-start gap-2">
                        <i className="ri-check-line text-green-600 mt-1"></i>
                        <span className="text-sm text-gray-700">Automated payout processing</span>
                      </div>
                      <div className="flex items-start gap-2">
                        <i className="ri-check-line text-green-600 mt-1"></i>
                        <span className="text-sm text-gray-700">Works with most international banks</span>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={() => setPayoutMethod(null)}
                        className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
                      >
                        Back
                      </button>
                      <button
                        onClick={connectStripe}
                        disabled={isProcessing}
                        className="flex-1 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        {isProcessing ? (
                          <>
                            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                            Connecting...
                          </>
                        ) : (
                          <>
                            Connect with Stripe
                            <i className="ri-external-link-line"></i>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                      <div className="flex gap-3">
                        <i className="ri-information-line text-orange-600 text-xl"></i>
                        <div>
                          <h4 className="font-medium text-gray-900 mb-1">Bank Account Details</h4>
                          <p className="text-sm text-gray-600">
                            Enter your bank details to receive commission payouts directly to your account.
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Show error message */}
                    {accountVerifyError && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <div className="flex gap-2">
                          <i className="ri-error-warning-line text-red-600 text-xl flex-shrink-0"></i>
                          <p className="text-sm text-red-600">{accountVerifyError}</p>
                        </div>
                      </div>
                    )}

                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Bank Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={bankDetails.bank_name}
                          onChange={(e) => setBankDetails({ ...bankDetails, bank_name: e.target.value })}
                          placeholder="e.g., Access Bank"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Bank Code <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={bankDetails.bank_code}
                          onChange={(e) => setBankDetails({ ...bankDetails, bank_code: e.target.value })}
                          placeholder="e.g., 044 (for Nigerian banks)"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Required for bank verification. Find your bank code online.
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Account Number <span className="text-red-500">*</span>
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={bankDetails.account_number}
                            onChange={(e) => {
                              setBankDetails({ ...bankDetails, account_number: e.target.value });
                              setAccountVerifyError('');
                            }}
                            placeholder="0123456789"
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                          />
                          <button
                            onClick={verifyBankAccount}
                            disabled={verifyingAccount || !bankDetails.account_number || !bankDetails.bank_code}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                          >
                            {verifyingAccount ? 'Verifying...' : 'Verify'}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Account Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={bankDetails.account_name}
                          onChange={(e) => setBankDetails({ ...bankDetails, account_name: e.target.value })}
                          placeholder="Will be auto-filled after verification"
                          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-gray-50"
                          readOnly
                        />
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={() => {
                          setPayoutMethod(null);
                          setAccountVerifyError('');
                        }}
                        className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium"
                      >
                        Back
                      </button>
                      <button
                        onClick={saveBankDetails}
                        disabled={savingBankDetails || !bankDetails.bank_name || !bankDetails.account_number || !bankDetails.account_name}
                        className="flex-1 px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        {savingBankDetails ? (
                          <>
                            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                            Saving...
                          </>
                        ) : (
                          'Save Bank Details'
                        )}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Plan Selection */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-full p-1 shadow-sm border border-gray-200">
            <button
              onClick={() => {
                setSelectedPlan('monthly');
                setShowCheckout(false); // Reset checkout when switching plans
              }}
              className={`px-6 py-2 rounded-full font-medium transition-all ${selectedPlan === 'monthly'
                ? 'bg-orange-500 text-white shadow-md'
                : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Monthly
            </button>
            <button
              onClick={() => {
                setSelectedPlan('yearly');
                setShowCheckout(false); // Reset checkout when switching plans
              }}
              className={`px-6 py-2 rounded-full font-medium transition-all ${selectedPlan === 'yearly'
                ? 'bg-orange-500 text-white shadow-md'
                : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Yearly
              <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                Save {Math.round(((pricing.monthly * 12 - pricing.yearly) / (pricing.monthly * 12)) * 100)}%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Card */}
        <div className="max-w-lg mx-auto">
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden border-2 border-orange-200">
            <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-6 py-8 text-white text-center">
              <h3 className="text-2xl font-bold mb-2">{plans[selectedPlan].name}</h3>
              <div className="flex items-baseline justify-center gap-2">
                <span className="text-5xl font-bold">${plans[selectedPlan].price}</span>
                <span className="text-orange-100">/{selectedPlan === 'monthly' ? 'month' : 'year'}</span>
              </div>
              {selectedPlan === 'yearly' && (
                <p className="mt-2 text-orange-100 text-sm">
                  That's just ${(pricing.yearly / 12).toFixed(2)}/month - Save ${(pricing.monthly * 12 - pricing.yearly).toFixed(2)}!
                </p>
              )}
            </div>

            <div className="p-6">
              {/* Features */}
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3">
                  <i className="ri-check-line text-green-600 text-xl"></i>
                  <span className="text-gray-700">Unlimited AI Strategy Analysis</span>
                </div>
                <div className="flex items-center gap-3">
                  <i className="ri-check-line text-green-600 text-xl"></i>
                  <span className="text-gray-700">Priority Support</span>
                </div>
                <div className="flex items-center gap-3">
                  <i className="ri-check-line text-green-600 text-xl"></i>
                  <span className="text-gray-700">Advanced Analytics Dashboard</span>
                </div>
                <div className="flex items-center gap-3">
                  <i className="ri-check-line text-green-600 text-xl"></i>
                  <span className="text-gray-700">Export Reports (PDF, CSV)</span>
                </div>
              </div>

              {/* Error Message */}
              {paymentError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-600 text-sm">{paymentError}</p>
                </div>
              )}

              {/* Action Button or Checkout Form */}
              {!showCheckout ? (
                userData.subscription_status === 'active' &&
                  (userData.subscription_plan === 'yearly' || (userData.subscription_plan === 'monthly' && selectedPlan === 'monthly')) ? (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-center">
                    <i className="ri-information-line text-blue-600 text-2xl mb-2 block"></i>
                    <p className="text-blue-800 font-medium">You already have an active {userData.subscription_plan} subscription!</p>
                    <p className="text-blue-600 text-sm mt-1">
                      {userData.subscription_plan === 'monthly' && selectedPlan === 'monthly'
                        ? "You're currently on the monthly plan. Switch to the Yearly plan above to save more!"
                        : "You're already on our best value Yearly plan!"}
                    </p>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowCheckout(true)}
                    className="w-full bg-orange-600 text-white py-4 rounded-lg hover:bg-orange-700 font-semibold text-lg transition-colors flex items-center justify-center gap-2"
                  >
                    <i className="ri-lock-line"></i>
                    Proceed to Secure Checkout
                  </button>
                )
              ) : (
                <StripeCheckoutWithSavedCard
                  amount={plans[selectedPlan].price}
                  email={userData.email}
                  name={userData.name}
                  planType={selectedPlan}
                  onSuccess={handlePaymentSuccess}
                  onError={handlePaymentError}
                  onCancel={() => setShowCheckout(false)}
                />
              )}

              {/* Security Badge */}
              {!showCheckout && (
                <div className="mt-4 text-center">
                  <p className="text-xs text-gray-500 flex items-center justify-center gap-1">
                    <i className="ri-lock-line"></i>
                    Secure payment processing with Stripe
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}