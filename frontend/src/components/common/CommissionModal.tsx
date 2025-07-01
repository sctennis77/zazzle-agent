import React, { useState, useEffect, useRef } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, ExpressCheckoutElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from './Modal';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { FaCrown, FaStar, FaGem, FaHeart } from 'react-icons/fa';

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

interface CommissionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommissionRequest {
  amount_usd: string;
  subreddit: string;
  donation_type: 'commission';
  commission_type: 'random_subreddit' | 'specific_post';
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

// Helper to extract subreddit from a Reddit URL
function extractSubredditFromUrl(url: string): string | null {
  try {
    const match = url.match(/reddit\.com\/r\/([^/]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

// Helper to extract post ID from a Reddit URL
function extractPostIdFromUrl(url: string): string | null {
  try {
    // Match /comments/<postid>/
    const match = url.match(/comments\/([a-zA-Z0-9_]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

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
  amount: _amount, 
  commissionMessage: _commissionMessage, 
  customerEmail: _customerEmail, 
  customerName: _customerName, 
  redditUsername: _redditUsername, 
  isAnonymous: _isAnonymous, 
  subreddit: _subreddit, 
  postId: _postId, 
  onSuccess, 
  onError 
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [elementsReady, setElementsReady] = useState(false);

  // Monitor when Elements are ready
  useEffect(() => {
    if (stripe && elements) {
      console.log('Stripe Elements ready:', { stripe: !!stripe, elements: !!elements });
      setElementsReady(true);
    } else {
      console.log('Stripe Elements not ready:', { stripe: !!stripe, elements: !!elements });
      setElementsReady(false);
    }
  }, [stripe, elements]);

  const handleConfirm = async () => {
    if (!stripe || !elements) {
      console.error('Stripe or Elements not ready:', { stripe: !!stripe, elements: !!elements });
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
        console.error('Payment confirmation error:', error);
        onError(error.message || 'Payment failed');
      } else {
        onSuccess();
      }
    } catch (error) {
      console.error('Payment confirmation exception:', error);
      onError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsProcessing(false);
    }
  };

  const isRedditUsernameRequired = !_isAnonymous;
  const isRedditUsernameValid = _isAnonymous || (_redditUsername && _redditUsername.trim().length > 0);

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
              name: _customerName || '',
              email: _customerEmail || '',
            },
          },
        }}
      />

      {/* Always-visible Pay button for card payments */}
      <button
        className="w-full mt-2 py-2 px-4 bg-purple-600 text-white rounded disabled:opacity-50"
        onClick={handleConfirm}
        disabled={!stripe || !elements || isProcessing || !elementsReady || !isRedditUsernameValid}
        type="button"
      >
        {!elementsReady ? "Loading payment methods..." : isProcessing ? "Processing..." : "Pay"}
      </button>
      
      {!elementsReady && (
        <div className="text-center text-sm text-gray-600">
          Initializing payment methods...
        </div>
      )}
      
      {isProcessing && (
        <div className="text-center text-sm text-gray-600">
          Processing payment...
        </div>
      )}

      {!isRedditUsernameValid && (
        <div className="text-red-600 text-sm bg-red-50 p-2 rounded mt-2">
          Reddit username is required unless you select Anonymous.
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

const COMMISSION_TYPES = {
  SUBREDDIT: 'subreddit',
  SPECIFIC: 'specific',
};

const COMMISSION_MINIMUMS = {
  [COMMISSION_TYPES.SUBREDDIT]: 'silver', // $5
  [COMMISSION_TYPES.SPECIFIC]: 'gold',   // $10
};

const CommissionModal: React.FC<CommissionModalProps> = ({ isOpen, onClose }) => {
  const [amount, setAmount] = useState('');
  const [commissionMessage, setCommissionMessage] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [previousRedditUsername, setPreviousRedditUsername] = useState('');
  const [subreddit, setSubreddit] = useState('golf');
  const [postId, setPostId] = useState('');
  const [commissionType, setCommissionType] = useState(COMMISSION_TYPES.SUBREDDIT);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [customAmount, setCustomAmount] = useState('');
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [showMessage, setShowMessage] = useState(false);
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null);
  const isMounted = useRef(false);

  // Use dynamic tiers from API
  const { tiers, getTierDisplay } = useDonationTiers();

  // Determine minimum tier for commission type
  const minTierName = COMMISSION_MINIMUMS[commissionType];
  const minTierIdx = tiers.findIndex(t => t.name === minTierName);
  const allowedTiers = minTierIdx >= 0 ? tiers.slice(minTierIdx) : tiers;

  // Default to the minimum allowed tier on open
  useEffect(() => {
    if (isOpen && allowedTiers.length > 0) {
      setAmount(allowedTiers[0].min_amount.toString());
      setCustomAmount('');
    }
  }, [isOpen, commissionType, tiers.length]);

  // Create payment intent when modal is open and amount is set
  useEffect(() => {
    if (isOpen && amount && parseFloat(amount) >= (allowedTiers[0]?.min_amount || 1)) {
      createPaymentIntent();
    }
  }, [isOpen, amount, commissionType, tiers.length]);

  // Find the current tier based on amount
  const currentTier = allowedTiers
    .slice()
    .reverse()
    .find(t => parseFloat(amount) >= t.min_amount) || allowedTiers[0];
  const tierDisplay = getTierDisplay(currentTier?.name || minTierName);
  const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;

  // Validate minimum
  const minAmount = currentTier?.min_amount || 1;
  const isBelowMin = parseFloat(amount) < minAmount;

  useEffect(() => {
    isMounted.current = isOpen;
    return () => { isMounted.current = false; };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setCustomAmount('');
      setCommissionMessage('');
      setCustomerEmail('');
      setCustomerName('');
      setRedditUsername('');
      setPreviousRedditUsername('');
      setIsAnonymous(false);
      setSubreddit('golf');
      setPostId('');
      setCommissionType(COMMISSION_TYPES.SUBREDDIT);
      setError('');
      setSuccess(false);
      setShowMessage(false);
      // Don't reset clientSecret and paymentIntentId here - let createPaymentIntent handle it
      (async () => {
        const paymentIntentId = await createPaymentIntent();
        if (!isMounted.current) return;
      })();
    } else {
      setClientSecret(null);
      setPaymentIntentId(null);
    }
  }, [isOpen]);

  // Function to create new PaymentIntent
  const createPaymentIntent = async () => {
    if (!isOpen || !amount || parseFloat(amount) < minAmount) {
      console.log('Skipping payment intent creation:', { isOpen, amount, minAmount });
      return null;
    }

    // For specific post commissions, post_id is required
    if (commissionType === COMMISSION_TYPES.SPECIFIC && !postId) {
      setError('Post ID or URL is required for specific post commissions');
      return null;
    }

    setError(''); // Clear any previous errors

    try {
      console.log('Creating payment intent for commission:', { amount, subreddit, commissionType });
      
      const commissionRequest: CommissionRequest = {
        amount_usd: amount,
        subreddit,
        donation_type: 'commission',
        commission_type: commissionType === COMMISSION_TYPES.SUBREDDIT ? 'random_subreddit' : 'specific_post',
        post_id: commissionType === COMMISSION_TYPES.SPECIFIC
          ? (() => {
              const extracted = extractPostIdFromUrl(postId);
              const candidate = extracted || (postId && !postId.includes('reddit.com') ? postId : undefined);
              if (candidate && candidate.startsWith('pi_')) return undefined;
              return candidate;
            })()
          : undefined,
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

      const { client_secret, payment_intent_id } = await response.json();
      console.log('Payment intent created successfully:', { payment_intent_id });
      
      if (!isMounted.current) return null;
      setClientSecret(client_secret);
      setPaymentIntentId(payment_intent_id);
      setError(''); // Clear any previous errors
      return payment_intent_id;
    } catch (error) {
      console.error('Failed to create payment intent:', error);
      if (!isMounted.current) return null;
      setError(error instanceof Error ? error.message : 'Failed to create payment intent');
      setClientSecret(null);
      setPaymentIntentId(null);
      return null;
    }
  };

  // Function to update existing PaymentIntent
  const updatePaymentIntent = async () => {
    if (!paymentIntentId || !amount || parseFloat(amount) < minAmount) {
      return null;
    }

    setError(''); // Clear any previous errors

    try {
      const commissionRequest: CommissionRequest = {
        amount_usd: amount,
        subreddit,
        donation_type: 'commission',
        commission_type: commissionType === COMMISSION_TYPES.SUBREDDIT ? 'random_subreddit' : 'specific_post',
        post_id: commissionType === COMMISSION_TYPES.SPECIFIC
          ? (() => {
              const extracted = extractPostIdFromUrl(postId);
              const candidate = extracted || (postId && !postId.includes('reddit.com') ? postId : undefined);
              if (candidate && candidate.startsWith('pi_')) return undefined;
              return candidate;
            })()
          : undefined,
        commission_message: commissionMessage,
        customer_email: customerEmail || undefined,
        customer_name: customerName || undefined,
        reddit_username: redditUsername.trim() || undefined,
        is_anonymous: isAnonymous,
      };

      const response = await fetch(`/api/donations/payment-intent/${paymentIntentId}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(commissionRequest),
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
      if (error instanceof Error) {
        console.error('Failed to update payment intent:', error.message);
      } else if (typeof error === 'object' && error !== null) {
        console.error('Failed to update payment intent:', JSON.stringify(error));
      } else {
        console.error('Failed to update payment intent:', error);
      }
      return null;
    }
  };

  // Debounced update effect
  useEffect(() => {
    if (!paymentIntentId || !isOpen) return;

    const timeoutId = setTimeout(() => {
      updatePaymentIntent();
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [paymentIntentId, amount, customerName, customerEmail, redditUsername, isAnonymous, commissionMessage, subreddit, postId, commissionType]);

  const handleSuccess = () => {
    setSuccess(true);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  if (success) {
    // Redirect to gallery view after a short delay
    setTimeout(() => {
      window.location.href = '/';
    }, 1200);
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
        {/* Tier selection and badge */}
        <div className="flex items-center gap-3 mb-2">
          <div className={`p-2 rounded-full ${tierDisplay.bgColor} border ${tierDisplay.borderColor}`}>
            <IconComponent size={20} className={tierDisplay.color} />
          </div>
          <div>
            <div className="font-semibold text-gray-900 text-base">{currentTier?.display_name || minTierName} Tier</div>
            <div className="text-xs text-gray-500">Minimum: ${minAmount.toFixed(2)}</div>
          </div>
        </div>
        {/* Commission Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Commission Type</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => { 
                setCommissionType(COMMISSION_TYPES.SUBREDDIT); 
                setPostId(''); 
                setError('');
                if (paymentIntentId) updatePaymentIntent();
              }}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors ${commissionType === COMMISSION_TYPES.SUBREDDIT ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              🎲 Random Post
              <div className="text-xs mt-1 opacity-75">From selected subreddit</div>
            </button>
            <button
              type="button"
              onClick={() => {
                setCommissionType(COMMISSION_TYPES.SPECIFIC);
                setSubreddit(''); // Unset subreddit when switching to specific post
                setPostId('');
                setError('');
                if (paymentIntentId) updatePaymentIntent();
              }}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors ${commissionType === COMMISSION_TYPES.SPECIFIC ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              🎯 Specific Post
              <div className="text-xs mt-1 opacity-75">Choose exact post</div>
            </button>
          </div>
        </div>

        {/* Subreddit Selection */}
        {commissionType !== COMMISSION_TYPES.SPECIFIC && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Subreddit</label>
            <select
              value={subreddit}
              onChange={(e) => {
                setSubreddit(e.target.value);
                if (paymentIntentId) updatePaymentIntent();
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              {AVAILABLE_SUBREDDITS.map((sub) => (
                <option key={sub} value={sub}>r/{sub}</option>
              ))}
            </select>
          </div>
        )}

        {/* Post ID Input (only for specific posts) */}
        {commissionType === COMMISSION_TYPES.SPECIFIC && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Post ID or URL</label>
            <input
              type="text"
              value={postId}
              onChange={(e) => {
                const value = e.target.value;
                setPostId(value);
                // If it's a Reddit URL, extract subreddit and post ID
                const subredditFromUrl = extractSubredditFromUrl(value);
                const postIdFromUrl = extractPostIdFromUrl(value);
                if (subredditFromUrl) {
                  setSubreddit(subredditFromUrl);
                } else {
                  setSubreddit('');
                }
                if (paymentIntentId) updatePaymentIntent();
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="e.g., 1llckgq or https://reddit.com/r/golf/comments/1llckgq/..."
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter the Reddit post ID or full URL
            </p>
            {/* Extracted post ID and subreddit display */}
            {(() => {
              const postIdFromUrl = extractPostIdFromUrl(postId);
              const displayPostId = postIdFromUrl || (postId && !postId.includes('reddit.com') ? postId : '');
              return (
                <>
                  {displayPostId && (
                    <div className="text-sm font-semibold text-purple-700 mt-2">
                      Post ID: {displayPostId}
                    </div>
                  )}
                  {subreddit && (
                    <div className="text-sm font-semibold text-green-700 mt-1">
                      Subreddit: r/{subreddit}
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}

        {/* Preset Amount Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Choose Amount</label>
          <div className="grid grid-cols-3 gap-2 mb-2">
            {allowedTiers.map((tier) => {
              const tDisplay = getTierDisplay(tier.name);
              const TIcon = iconMap[tDisplay.icon as keyof typeof iconMap] || FaHeart;
              return (
                <button
                  key={tier.name}
                  type="button"
                  onClick={() => {
                    setAmount(tier.min_amount.toString());
                    setCustomAmount('');
                    if (paymentIntentId) updatePaymentIntent();
                  }}
                  className={`flex items-center gap-1 px-2 py-1 border rounded-lg text-xs font-medium transition-colors h-9 ${amount === tier.min_amount.toString() ? tDisplay.bgColor + ' ' + tDisplay.color + ' border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
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
                min={allowedTiers[0]?.min_amount || 1}
                step="0.01"
                value={customAmount}
                onChange={e => {
                  setCustomAmount(e.target.value);
                  setAmount(e.target.value);
                  if (paymentIntentId) updatePaymentIntent();
                }}
                className="w-full border border-gray-300 rounded-lg pl-5 pr-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent h-9"
                placeholder="Custom"
              />
            </div>
          </div>
          {isBelowMin && (
            <div className="text-xs text-red-500 mt-1">Minimum for {currentTier?.display_name} is ${minAmount.toFixed(2)}</div>
          )}
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
                      colorPrimary: '#9333ea',
                      borderRadius: '8px',
                    },
                  },
                  loader: 'auto',
                }}
                key={clientSecret}
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