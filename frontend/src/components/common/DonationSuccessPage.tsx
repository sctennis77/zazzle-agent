import React, { useState, useEffect, useRef } from 'react';
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
  
  const paymentIntentId = searchParams.get('payment_intent');
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 30; // Increased from 15 to 30 attempts
  const [countdown, setCountdown] = useState(3);
  const countdownStartedRef = useRef(false);

  // Reset countdownStartedRef when donation changes
  useEffect(() => {
    countdownStartedRef.current = false;
    setCountdown(3); // Reset countdown to 3 seconds for each new donation
  }, [donation]);

  // Auto-redirect when donation is found
  useEffect(() => {
    if (donation && !countdownStartedRef.current) {
      countdownStartedRef.current = true;
      const interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(interval);
            navigate('/');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [donation, navigate]);

  useEffect(() => {
    if (!paymentIntentId) {
      setError('No payment intent ID provided');
      setLoading(false);
      return;
    }

    console.log('Starting donation polling for payment intent:', paymentIntentId);

    const pollForDonation = async () => {
      try {
        console.log(`Polling attempt ${attempts + 1}/${maxAttempts} for payment intent: ${paymentIntentId}`);
        const response = await fetch(`/api/donations/${paymentIntentId}`);
        
        if (response.ok) {
          const donationData = await response.json();
          console.log('Donation found:', donationData);
          setDonation(donationData);
          setLoading(false);
          return true; // Success
        } else if (response.status === 404) {
          console.log(`Donation not found yet (attempt ${attempts + 1}/${maxAttempts})`);
          return false; // Continue polling
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      } catch (err) {
        console.error('Error polling for donation:', err);
        return false; // Continue polling on error
      }
    };

    const pollInterval = setInterval(async () => {
      setAttempts(prev => prev + 1);
      
      if (attempts >= maxAttempts) {
        clearInterval(pollInterval);
        setError('Unable to find donation after multiple attempts. Please contact support if this persists.');
        setLoading(false);
        return;
      }

      const success = await pollForDonation();
      if (success) {
        clearInterval(pollInterval);
      }
    }, 1000);

    // Initial poll
    pollForDonation();

    return () => {
      clearInterval(pollInterval);
    };
  }, [paymentIntentId, attempts, maxAttempts, navigate]);

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 text-center animate-in">
          <div className="mb-6">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Oops!</h2>
            <p className="text-gray-600 mb-6">{error}</p>
          </div>
          
          <div className="space-y-3">
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
            >
              Try Again
            </button>
            <Link
              to="/"
              className="block w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
            >
              Return to Gallery
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 text-center animate-in">
          {/* Loading Animation */}
          <div className="mb-8">
            <div className="relative w-20 h-20 mx-auto mb-6">
              <div className="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
              <div className="absolute inset-2 bg-blue-100 rounded-full flex items-center justify-center">
                <div className="w-8 h-8 bg-blue-600 rounded-full animate-pulse"></div>
              </div>
            </div>
            
            {/* Progress Bar */}
            <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
              <div 
                className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${(attempts / maxAttempts) * 100}%` }}
              ></div>
            </div>
            
            <p className="text-sm text-gray-500 mb-2">
              Attempt {attempts}/{maxAttempts}
            </p>
          </div>

          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Processing Your Commission</h2>
            <p className="text-gray-600 mb-6">
              We're setting up your commission and will redirect you to the gallery shortly...
            </p>
            
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
              <span>Connecting to payment processor</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (donation) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 text-center animate-in">
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

          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Commission Successful!</h2>
            <p className="text-gray-600 mb-6">
              Thank you for your ${donation.amount_usd} commission! Your artwork is being created and will appear in the gallery shortly.
            </p>
            
            {donation.commission_message && (
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Your message:</span> {donation.commission_message}
                </p>
              </div>
            )}

            <div className="space-y-3">
              <Link
                to="/"
                className="block w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 transform hover:scale-105"
              >
                View Gallery
              </Link>
              <p className="text-xs text-gray-500">
                Redirecting automatically in {countdown} seconds...
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default DonationSuccessPage; 