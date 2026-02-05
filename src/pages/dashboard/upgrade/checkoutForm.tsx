
import { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
    Elements,
    CardElement,
    useStripe,
    useElements
} from '@stripe/react-stripe-js';

const STRIPE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
const stripePromise = STRIPE_KEY ? loadStripe(STRIPE_KEY) : null;

// Card Element styling matching your orange/black theme
const CARD_ELEMENT_OPTIONS = {
    style: {
        base: {
            color: '#0A0A0A',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSmoothing: 'antialiased',
            fontSize: '16px',
            '::placeholder': {
                color: '#9CA3AF',
            },
        },
        invalid: {
            color: '#EF4444',
            iconColor: '#EF4444',
        },
    },
    hidePostalCode: false,
};

interface CheckoutFormProps {
    amount: number;
    planType: 'monthly' | 'yearly';
    email: string;
    name: string;
    onSuccess: (response: any) => void;
    onError: (error: string) => void;
    onCancel: () => void;
}

function CheckoutForm({
    amount,
    planType,
    email,
    name,
    onSuccess,
    onError,
    onCancel
}: CheckoutFormProps) {
    const stripe = useStripe();
    const elements = useElements();
    const [processing, setProcessing] = useState(false);
    const [error, setError] = useState<string>('');
    const [cardComplete, setCardComplete] = useState(false);
    const [billingDetails, setBillingDetails] = useState({
        name: name,
        email: email,
        address: {
            line1: '',
            city: '',
            state: '',
            postal_code: '',
            country: 'US',
        },
    });

    const handleSubmit = async () => {
        if (!stripe || !elements) {
            return;
        }

        setProcessing(true);
        setError('');

        try {
            const cardElement = elements.getElement(CardElement);

            if (!cardElement) {
                throw new Error('Card element not found');
            }

            // Step 1: Create payment method with billing details
            const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
                type: 'card',
                card: cardElement,
                billing_details: billingDetails,
            });

            if (pmError) {
                throw new Error(pmError.message);
            }

            // Step 2: Send payment method to backend to create subscription
            const token = document.cookie
                .split('; ')
                .find((row) => row.startsWith('access_token='))
                ?.split('=')[1];

            const response = await fetch('/api/stripe/create-subscription-with-saved-card', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    payment_method_id: paymentMethod.id,
                    plan_type: planType,
                    billing_details: billingDetails,
                }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Subscription creation failed');
            }

            const data = await response.json();

            // Step 3: Handle subscription status
            if (data.status === 'active') {
                // Subscription successful
                onSuccess(data);
            } else if (data.status === 'requires_action') {
                // Handle 3D Secure authentication
                const { error: confirmError } = await stripe.confirmCardPayment(
                    data.client_secret
                );

                if (confirmError) {
                    throw new Error(confirmError.message);
                }

                // After successful 3D Secure, confirm with backend
                const confirmResponse = await fetch('/api/stripe/confirm-subscription', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        subscription_id: data.subscription_id,
                        payment_intent_id: data.payment_intent_id || data.subscription_id,
                    }),
                });

                if (!confirmResponse.ok) {
                    throw new Error('Subscription confirmation failed');
                }

                const confirmData = await confirmResponse.json();
                onSuccess(confirmData);
            } else {
                throw new Error('Unexpected subscription status');
            }
        } catch (err: any) {
            console.error('Payment error:', err);
            setError(err.message || 'An error occurred during payment');
            onError(err.message || 'Payment failed');
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="border-b border-gray-200 pb-4">
                <h3 className="text-lg font-semibold text-gray-900">Payment Details</h3>
                <p className="text-sm text-gray-600 mt-1">
                    Your card will be securely saved for automatic billing
                </p>
            </div>

            {/* Billing Information */}
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Full Name <span className="text-red-500">*</span>
                    </label>
                    <input
                        type="text"
                        value={billingDetails.name}
                        onChange={(e) => setBillingDetails({ ...billingDetails, name: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        required
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Email <span className="text-red-500">*</span>
                    </label>
                    <input
                        type="email"
                        value={billingDetails.email}
                        onChange={(e) => setBillingDetails({ ...billingDetails, email: e.target.value })}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        required
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Address Line 1 <span className="text-red-500">*</span>
                    </label>
                    <input
                        type="text"
                        value={billingDetails.address.line1}
                        onChange={(e) => setBillingDetails({
                            ...billingDetails,
                            address: { ...billingDetails.address, line1: e.target.value }
                        })}
                        placeholder="Street address"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                        required
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            City <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={billingDetails.address.city}
                            onChange={(e) => setBillingDetails({
                                ...billingDetails,
                                address: { ...billingDetails.address, city: e.target.value }
                            })}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            State <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={billingDetails.address.state}
                            onChange={(e) => setBillingDetails({
                                ...billingDetails,
                                address: { ...billingDetails.address, state: e.target.value }
                            })}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                            required
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            ZIP Code <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={billingDetails.address.postal_code}
                            onChange={(e) => setBillingDetails({
                                ...billingDetails,
                                address: { ...billingDetails.address, postal_code: e.target.value }
                            })}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Country <span className="text-red-500">*</span>
                        </label>
                        <select
                            value={billingDetails.address.country}
                            onChange={(e) => setBillingDetails({
                                ...billingDetails,
                                address: { ...billingDetails.address, country: e.target.value }
                            })}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
                            required
                        >
                            <option value="US">United States</option>
                            <option value="CA">Canada</option>
                            <option value="GB">United Kingdom</option>
                            <option value="NG">Nigeria</option>
                            <option value="GH">Ghana</option>
                            <option value="KE">Kenya</option>
                            <option value="ZA">South Africa</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Card Information */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Card Information <span className="text-red-500">*</span>
                </label>
                <div className="border border-gray-300 rounded-lg p-3 focus-within:ring-2 focus-within:ring-orange-500 focus-within:border-orange-500">
                    <CardElement
                        options={CARD_ELEMENT_OPTIONS}
                        onChange={(e) => {
                            setCardComplete(e.complete);
                            if (e.error) {
                                setError(e.error.message);
                            } else {
                                setError('');
                            }
                        }}
                    />
                </div>
                <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
                    <i className="ri-lock-line"></i>
                    Your card details are encrypted and secure. We never store your full card number.
                </p>
            </div>

            {/* Security Badges */}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-start gap-3">
                    <i className="ri-shield-check-line text-green-600 text-xl flex-shrink-0 mt-0.5"></i>
                    <div>
                        <h4 className="font-medium text-gray-900 text-sm mb-1">Secure Payment Processing</h4>
                        <ul className="text-xs text-gray-600 space-y-1">
                            <li>• PCI DSS Level 1 compliant</li>
                            <li>• 256-bit SSL encryption</li>
                            <li>• Your card is saved securely for automatic billing</li>
                            <li>• {planType === 'monthly' ? 'Billed monthly' : 'Billed annually'} until you cancel</li>
                        </ul>
                    </div>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-red-600 text-sm flex items-start gap-2">
                        <i className="ri-error-warning-line flex-shrink-0 mt-0.5"></i>
                        {error}
                    </p>
                </div>
            )}

            {/* Order Summary */}
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Plan</span>
                    <span className="text-sm text-gray-900 capitalize">{planType}</span>
                </div>
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Billing Frequency</span>
                    <span className="text-sm text-gray-900">{planType === 'monthly' ? 'Every month' : 'Every year'}</span>
                </div>
                <div className="border-t border-orange-300 my-2"></div>
                <div className="flex items-center justify-between">
                    <span className="text-base font-semibold text-gray-900">Total Due Today</span>
                    <span className="text-xl font-bold text-orange-600">${amount.toFixed(2)}</span>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
                <button
                    onClick={onCancel}
                    className="flex-1 px-6 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                    disabled={processing}
                >
                    Cancel
                </button>
                <button
                    onClick={handleSubmit}
                    disabled={!stripe || processing || !cardComplete}
                    className="flex-1 px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    {processing ? (
                        <>
                            <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full"></div>
                            Processing...
                        </>
                    ) : (
                        <>
                            <i className="ri-lock-line"></i>
                            Pay ${amount.toFixed(2)}
                        </>
                    )}
                </button>
            </div>

            {/* Trust Indicators */}
            <div className="text-center">
                <div className="flex items-center justify-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                        <i className="ri-shield-check-line text-green-600"></i>
                        Secure
                    </span>
                    <span className="flex items-center gap-1">
                        <i className="ri-time-line text-blue-600"></i>
                        Cancel Anytime
                    </span>
                    <span className="flex items-center gap-1">
                        <i className="ri-customer-service-line text-purple-600"></i>
                        24/7 Support
                    </span>
                </div>
            </div>
        </div>
    );
}

// Main wrapper component
export default function StripeCheckoutWithSavedCard(props: CheckoutFormProps) {
    if (!stripePromise) {
        return (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
                Stripe configuration error. Please contact support.
            </div>
        );
    }

    return (
        <Elements stripe={stripePromise}>
            <CheckoutForm {...props} />
        </Elements>
    );
}