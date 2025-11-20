
import { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import type { Stripe, StripeElements } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';

interface StripeCheckoutProps {
  amount: number;
  email: string;
  name: string;
  planType: string;
  userId: number;
  onSuccess: (response: { paymentIntentId: string }) => void;
  onError: (error: string) => void;
}

// Payment form component
function CheckoutForm({ userId, onSuccess, onError 
}: { 
  userId: number;
  onSuccess: (response: { paymentIntentId: string }) => void;
  onError: (error: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsProcessing(true);
    setMessage('');

    try {
      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        redirect: 'if_required',
      });

      if (error) {
        setMessage(error.message || 'Payment failed');
        onError(error.message || 'Payment failed');
        setIsProcessing(false);
        return;
      }

      if (paymentIntent && paymentIntent.status === 'succeeded') {
        // Verify payment with backend
        const response = await fetch('/api/stripe/verify-payment', {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            payment_intent_id: paymentIntent.id,
            user_id: userId
          }),
        });

        if (response.ok) {
          onSuccess({ paymentIntentId: paymentIntent.id });
        } else {
          const data = await response.json();
          onError(data.detail || 'Payment verification failed');
        }
      }
    } catch (err: any) {
      setMessage(err.message || 'An error occurred');
      onError(err.message || 'An error occurred');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      
      {message && (
        <div className="text-red-600 text-sm">{message}</div>
      )}
      
      <button
        disabled={!stripe || isProcessing}
        className={`w-full py-3 px-4 rounded-lg font-semibold transition-all ${
          !stripe || isProcessing
            ? 'bg-gray-300 cursor-not-allowed'
            : 'bg-purple-600 hover:bg-purple-700 text-white shadow-md'
        }`}
      >
        {isProcessing ? (
          <div className="flex items-center justify-center gap-2">
            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
            Processing...
          </div>
        ) : (
          'Pay Now'
        )}
      </button>
      
      <div className="text-xs text-gray-500 text-center">
        Your payment is secured by Stripe
      </div>
    </form>
  );
}

// Main Stripe Checkout component
export default function StripeCheckout({ amount, email, name, planType, userId, onSuccess, onError
}: StripeCheckoutProps) {
  const [stripePromise, setStripePromise] = useState<Promise<Stripe | null> | null>(null);
  const [clientSecret, setClientSecret] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Fetch Stripe publishable key
    fetch('/api/stripe/config')
      .then(res => res.json())
      .then(data => {
        setStripePromise(loadStripe(data.publishableKey));
      })
      .catch(err => {
        console.error('Error loading Stripe config:', err);
        onError('Failed to load payment configuration');
      });
  }, []);

  useEffect(() => {
    // Create payment intent
    fetch('/api/stripe/create-payment-intent', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        amount,
        plan_type: planType,
        email,
        name,
        user_id: userId
      }),
    })
      .then(res => res.json())
      .then(data => {
        setClientSecret(data.clientSecret);
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Error creating payment intent:', err);
        onError('Failed to initialize payment');
        setIsLoading(false);
      });
  }, [amount, email, name, planType, userId]);

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full mx-auto mb-3"></div>
        <p className="text-gray-600">Initializing secure payment...</p>
      </div>
    );
  }

  if (!clientSecret || !stripePromise) {
    return (
      <div className="text-center py-8 text-red-600">
        Failed to initialize payment. Please try again.
      </div>
    );
  }

  const appearance = {
    theme: 'stripe' as const,
    variables: {
      colorPrimary: '#9333ea',
      colorBackground: '#ffffff',
      colorText: '#1f2937',
      colorDanger: '#ef4444',
      fontFamily: 'system-ui, sans-serif',
      spacingUnit: '4px',
      borderRadius: '8px',
    },
  };

  return (
    <div>
      <Elements stripe={stripePromise} options={{ clientSecret, appearance }}>
        <CheckoutForm 
          userId={userId} 
          onSuccess={onSuccess} 
          onError={onError} 
        />
      </Elements>
    </div>
  );
}