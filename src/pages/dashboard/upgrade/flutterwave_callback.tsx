
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function PaymentCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('verifying');

  useEffect(() => {
    const verifyPayment = async () => {
      const transactionId = searchParams.get('transaction_id');
      const txRef = searchParams.get('tx_ref');
      const status = searchParams.get('status');

      if (status === 'successful' && transactionId) {
        try {
          const response = await fetch('/api/payments/flutterwave/verify', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({ transaction_id: transactionId }),
          });

          const data = await response.json();

          if (data.status === 'success') {
            setStatus('success');
            setTimeout(() => navigate('/dashboard'), 2000);
          } else {
            setStatus('failed');
          }
        } catch (error) {
          console.error('Verification error:', error);
          setStatus('failed');
        }
      } else {
        setStatus('cancelled');
      }
    };

    verifyPayment();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        {status === 'verifying' && (
          <>
            <div className="animate-spin w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-lg text-gray-600">Verifying your payment...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="ri-check-line text-green-600 text-3xl"></i>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h2>
            <p className="text-gray-600">Redirecting to dashboard...</p>
          </>
        )}
        {(status === 'failed' || status === 'cancelled') && (
          <>
            <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i className="ri-close-line text-red-600 text-3xl"></i>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment {status === 'failed' ? 'Failed' : 'Cancelled'}</h2>
            <button
              onClick={() => navigate('/upgrade')}
              className="mt-4 px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700"
            >
              Try Again
            </button>
          </>
        )}
      </div>
    </div>
  );
}