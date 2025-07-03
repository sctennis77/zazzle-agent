import React, { useEffect, useState } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';

interface Donation {
  id: number;
  amount_usd: number;
  customer_name?: string;
  customer_email?: string;
  message?: string;
  subreddit?: string;
  reddit_username?: string;
  is_anonymous?: boolean;
  status: string;
  tier?: string;
  donation_type?: string;
  commission_type?: string;
  post_id?: string;
  commission_message?: string;
  created_at?: string;
}

const DonationSuccessPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [donation, setDonation] = useState<Donation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const [showSuccess, setShowSuccess] = useState(false);
  const [redirectTimeout, setRedirectTimeout] = useState<number | null>(null);
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const paymentIntentId = searchParams.get('payment_intent_id');
    if (!paymentIntentId) {
      setError('Missing payment_intent_id in URL.');
      setLoading(false);
      return;
    }

    console.log('Starting donation polling for payment intent:', paymentIntentId);

    let currentAttempts = 0;
    const maxAttempts = 15;
    const delayMs = 1000;
    let cancelled = false;

    const fetchWithRetry = async () => {
      while (currentAttempts < maxAttempts && !cancelled) {
        try {
          console.log(`Polling attempt ${currentAttempts + 1}/${maxAttempts} for payment intent: ${paymentIntentId}`);
          const res = await fetch(`/api/donations/${paymentIntentId}`);
          
          if (res.ok) {
            const data = await res.json();
            console.log('Donation found:', data);
            setDonation(data);
            setLoading(false);
            setShowSuccess(true);
            // Auto-redirect after 5 seconds
            const timeout = window.setTimeout(() => {
              navigate('/');
            }, 5000);
            setRedirectTimeout(timeout);
            return;
          } else if (res.status === 404) {
            // Not ready yet, keep polling
            console.log(`Donation not found yet (attempt ${currentAttempts + 1}), waiting ${delayMs}ms...`);
            await new Promise((resolve) => setTimeout(resolve, delayMs));
            currentAttempts++;
            setAttempts(currentAttempts);
          } else {
            console.error('Unexpected response status:', res.status);
            setError('Failed to fetch donation info.');
            setLoading(false);
            return;
          }
        } catch (err) {
          console.error('Error fetching donation:', err);
          setError('Error fetching donation info.');
          setLoading(false);
          return;
        }
      }
      console.log(`Polling completed after ${currentAttempts} attempts. Donation not found.`);
      setError('Donation not found after payment. Please contact support.');
      setLoading(false);
    };

    fetchWithRetry();
    return () => {
      console.log('Cleaning up donation polling');
      cancelled = true;
      if (redirectTimeout) clearTimeout(redirectTimeout);
    };
    // eslint-disable-next-line
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-indigo-50 flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          {/* Animated loading spinner */}
          <div className="mb-6">
            <div className="relative w-16 h-16 mx-auto">
              <div className="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
              <div className="absolute inset-2 bg-white rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
              </div>
            </div>
          </div>
          
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Processing Your Donation</h2>
          <p className="text-gray-600 mb-6">
            We're confirming your payment and setting up your commission...
          </p>
          
          {attempts > 0 && (
            <div className="bg-blue-50 rounded-lg p-4 mb-4">
              <div className="text-sm text-blue-700">
                <div className="flex items-center justify-between mb-2">
                  <span>Processing payment...</span>
                  <span className="font-mono">{attempts}/15</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(attempts / 15) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
          )}
          
          <div className="text-xs text-gray-500">
            This usually takes just a few seconds
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-50 flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="mb-6">
            <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Something went wrong</h2>
          <p className="text-red-600 mb-6">{error}</p>
          <button 
            onClick={() => navigate('/')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Return to Gallery
          </button>
        </div>
      </div>
    );
  }

  if (!donation) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex items-center justify-center p-8">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="mb-6">
            <div className="w-16 h-16 mx-auto bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Donation Not Found</h2>
          <p className="text-gray-600 mb-6">We couldn't locate your donation information.</p>
          <button 
            onClick={() => navigate('/')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Return to Gallery
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-purple-50 flex items-center justify-center p-8">
      <div className="max-w-lg w-full bg-white rounded-2xl shadow-2xl p-8 text-center transform transition-all duration-500 animate-in slide-in-from-bottom-4">
        {/* Success Animation */}
        <div className="mb-8">
          <div className="relative w-20 h-20 mx-auto">
            <div className="absolute inset-0 bg-green-100 rounded-full animate-ping opacity-75"></div>
            <div className="absolute inset-2 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-10 h-10 text-white checkmark-animate" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </div>

        <h1 className="text-3xl font-bold text-gray-800 mb-2">Thank You!</h1>
        <p className="text-lg text-gray-600 mb-8">Your donation has been processed successfully</p>

        {/* Donation Details */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 mb-8">
          <div className="grid grid-cols-2 gap-4 text-left">
            <div>
              <div className="text-sm font-medium text-gray-500">Amount</div>
              <div className="text-xl font-bold text-gray-800">${donation.amount_usd}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Tier</div>
              <div className="text-xl font-bold text-gray-800 capitalize">{donation.tier}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Type</div>
              <div className="text-lg font-semibold text-gray-800 capitalize">{donation.commission_type}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Subreddit</div>
              <div className="text-lg font-semibold text-gray-800">r/{donation.subreddit}</div>
            </div>
          </div>
          
          {donation.commission_message && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="text-sm font-medium text-gray-500 mb-2">Your Message</div>
              <div className="text-gray-700 italic">"{donation.commission_message}"</div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="space-y-4">
          <button 
            onClick={() => navigate('/')}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all duration-300 transform hover:scale-105 shadow-lg"
          >
            View Gallery
          </button>
          
          <div className="text-sm text-gray-500">
            Redirecting automatically in 5 seconds...
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute top-4 right-4 w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
        <div className="absolute bottom-4 left-4 w-3 h-3 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.5s' }}></div>
      </div>
    </div>
  );
};

export default DonationSuccessPage; 