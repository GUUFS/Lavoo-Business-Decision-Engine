// FlutterwaveCheckout.tsx
import { useState } from 'react';
import { useFlutterwave, closePaymentModal } from 'flutterwave-react-v3';

interface FlutterwaveCheckoutProps {
  amount: number;
  email: string;
  name: string;
  planType: string;
  userLocation?: string;
  onSuccess: (response: { transaction_id: string }) => void;
  onError: (error: string) => void;
}

export default function FlutterwaveCheckout({ 
  amount, 
  email, 
  name, 
  planType, 
   userLocation = 'US',
  onSuccess, 
  onError 
}: FlutterwaveCheckoutProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Flutterwave configuration
  const config = {
    public_key: import.meta.env.VITE_FLUTTERWAVE_PUBLIC_KEY || '',
    tx_ref: `TX-${Date.now()}-${Math.random().toString(36).substring(7)}`,
    amount: amount,
    currency: userLocation === 'NG' ? 'NGN' : 'USD', // Change to 'NGN' for Nigerian Naira
    payment_options: 'card,mobilemoney,ussd,banktransfer',
    customer: {
      email: email,
      phone_number: '0000000000', // Provide a default phone number
      name: name,
    },
    customizations: {
      title: 'AI Strategy Pro',
      description: `${planType} Subscription`,
      logo: '', // Add your logo URL here
    },
  };

  const handleFlutterPayment = useFlutterwave(config);

  const verifyPayment = async (transactionId: string): Promise<any> => {
    try {
      console.log('Verifying payment with transaction ID:', transactionId);
      
      const response = await fetch('http://localhost:8000/api/payments/flutterwave/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add authorization header if needed
          // 'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          transaction_id: String(transactionId),
        }),
      });

      const responseText = await response.text();
      console.log('Verification response:', responseText);

      if (!response.ok) {
        throw new Error(`Verification failed: ${responseText}`);
      }

      if (!responseText) {
        throw new Error('Empty response from server');
      }

      const data = JSON.parse(responseText);
      
      if (data.status === 'success') {
        console.log('Payment verified successfully:', data);
        return data;
      } else {
        throw new Error(data.message || 'Payment verification failed');
      }
    } catch (err) {
      console.error('Verification error:', err);
      throw err;
    }
  };

  const handlePayment = () => {
    if (!config.public_key) {
      setError('Flutterwave public key is not configured');
      onError('Payment system not configured');
      return;
    }

    console.log('Initiating Flutterwave payment with config:', {
      amount: config.amount,
      email: config.customer.email,
      planType: planType
    });

    setIsLoading(true);
    setError(null);

    handleFlutterPayment({
      callback: async (response: any) => {
        console.log('Flutterwave payment response:', response);
        
        try {
          if (response.status === 'successful') {
            console.log('Payment successful, verifying on backend...');
            // Verify payment on backend
            const verificationResult = await verifyPayment(response.transaction_id);
            
            if (verificationResult.status === 'success') {
              console.log('Payment verified successfully');
              onSuccess({ transaction_id: response.transaction_id });
            } else {
              console.error('Verification failed:', verificationResult);
              onError('Payment verification failed');
            }
          } else if (response.status === 'cancelled') {
            console.log('Payment was cancelled by user');
            onError('Payment was cancelled');
          } else {
            console.log('Payment failed with status:', response.status);
            onError('Payment was not successful');
          }
        } catch (err: any) {
          console.error('Payment error:', err);
          onError(err.message || 'Payment processing failed');
        } finally {
          setIsLoading(false);
          closePaymentModal();
        }
      },
      onClose: () => {
        console.log('Payment modal closed');
        setIsLoading(false);
      },
    });
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
        <p className="text-red-600 text-sm mb-2">{error}</p>
        <button
          onClick={() => {
            setError(null);
          }}
          className="text-red-600 text-sm underline hover:text-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="w-full">
      <button
        onClick={handlePayment}
        disabled={isLoading}
        className={`w-full py-3 px-6 ${
          isLoading 
            ? 'bg-gray-400 cursor-not-allowed' 
            : 'bg-orange-500 hover:bg-orange-600'
        } text-white font-semibold rounded-lg transition-colors duration-200 flex items-center justify-center`}
      >
        {isLoading ? (
          <>
            <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></div>
            Processing...
          </>
        ) : (
          <>
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
            </svg>
            Pay ${amount} with Flutterwave
          </>
        )}
      </button>
      
      {/* Information text */}
      <p className="text-xs text-gray-500 text-center mt-2">
        Secure payment powered by Flutterwave
      </p>
    </div>
  );
}