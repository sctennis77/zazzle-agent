import React, { useState, useEffect, useRef } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, ExpressCheckoutElement, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from './Modal';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { FaCrown, FaStar, FaGem, FaHeart } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

interface DonationModalProps {
  isOpen: boolean;
  onClose: () => void;
  subreddit: string;
  postId?: string;
  supportOnly?: boolean;
}

interface DonationRequest {
  amount_usd: string;
  subreddit: string;
  donation_type: 'support';
  post_id?: string;
  message?: string;
  customer_email?: string;
  customer_name?: string;
  reddit_username?: string;
  is_anonymous: boolean;
}

// Component that uses the Express Checkout Element and Payment Element
const DonationForm: React.FC<{
  amount: string;
  message: string;
  customerEmail: string;
  customerName: string;
  redditUsername: string;
  isAnonymous: boolean;
  subreddit: string;
  postId?: string;
  onSuccess: () => void;
  onError: (error: string) => void;
}> = ({ 
  amount, 
  message, 
  customerEmail, 
  customerName, 
  redditUsername, 
  isAnonymous, 
  subreddit, 
  postId, 
  onSuccess, 
  onError
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleConfirm = async () => {
    if (!stripe || !elements) {
      onError('Payment not ready');
      return;
    }

    setIsProcessing(true);

    try {
      // Confirm the payment with the Express Checkout Element
      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        // Remove return_url to handle success directly in frontend
        redirect: 'if_required', // Only redirect if required (like 3D Secure)
      });

      if (error) {
        onError(error.message || 'Payment failed');
      } else if (paymentIntent && paymentIntent.status === 'succeeded') {
        // Payment succeeded, call onSuccess directly
        onSuccess();
      } else {
        // Payment is processing or requires additional action
        onError('Payment is being processed. Please check your email for confirmation.');
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Express Checkout Element for click-to-pay methods */}
      <ExpressCheckoutElement
        options={{
          buttonType: {
            applePay: 'donate',
            googlePay: 'donate',
            paypal: 'pay',
          },
          buttonHeight: 48,
          buttonTheme: {
            applePay: 'black',
            googlePay: 'black',
            paypal: 'gold',
          },
          layout: {
            maxColumns: 2,
            maxRows: 3,
            overflow: 'auto',
          },
          paymentMethodOrder: ['link', 'applePay', 'googlePay', 'paypal'],
          paymentMethods: {
            applePay: 'auto',
            googlePay: 'auto',
            link: 'auto',
            paypal: 'auto',
          },
        }}
        onConfirm={handleConfirm}
      />
      
      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-300" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-white px-2 text-gray-500">Or pay with card</span>
        </div>
      </div>
      
      {/* Payment Element for card payments */}
      <PaymentElement 
        options={{
          layout: 'tabs',
          defaultValues: {
            billingDetails: {
              name: customerName || '',
              email: customerEmail || '',
            },
          },
        }}
      />

      {/* Always-visible Pay button for card payments */}
      <button
        className="w-full mt-2 py-2 px-4 bg-pink-600 text-white rounded disabled:opacity-50"
        onClick={handleConfirm}
        disabled={!stripe || !elements || isProcessing}
        type="button"
      >
        {isProcessing ? "Processing..." : "Pay"}
      </button>
      
      {isProcessing && (
        <div className="text-center text-sm text-gray-600">
          Processing payment...
        </div>
      )}
    </div>
  );
};

const iconMap = {
  FaCrown,
  FaStar,
  FaGem,
  FaHeart,
};

const DonationModal: React.FC<DonationModalProps> = ({ 
  isOpen, 
  onClose, 
  subreddit, 
  postId, 
  supportOnly = false
}) => {
  const [amount, setAmount] = useState('5');
  const [customAmount, setCustomAmount] = useState('');
  const [message, setMessage] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [previousRedditUsername, setPreviousRedditUsername] = useState('');
  const [showMessage, setShowMessage] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const navigate = useNavigate();
  const [countdown, setCountdown] = React.useState(3);

  // Use dynamic tiers from API
  const { tiers, getTierDisplay } = useDonationTiers();

  // Default to the lowest tier min amount
  useEffect(() => {
    if (isOpen && tiers.length > 0) {
      setAmount(tiers[0].min_amount.toString());
      setCustomAmount('');
    }
  }, [isOpen, tiers]);





  useEffect(() => {
    if (isOpen) {
      // Don't reset amount here - let the tiers useEffect handle it
      setCustomAmount('');
      setMessage('');
      setCustomerEmail('');
      setCustomerName('');
      setRedditUsername('');
      setPreviousRedditUsername('');
      setIsAnonymous(false); // Default to not anonymous, like commission form
      setError('');
      setSuccess(false);
      setShowMessage(false);
      // Don't reset clientSecret and paymentIntentId here - let createPaymentIntent handle it
    } else {
      // Only reset when closing
      setClientSecret(null);
      setPaymentIntentId(null);
    }
  }, [isOpen]);

  // Create payment intent after amount is set by tiers useEffect
  useEffect(() => {
    if (isOpen && amount && tiers.length > 0) {
      // Small delay to ensure state is properly set
      const timeoutId = setTimeout(async () => {
        await createPaymentIntent();
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [isOpen, amount, tiers]);

  // Debounced update effect - improved: only update if email is valid, and debounce is 1s
  useEffect(() => {
    if (!paymentIntentId || !isOpen) return;

    // Email validation regex
    const isEmailValid = !customerEmail || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(customerEmail);

    // Only update if email is valid
    if (!isEmailValid) return;

    const timeoutId = setTimeout(() => {
      updatePaymentIntent();
    }, 1000); // 1s debounce

    return () => clearTimeout(timeoutId);
  }, [paymentIntentId, amount, customerName, customerEmail, redditUsername, isAnonymous, message, subreddit, postId, isOpen]);

  const createPaymentIntent = async () => {
    if (!amount || parseFloat(amount) < 0.50) {
      setError('Amount must be at least $0.50');
      return null;
    }

    setError(''); // Clear any previous errors

    try {
      const donationRequest: DonationRequest = {
        amount_usd: amount,
        subreddit,
        donation_type: 'support',
        post_id: postId,
        message: message || undefined,
        customer_email: customerEmail || undefined,
        customer_name: customerName || undefined,
        reddit_username: redditUsername.trim() || undefined,
        is_anonymous: isAnonymous,
      };

      const response = await fetch('/api/donations/create-payment-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(donationRequest),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create payment intent');
      }

      const { client_secret, payment_intent_id } = await response.json();
      setClientSecret(client_secret);
      setPaymentIntentId(payment_intent_id);
      setError(''); // Clear any previous errors
      return payment_intent_id;
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to create payment intent');
      setClientSecret(null);
      setPaymentIntentId(null);
      return null;
    }
  };

  const updatePaymentIntent = async () => {
    if (!paymentIntentId || !amount || parseFloat(amount) < 0.50) {
      return null;
    }

    setError(''); // Clear any previous errors

    try {
      const donationRequest: DonationRequest = {
        amount_usd: amount,
        subreddit,
        donation_type: 'support',
        post_id: postId,
        message: message || undefined,
        customer_email: customerEmail || undefined,
        customer_name: customerName || undefined,
        reddit_username: redditUsername.trim() || undefined,
        is_anonymous: isAnonymous,
      };

      const response = await fetch(`/api/donations/payment-intent/${paymentIntentId}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(donationRequest),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update payment intent');
      }

      const { client_secret } = await response.json();
      setClientSecret(client_secret);
      setError(''); // Clear any previous errors
      return client_secret;
    } catch (error) {
      // Silently handle update errors to avoid disrupting user experience
      console.error('Failed to update payment intent:', error);
      return null;
    }
  };

  const handleSuccess = () => {
    setSuccess(true);
    // Poll for payment completion
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/donations/payment-intent/${paymentIntentId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.status === 'succeeded') {
            // Payment completed, no need to poll anymore
            clearInterval(pollInterval);
          }
        }
      } catch (error) {
        console.error('Error fetching payment intent state:', error);
      }
    }, 2000);

    // Stop polling after 30 seconds
    setTimeout(() => {
      clearInterval(pollInterval);
    }, 30000);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  // Find the current tier based on amount
  const currentTier = tiers
    .slice()
    .reverse()
    .find(t => parseFloat(amount) >= t.min_amount) || tiers[0];
  const tierDisplay = getTierDisplay(currentTier?.name || 'bronze');
  const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;

  // Validate minimum
  const minAmount = currentTier?.min_amount || 1;
  const isBelowMin = parseFloat(amount) < minAmount;

  // Countdown/redirect effect for support donations only
  React.useEffect(() => {
    if (success && supportOnly) {
      if (countdown <= 0) {
        navigate(`/?product=${postId}`);
        return;
      }
      const timer = setTimeout(() => {
        setCountdown((c) => c - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [success, supportOnly, countdown, navigate, postId]);

  if (success) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} title="Thank you!">
        <div className="flex flex-col items-center justify-center p-6">
          <div className="text-green-600 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="text-lg text-green-600 font-semibold mb-2">Thank you for your support!</p>
          <p className="text-gray-600 text-center mb-4">Your donation helps keep this project running. You’ll see your support listed on the product card.</p>
          {supportOnly && (
            <div className="flex flex-col items-center gap-2 w-full">
              <p className="text-sm text-gray-500">Redirecting in {countdown} seconds...</p>
              <div className="flex gap-3 mt-2">
                <button
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 font-semibold"
                  onClick={() => navigate(`/?product=${postId}`)}
                >
                  Continue
                </button>
                <button
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 font-semibold"
                  onClick={onClose}
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={supportOnly ? 'Support This Post' : 'Make a Donation'}>
      <div className="space-y-6 p-6">
        {/* Tier selection and badge */}
        <div className="flex items-center gap-3 mb-2">
          <div className={`p-2 rounded-full ${tierDisplay.bgColor} border ${tierDisplay.borderColor}`}>
            <IconComponent size={20} className={tierDisplay.color} />
          </div>
          <div>
            <div className="font-semibold text-gray-900 text-base">{currentTier?.display_name || 'Bronze'} Tier</div>
            <div className="text-xs text-gray-500">Minimum: ${minAmount.toFixed(2)}</div>
          </div>
        </div>
        {/* Preset Amount Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Choose Amount</label>
          <div className="grid grid-cols-3 gap-2 mb-2">
            {tiers.map((tier) => {
              const tDisplay = getTierDisplay(tier.name);
              const TIcon = iconMap[tDisplay.icon as keyof typeof iconMap] || FaHeart;
              return (
                <button
                  key={tier.name}
                  type="button"
                  onClick={async () => {
                    const newAmount = tier.min_amount.toString();
                    setAmount(newAmount);
                    setCustomAmount('');
                    
                    // If we have a payment intent, update it with the new amount
                    if (paymentIntentId) {
                      // Pass the new amount directly to avoid state closure issues
                      setTimeout(() => updatePaymentIntent(), 50);
                    }
                  }}
                  className={`flex items-center gap-1 px-2 py-1 border rounded-lg text-xs font-medium transition-colors h-9 ${amount === tier.min_amount.toString() ? tDisplay.bgColor + ' ' + tDisplay.color + ' border-pink-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
                >
                  <TIcon size={14} className={tDisplay.color} />
                  {tier.display_name}
                  <span className="ml-1 text-gray-400">${tier.min_amount}</span>
                </button>
              );
            })}
            {/* Custom Amount as last grid cell */}
            <div className="relative flex items-center h-9">
              <span className="absolute left-2 text-gray-500 text-xs">$</span>
              <input
                type="number"
                min={tiers[0]?.min_amount || 1}
                step="0.01"
                value={customAmount}
                onChange={e => {
                  const newAmount = e.target.value;
                  setCustomAmount(newAmount);
                  setAmount(newAmount);
                  
                  // If we have a payment intent, update it with the new amount
                  if (paymentIntentId) {
                    // Pass the new amount directly to avoid state closure issues
                    setTimeout(() => updatePaymentIntent(), 50);
                  }
                }}
                className="w-full border border-gray-300 rounded-lg pl-5 pr-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent h-9"
                placeholder="Custom"
              />
            </div>
          </div>
          {isBelowMin && (
            <div className="text-xs text-red-500 mt-1">Minimum for {currentTier?.display_name} is ${minAmount.toFixed(2)}</div>
          )}
        </div>

        {/* Customer Information - Email and Name */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
            <input
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500"
              placeholder="your@email.com"
              pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
              title="Please enter a valid email address"
            />
            {customerEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(customerEmail) && (
              <p className="text-xs text-red-500 mt-1">Please enter a valid email address</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name (optional)</label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500"
              placeholder="Your Name"
            />
            <p className="text-xs text-gray-500 mt-1">
              Required for card payments, optional for Apple Pay/Google Pay/PayPal
            </p>
          </div>
        </div>

        {/* Customer Information - Only for Reddit Username */}
        <div className="space-y-4">
          {/* Reddit Username and Anonymous Toggle */}
          <div className="flex items-center gap-3 mb-2">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reddit Username
                {!isAnonymous && <span className="text-red-500 ml-1">*</span>}
              </label>
              <input
                type="text"
                value={redditUsername}
                onChange={(e) => {
                  setRedditUsername(e.target.value);
                  // Update payment intent when username changes
                  if (paymentIntentId && !isAnonymous) {
                    setTimeout(() => updatePaymentIntent(), 100);
                  }
                }}
                disabled={isAnonymous}
                className={`w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500 ${isAnonymous ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`}
                placeholder={isAnonymous ? "Anonymous donation" : "u/username"}
              />
              {!isAnonymous && !redditUsername.trim() && (
                <p className="text-red-500 text-xs mt-1">Reddit username is required when not anonymous</p>
              )}
            </div>
            <div className="flex flex-col items-center justify-end h-full">
              <label className="text-xs text-gray-600 mb-1">Anonymous</label>
              <button
                type="button"
                onClick={() => {
                  const newAnonymousState = !isAnonymous;
                  setIsAnonymous(newAnonymousState);
                  
                  // Handle reddit username when toggling anonymous
                  if (newAnonymousState) {
                    // Switching to anonymous - save current username and clear it
                    setPreviousRedditUsername(redditUsername);
                    setRedditUsername('');
                  } else {
                    // Switching from anonymous - restore previous username if any
                    setRedditUsername(previousRedditUsername);
                  }
                  
                  // Immediately update payment intent when toggling anonymous
                  if (paymentIntentId) {
                    setTimeout(() => updatePaymentIntent(), 100);
                  }
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${isAnonymous ? 'bg-pink-500' : 'bg-gray-300'}`}
                aria-pressed={isAnonymous}
                aria-label="Toggle anonymous donation"
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${isAnonymous ? 'translate-x-5' : 'translate-x-1'}`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Message */}
        <div>
          {!showMessage && (
            <button
              type="button"
              className="text-xs text-pink-500 underline mb-2"
              onClick={() => setShowMessage(true)}
            >
              + Add a support message
            </button>
          )}
          {showMessage && (
            <>
              <button
                type="button"
                className="text-xs text-pink-500 underline mb-2"
                onClick={() => setShowMessage(false)}
              >
                – Hide support message
              </button>
              <label className="block text-sm font-medium text-gray-700 mb-2 mt-2">Support Message</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-pink-500"
                rows={3}
                placeholder="Leave a message of support..."
              />
              <p className="text-xs text-gray-500 mt-1">
                This message will be displayed alongside your donation for recognition purposes.
              </p>
            </>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
            {error}
          </div>
        )}

        {/* Payment Options */}
        <div className="border-t pt-6 min-h-[340px] relative">
          {!clientSecret ? (
            <div className="animate-pulse flex flex-col gap-4 items-center justify-center min-h-[300px]">
              <div className="bg-gray-200 rounded-lg h-12 w-3/4 mb-2" />
              <div className="bg-gray-200 rounded-lg h-12 w-3/4 mb-2" />
              <div className="bg-gray-200 rounded-lg h-10 w-1/2 mb-2" />
              <div className="bg-gray-200 rounded-lg h-12 w-full" />
            </div>
          ) : (
            <div className="transition-opacity duration-500 opacity-100" style={{ opacity: clientSecret ? 1 : 0 }}>
              <Elements 
                stripe={stripePromise}
                options={{
                  clientSecret: clientSecret,
                  appearance: {
                    theme: 'stripe',
                    variables: {
                      colorPrimary: '#ec4899', // pink-600 for donation
                      borderRadius: '8px',
                    },
                  },
                  loader: 'auto',
                }}
                key={`${clientSecret}-${paymentIntentId}`}
              >
                        <DonationForm
          amount={amount}
          message={message}
          customerEmail={customerEmail}
          customerName={customerName}
          redditUsername={redditUsername}
          isAnonymous={isAnonymous}
          subreddit={subreddit}
          postId={postId}
          onSuccess={handleSuccess}
          onError={handleError}
        />
              </Elements>
            </div>
          )}
        </div>

        {/* Cancel Button */}
        <div className="flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default DonationModal; 