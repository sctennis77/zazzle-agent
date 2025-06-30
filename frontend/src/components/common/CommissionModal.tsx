import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, ExpressCheckoutElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from './Modal';

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_key_here');

interface CommissionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommissionRequest {
  amount_usd: string;
  subreddit: string;
  donation_type: 'commission';
  post_id?: string;
  commission_message?: string;
  customer_email?: string;
  customer_name?: string;
  reddit_username?: string;
  is_anonymous: boolean;
}

// Available subreddits for commission
const AVAILABLE_SUBREDDITS = [
  // Nature & Outdoors
  "nature", "earthporn", "landscapephotography", "hiking", "camping", "gardening", "plants", "succulents",
  // Space & Science
  "space", "astrophotography", "nasa", "science", "physics", "chemistry", "biology",
  // Sports & Recreation
  "golf", "soccer", "basketball", "tennis", "baseball", "hockey", "fishing", "surfing", "skiing", "rockclimbing",
  // Animals & Pets
  "aww", "cats", "dogs", "puppies", "kittens", "wildlife", "birding", "aquariums",
  // Food & Cooking
  "food", "foodporn", "cooking", "baking", "coffee", "tea", "wine",
  // Art & Design
  "art", "design", "architecture", "interiordesign", "streetart", "digitalart",
  // Technology & Gaming
  "programming", "gaming", "pcgaming", "retrogaming", "cyberpunk", "futurology",
  // Travel & Culture
  "travel", "backpacking", "photography", "cityporn", "history",
  // Lifestyle & Wellness
  "fitness", "yoga", "meditation", "minimalism", "sustainability", "vegan"
];

// Component that uses the Express Checkout Element
const CommissionForm: React.FC<{
  amount: string;
  commissionMessage: string;
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
  commissionMessage, 
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
      const { error } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/commission/success`,
        },
      });

      if (error) {
        onError(error.message || 'Payment failed');
      } else {
        onSuccess();
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
      <PaymentElement />

      {/* Always-visible Pay button for card payments */}
      <button
        className="w-full mt-2 py-2 px-4 bg-purple-600 text-white rounded disabled:opacity-50"
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

const CommissionModal: React.FC<CommissionModalProps> = ({ isOpen, onClose }) => {
  const [amount, setAmount] = useState('25');
  const [commissionMessage, setCommissionMessage] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [previousRedditUsername, setPreviousRedditUsername] = useState('');
  const [subreddit, setSubreddit] = useState('golf');
  const [postId, setPostId] = useState('');
  const [commissionType, setCommissionType] = useState<'random' | 'specific'>('random');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [customAmount, setCustomAmount] = useState('');
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [showMessage, setShowMessage] = useState(false);
  const presetAmounts = [10, 25, 50, 100, 250];

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setAmount('25');
      setCustomAmount('');
      setCommissionMessage('');
      setCustomerEmail('');
      setCustomerName('');
      setRedditUsername('');
      setPreviousRedditUsername('');
      setIsAnonymous(false);
      setSubreddit('golf');
      setPostId('');
      setCommissionType('random');
      setError('');
      setSuccess(false);
      setClientSecret(null);
      setShowMessage(false);
    }
  }, [isOpen]);

  // Create payment intent when form data changes
  useEffect(() => {
    const createPaymentIntent = async () => {
      if (!isOpen || !amount || !subreddit) return;

      // For specific post commissions, post_id is required
      if (commissionType === 'specific' && !postId) {
        setError('Post ID or URL is required for specific post commissions');
        setClientSecret(null);
        return;
      }

      try {
        const commissionRequest: CommissionRequest = {
          amount_usd: amount,
          subreddit,
          donation_type: 'commission',
          post_id: commissionType === 'specific' ? postId : undefined,
          commission_message: commissionMessage,
          customer_email: customerEmail || undefined,
          customer_name: customerName || undefined,
          reddit_username: redditUsername.trim() || undefined,
          is_anonymous: isAnonymous,
        };

        const response = await fetch('/api/donations/create-payment-intent', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(commissionRequest),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create payment intent');
        }

        const { client_secret } = await response.json();
        setClientSecret(client_secret);
        setError(''); // Clear any previous errors
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Failed to create payment intent');
        setClientSecret(null);
      }
    };

    createPaymentIntent();
  }, [isOpen, amount, customerName, customerEmail, redditUsername, isAnonymous, commissionMessage, subreddit, postId, commissionType]);

  const handleSuccess = () => {
    setSuccess(true);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const extractPostId = (input: string) => {
    // Handle various Reddit URL formats
    const patterns = [
      /reddit\.com\/r\/\w+\/comments\/(\w+)/,
      /reddit\.com\/comments\/(\w+)/,
      /^(\w+)$/ // Just the post ID
    ];
    
    for (const pattern of patterns) {
      const match = input.match(pattern);
      if (match) {
        return match[1];
      }
    }
    return input; // Return as-is if no pattern matches
  };

  if (success) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} title="Commission Submitted!">
        <div className="flex flex-col items-center justify-center p-6">
          <div className="text-green-600 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="text-lg text-green-600 font-semibold mb-2">Thank you for your commission!</p>
          <p className="text-gray-600 text-center">Your commission has been submitted and will be processed soon.</p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Commission Art">
      <div className="space-y-6 p-6">
        {/* Commission Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Commission Type</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => { setCommissionType('random'); setPostId(''); }}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors ${commissionType === 'random' ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              🎲 Random Post
              <div className="text-xs mt-1 opacity-75">From selected subreddit</div>
            </button>
            <button
              type="button"
              onClick={() => setCommissionType('specific')}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors ${commissionType === 'specific' ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              🎯 Specific Post
              <div className="text-xs mt-1 opacity-75">Choose exact post</div>
            </button>
          </div>
        </div>

        {/* Subreddit Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Subreddit</label>
          <select
            value={subreddit}
            onChange={(e) => setSubreddit(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            {AVAILABLE_SUBREDDITS.map((sub) => (
              <option key={sub} value={sub}>r/{sub}</option>
            ))}
          </select>
        </div>

        {/* Post ID Input (only for specific posts) */}
        {commissionType === 'specific' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Post ID or URL</label>
            <input
              type="text"
              value={postId}
              onChange={(e) => setPostId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="e.g., 1llckgq or https://reddit.com/r/golf/comments/1llckgq/..."
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter the Reddit post ID or full URL
            </p>
          </div>
        )}

        {/* Preset Amount Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Commission Amount</label>
          <div className="grid grid-cols-3 gap-2 mb-2">
            {presetAmounts.map((preset, idx) => (
              <button
                key={preset}
                type="button"
                onClick={() => { setAmount(preset.toString()); setCustomAmount(''); }}
                className={`px-2 py-1 border rounded-lg text-xs font-medium transition-colors h-9 ${amount === preset.toString() ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
              >
                ${preset}
              </button>
            ))}
            {/* Custom Amount as last grid cell */}
            <div className="relative flex items-center h-9">
              <span className="absolute left-2 text-gray-500 text-xs">$</span>
              <input
                type="number"
                min="5"
                step="1"
                value={customAmount}
                onChange={e => { setCustomAmount(e.target.value); setAmount(e.target.value); }}
                className="w-full border border-gray-300 rounded-lg pl-5 pr-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent h-9"
                placeholder="Custom"
              />
            </div>
          </div>
        </div>

        {/* Customer Information */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
            <input
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name (optional)</label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Your Name"
            />
            <p className="text-xs text-gray-500 mt-1">
              Required for card payments, optional for Apple Pay/Google Pay/PayPal
            </p>
          </div>
          {/* Reddit Username and Anonymous Toggle */}
          <div className="flex items-center gap-3 mb-2">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Reddit Username</label>
              <input
                type="text"
                value={redditUsername}
                onChange={(e) => setRedditUsername(e.target.value)}
                className={`w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 ${isAnonymous ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`}
                placeholder="u/username"
                disabled={isAnonymous}
              />
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
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${isAnonymous ? 'bg-purple-500' : 'bg-gray-300'}`}
                aria-pressed={isAnonymous}
                aria-label="Toggle anonymous commission"
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${isAnonymous ? 'translate-x-5' : 'translate-x-1'}`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Commission Message */}
        <div>
          {!showMessage && (
            <button
              type="button"
              className="text-xs text-purple-500 underline mb-2"
              onClick={() => setShowMessage(true)}
            >
              + Add a commission message
            </button>
          )}
          {showMessage && (
            <>
              <button
                type="button"
                className="text-xs text-purple-500 underline mb-2"
                onClick={() => setShowMessage(false)}
              >
                – Hide commission message
              </button>
              <label className="block text-sm font-medium text-gray-700 mb-2 mt-2">Commission Message</label>
              <textarea
                value={commissionMessage}
                onChange={(e) => setCommissionMessage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                rows={3}
                placeholder="Leave a message to display with your commission..."
              />
              <p className="text-xs text-gray-500 mt-1">
                This message will be displayed alongside your commission for recognition purposes.
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

        {/* Express Checkout Element */}
        <div className="border-t pt-6">
          {clientSecret ? (
            <Elements 
              stripe={stripePromise}
              options={{
                clientSecret: clientSecret,
                appearance: {
                  theme: 'stripe',
                  variables: {
                    colorPrimary: '#9333ea',
                  },
                },
              }}
            >
              <CommissionForm
                amount={amount}
                commissionMessage={commissionMessage}
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
          ) : (
            <div className="text-center text-sm text-gray-600 py-4">
              Please fill in all required fields to continue
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

export default CommissionModal; 