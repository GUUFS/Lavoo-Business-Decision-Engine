
import { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';

const STRIPE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;
const stripePromise = STRIPE_KEY ? loadStripe(STRIPE_KEY) : null;

function CheckoutForm({ userId, onSuccess, onError }: {
  userId: number;
  onSuccess: (response: { paymentIntentId: string }) => void;
  onError: (error: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setIsProcessing(true);
    setMessage('');

    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: window.location.href, // optional, only needed for redirects
      },
      redirect: 'if_required',
    });

    if (error) {
      setMessage(error.message || 'Payment failed');
      onError(error.message || 'Payment failed');
      setIsProcessing(false);
      return;
    }

    if (paymentIntent?.status === 'succeeded') {
      const token = document.cookie
        .split("; ")
        .find((r) => r.startsWith("access_token="))
        ?.split("=")[1];

      const response = await fetch('/api/stripe/verify-payment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          payment_intent_id: paymentIntent.id,
          user_id: userId,
        }),
      });

      if (response.ok) {
        onSuccess({ paymentIntentId: paymentIntent.id });
      } else {
        const data = await response.json();
        onError(data.detail || 'Verification failed');
      }
    }

    setIsProcessing(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      {message && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
          {message}
        </div>
      )}
      <button
        type="submit"
        disabled={!stripe || isProcessing}
        className={`w-full py-3 px-4 rounded-lg font-semibold transition-all ${!stripe || isProcessing
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-purple-600 hover:bg-purple-700 text-white'
          }`}
      >
        {isProcessing ? 'Processing...' : 'Pay Now'}
      </button>
    </form>
  );
}

export default function StripeCheckout({
  amount,
  email,
  name,
  planType,
  userId,
  onSuccess,
  onError,
}: {
  amount: number;
  email: string;
  name: string;
  planType: string;
  userId: number;
  onSuccess: (response: { paymentIntentId: string }) => void;
  onError: (error: string) => void;
}) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    return () => {
      // This runs on unmount — helps React 18 Strict Mode not double-fetch
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    const createPaymentIntent = async () => {
      setIsLoading(true); // Reset loading state when checking for new intent

      if (!STRIPE_KEY) {
        if (mounted) {
          setError('Stripe key missing');
          onError('Stripe configuration error');
          setIsLoading(false);
        }
        return;
      }

      const token = document.cookie
        .split("; ")
        .find((row) => row.startsWith("access_token="))
        ?.split("=")[1];

      if (!token) {
        if (mounted) {
          setError('Please log in again');
          onError('Authentication required');
          setIsLoading(false);
        }
        return;
      }

      try {
        const response = await fetch('/api/stripe/create-payment-intent', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            amount,
            plan_type: planType,
            email,
            name,
            user_id: userId,
          }),
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || 'Failed to create payment intent');
        }

        const data = await response.json();

        if (mounted) {
          setClientSecret(data.clientSecret);
          setIsLoading(false);
        }
      } catch (err: any) {
        if (mounted) {
          console.error('Payment intent error:', err);
          setError(err.message || 'Payment setup failed');
          onError(err.message || 'Payment setup failed');
          setIsLoading(false);
        }
      }
    };

    createPaymentIntent();

    return () => {
      mounted = false;
    };
  }, [amount, planType, email, name, userId]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600">
        {error}
      </div>
    );
  }

  if (isLoading || !clientSecret) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full mx-auto mb-3"></div>
        <p>Loading payment...</p>
      </div>
    );
  }

  const appearance = {
    theme: 'stripe',
    variables: {
      colorPrimary: '#9333ea',
      colorBackground: '#ffffff',
      colorText: '#1f2937',
      colorDanger: '#ef4444',
      borderRadius: '8px',
    },
  } as const;

  const options = {
    clientSecret,
    appearance,
  };

  return (
    <Elements stripe={stripePromise} options={options}>
      <CheckoutForm userId={userId} onSuccess={onSuccess} onError={onError} />
    </Elements>
  );
}