import React, { useState, useEffect, useRef } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, ExpressCheckoutElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from './Modal';
import { useDonationTiers } from '../../hooks/useDonationTiers';
import { FaCrown, FaStar, FaGem, FaHeart } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { API_BASE } from '../../utils/apiBase';

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

interface CommissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialPostId?: string;
}

interface CommissionRequest {
  amount_usd: string;
  subreddit: string;
  donation_type: 'commission';
  commission_type: 'random_subreddit' | 'specific_post' | 'random_random';
  post_id?: string;
  commission_message?: string;
  customer_email?: string;
  customer_name?: string;
  reddit_username?: string;
  is_anonymous: boolean;
}

// Validation result interface
interface ValidationResult {
  valid: boolean;
  subreddit?: string;
  subreddit_id?: number;
  post_id?: string;
  post_title?: string;
  post_content?: string;
  post_url?: string;
  commission_type: string;
  error?: string;
  agent_ratings?: {
    mood?: string[];
    topic?: string[];
    illustration_potential?: number;
  };
}

// Subreddit API types
interface SubredditInfo {
  id: number;
  subreddit_name: string;
  display_name?: string;
  description?: string;
  public_description?: string;
  subscribers?: number;
  over18: boolean;
  created_at: string;
  updated_at: string;
}

interface SubredditValidationResponse {
  subreddit_name: string;
  exists: boolean;
  message: string;
  subreddit?: SubredditInfo;
}

// API functions for subreddit management
const fetchAvailableSubreddits = async (): Promise<SubredditInfo[]> => {
  try {
    const response = await fetch(`${API_BASE}/api/subreddits`);
    if (!response.ok) {
      throw new Error(`Failed to fetch subreddits: ${response.statusText}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching subreddits:', error);
    return [];
  }
};

const validateSubreddit = async (subredditName: string): Promise<SubredditValidationResponse> => {
  try {
    const response = await fetch(`${API_BASE}/api/subreddits/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ subreddit_name: subredditName }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to validate subreddit: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error validating subreddit:', error);
    return {
      subreddit_name: subredditName,
      exists: false,
      message: 'Failed to validate subreddit. Please try again.',
    };
  }
};

// Helper to extract subreddit from a Reddit URL
function extractSubredditFromUrl(url: string | any): string | null {
  try {
    if (typeof url !== 'string') {
      return null;
    }
    const match = url.match(/reddit\.com\/r\/([^/]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

// Helper to extract post ID from a Reddit URL
function extractPostIdFromUrl(url: string | any): string | null {
  try {
    if (typeof url !== 'string') {
      return null;
    }
    // Match /comments/<postid>/
    const match = url.match(/comments\/([a-zA-Z0-9_]+)/);
    return match ? match[1] : null;
  } catch {
    return null;
  }
}

// Helper to format artistic potential level
function formatArtisticPotential(potential: number | undefined): { level: string; color: string } {
  const safePotential = potential || 0;
  if (safePotential >= 9) {
    return { level: 'Very High', color: 'text-purple-600' };
  } else if (safePotential >= 7) {
    return { level: 'High', color: 'text-blue-600' };
  } else {
    return { level: 'Medium', color: 'text-green-600' };
  }
}

// Component to display agent ratings
const AgentRatingsDisplay: React.FC<{ agentRatings: NonNullable<ValidationResult['agent_ratings']> }> = ({ agentRatings }) => {
  const { level, color } = formatArtisticPotential(agentRatings.illustration_potential || 0);
  
  // Don't render if no meaningful data
  const hasMood = agentRatings.mood && agentRatings.mood.length > 0;
  const hasTopic = agentRatings.topic && agentRatings.topic.length > 0;
  const hasPotential = agentRatings.illustration_potential !== undefined && agentRatings.illustration_potential > 0;
  
  if (!hasMood && !hasTopic && !hasPotential) {
    return null;
  }
  
  return (
    <div className="mt-2 p-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
      <div className="text-sm font-medium text-gray-700 mb-2">✨ AI Content Analysis</div>
      <div className="flex flex-wrap gap-3 text-sm">
        {hasMood && (
          <div className="flex items-center gap-1">
            <span className="text-gray-600">Mood:</span>
            <span>{agentRatings.mood.join(' ')}</span>
          </div>
        )}
        {hasTopic && (
          <div className="flex items-center gap-1">
            <span className="text-gray-600">Theme:</span>
            <span>{agentRatings.topic.join(' ')}</span>
          </div>
        )}
        {hasPotential && (
          <div className="flex items-center gap-1">
            <span className="text-gray-600">Artistic Potential:</span>
            <span className={`font-semibold ${color}`}>{level} ({agentRatings.illustration_potential}/10)</span>
          </div>
        )}
      </div>
    </div>
  );
};

// Wrapper component to handle Elements readiness
const CommissionFormWrapper: React.FC<{
  amount: string;
  commissionMessage: string;
  customerEmail: string;
  customerName: string;
  redditUsername: string;
  isAnonymous: boolean;
  subreddit: string;
  postId?: string;
  onSuccess: (paymentIntentId?: string) => void;
  onError: (error: string) => void;
  onElementsReady: () => void;
}> = (props) => {
  const stripe = useStripe();
  const elements = useElements();
  const [hasNotifiedReady, setHasNotifiedReady] = useState(false);

  // Monitor when Elements are ready and notify parent
  useEffect(() => {
    if (stripe && elements && !hasNotifiedReady) {
      console.log('Stripe Elements ready:', { stripe: !!stripe, elements: !!elements });
      props.onElementsReady();
      setHasNotifiedReady(true);
    }
  }, [stripe, elements, hasNotifiedReady, props]);

  // Don't render form until Elements are ready
  if (!stripe || !elements) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[200px] text-gray-500">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-4"></div>
        <span>Loading payment form...</span>
      </div>
    );
  }

  return <CommissionForm {...props} />;
};

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
  onSuccess: (paymentIntentId?: string) => void;
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

  const handleConfirm = async () => {
    if (!stripe || !elements) {
      console.error('Stripe or Elements not ready:', { stripe: !!stripe, elements: !!elements });
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
        console.error('Payment confirmation error:', error);
        onError(error.message || 'Payment failed');
      } else if (paymentIntent && paymentIntent.status === 'succeeded') {
        // Payment succeeded, call onSuccess directly
        onSuccess();
      } else {
        // Payment is processing or requires additional action
        onError('Payment is being processed. Please check your email for confirmation.');
      }
    } catch (error) {
      console.error('Payment confirmation exception:', error);
      onError(error instanceof Error ? error.message : 'An error occurred');
    } finally {
      setIsProcessing(false);
    }
  };

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

      {/* Submit button for card payments */}
      <button
        onClick={handleConfirm}
        disabled={!stripe || !elements || isProcessing || !isRedditUsernameValid}
        className={`w-full py-3 px-4 rounded-md font-medium transition-colors ${
          !stripe || !elements || isProcessing || !isRedditUsernameValid
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-purple-600 text-white hover:bg-purple-700'
        }`}
      >
        {isProcessing ? 'Processing...' : 'Pay with Card'}
      </button>

      {/* Validation messages */}
      {!isRedditUsernameValid && !_isAnonymous && (
        <p className="text-sm text-red-600">Reddit username is required when not anonymous</p>
      )}
    </div>
  );
};

const iconMap = {
  crown: FaCrown,
  star: FaStar,
  gem: FaGem,
  heart: FaHeart,
};

const COMMISSION_TYPES = {
  SUBREDDIT: 'subreddit',
  SPECIFIC: 'specific',
  RANDOM: 'random',
};

const COMMISSION_MINIMUMS = {
  [COMMISSION_TYPES.SUBREDDIT]: 'silver', // $5
  [COMMISSION_TYPES.SPECIFIC]: 'gold',   // $10
  [COMMISSION_TYPES.RANDOM]: 'bronze',   // $1
};

const CommissionModal: React.FC<CommissionModalProps> = ({ isOpen, onClose, onSuccess, initialPostId }) => {
  const [amount, setAmount] = useState('');
  const [commissionMessage, setCommissionMessage] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [previousRedditUsername, setPreviousRedditUsername] = useState('');
  const [subreddit, setSubreddit] = useState('');
  const [postId, setPostId] = useState('');
  const [commissionType, setCommissionType] = useState(COMMISSION_TYPES.SUBREDDIT); // Default to random_subreddit
  
  // Subreddit management state
  const [availableSubreddits, setAvailableSubreddits] = useState<SubredditInfo[]>([]);
  const [customSubreddit, setCustomSubreddit] = useState('');
  const [isValidatingSubreddit, setIsValidatingSubreddit] = useState(false);
  const [subredditValidationMessage, setSubredditValidationMessage] = useState('');
  const [showCustomSubredditInput, setShowCustomSubredditInput] = useState(false);
  const [subredditSearchTerm, setSubredditSearchTerm] = useState('');
  const [showSubredditDropdown, setShowSubredditDropdown] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [error, setError] = useState('');
  // Note: error state is used in error handling logic
  const [success, setSuccess] = useState(false);
  const [customAmount, setCustomAmount] = useState('');
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null);
  const [stripeElementsReady, setStripeElementsReady] = useState(false);
  
  // Validation state
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [messageError, setMessageError] = useState<string | null>(null);
  
  const isMounted = useRef(false);

  // Use dynamic tiers from API
  const { tiers, getTierDisplay } = useDonationTiers();

  // Determine minimum tier for commission type
  const minTierName = COMMISSION_MINIMUMS[commissionType];
  const minTierIdx = tiers.findIndex(t => t.name === minTierName);
  const allowedTiers = minTierIdx >= 0 ? tiers.slice(minTierIdx) : tiers;

  // Default to the minimum allowed tier on open
  useEffect(() => {
    if (isOpen && allowedTiers && allowedTiers.length > 0) {
      setAmount(allowedTiers[0].min_amount.toString());
      setCustomAmount('');
    }
  }, [isOpen, commissionType, tiers.length]);

  // Find the current tier based on amount
  const currentTier = allowedTiers && allowedTiers.length > 0 ? allowedTiers
    .slice()
    .reverse()
    .find(t => parseFloat(amount) >= t.min_amount) || allowedTiers[0] : null;
  const tierDisplay = getTierDisplay(currentTier?.name || minTierName);
  const IconComponent = iconMap[tierDisplay.icon as keyof typeof iconMap] || FaHeart;

  // Validate minimum
  const minAmount = currentTier?.min_amount || 1;
  const isBelowMin = parseFloat(amount) < minAmount;

  useEffect(() => {
    isMounted.current = isOpen;
    return () => { isMounted.current = false; };
  }, [isOpen]);

  // Load available subreddits when modal opens
  useEffect(() => {
    if (isOpen) {
      loadAvailableSubreddits();
    }
  }, [isOpen]);

  const loadAvailableSubreddits = async () => {
    try {
      const subreddits = await fetchAvailableSubreddits();
      setAvailableSubreddits(subreddits);
    } catch (error) {
      console.error('Error loading subreddits:', error);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setCustomAmount('');
      setCommissionMessage('');
      setCustomerEmail('');
      setCustomerName('');
      setRedditUsername('');
      setPreviousRedditUsername('');
      setIsAnonymous(false);
      setSubreddit(''); // Unselected subreddit
      
      // Handle initial post ID from Clouvel Agent
      if (initialPostId && typeof initialPostId === 'string' && initialPostId.trim() !== '') {
        setPostId(initialPostId);
        setCommissionType(COMMISSION_TYPES.SPECIFIC);
        
        // If it's a Reddit URL, extract subreddit and auto-validate
        const subredditFromUrl = extractSubredditFromUrl(initialPostId);
        if (subredditFromUrl) {
          setSubreddit(subredditFromUrl);
          // Trigger validation after a short delay to ensure state is set
          setTimeout(() => {
            validateCommission(COMMISSION_TYPES.SPECIFIC, subredditFromUrl, initialPostId);
          }, 100);
        }
      } else {
        setPostId('');
        setCommissionType(COMMISSION_TYPES.SUBREDDIT); // Default to random_subreddit
      }
      
      setError('');
      setSuccess(false);
      setValidationResult(null);
      setValidationError('');
      setClientSecret(null);
      setPaymentIntentId(null);
      setUsernameError(null);
      setMessageError(null);
      setStripeElementsReady(false);
      
      // Reset subreddit management state
      setCustomSubreddit('');
      setIsValidatingSubreddit(false);
      setSubredditValidationMessage('');
      setShowCustomSubredditInput(false);
      setSubredditSearchTerm('');
      setShowSubredditDropdown(false);
      setHighlightedIndex(-1);
    }
  }, [isOpen, initialPostId]);

  // Handle commission type changes
  const handleCommissionTypeChange = (type: string) => {
    setCommissionType(type);
    setValidationResult(null);
    setValidationError('');
    setClientSecret(null);
    setPaymentIntentId(null);
    setError('');
    if (type === COMMISSION_TYPES.RANDOM) {
      // Immediately validate for random_random
      validateCommission(type, '', '');
    } else if (type === COMMISSION_TYPES.SUBREDDIT) {
      setSubreddit(''); // Reset subreddit
      setSubredditSearchTerm('');
      setShowSubredditDropdown(false);
      setHighlightedIndex(-1);
    } else if (type === COMMISSION_TYPES.SPECIFIC) {
      setPostId('');
      setSubreddit('');
    }
  };

  // Handle custom subreddit validation
  const handleCustomSubredditValidation = async () => {
    if (!customSubreddit.trim()) {
      setSubredditValidationMessage('Please enter a subreddit name');
      return;
    }

    setIsValidatingSubreddit(true);
    setSubredditValidationMessage('');

    try {
      const result = await validateSubreddit(customSubreddit.trim());
      
      if (result.exists && result.subreddit) {
        // Successfully validated and added
        setSubredditValidationMessage(result.message);
        
        // Add to available subreddits list and select it
        const newSubreddit = result.subreddit;
        setAvailableSubreddits(prev => {
          // Check if already exists to avoid duplicates
          const exists = prev.some(s => s.subreddit_name === newSubreddit.subreddit_name);
          if (exists) return prev;
          return [...prev, newSubreddit].sort((a, b) => a.subreddit_name.localeCompare(b.subreddit_name));
        });
        
        // Select the newly validated subreddit
        setSubreddit(newSubreddit.subreddit_name);
        setCustomSubreddit('');
        setShowCustomSubredditInput(false);
        
        // Clear validation message after a short delay
        setTimeout(() => setSubredditValidationMessage(''), 3000);
      } else {
        // Validation failed
        setSubredditValidationMessage(result.message);
      }
    } catch (error) {
      setSubredditValidationMessage('Error validating subreddit. Please try again.');
    } finally {
      setIsValidatingSubreddit(false);
    }
  };

  // Filter subreddits based on search term
  const filteredSubreddits = (availableSubreddits || []).filter(sub =>
    sub.subreddit_name.toLowerCase().includes(subredditSearchTerm.toLowerCase()) ||
    (sub.display_name && sub.display_name.toLowerCase().includes(subredditSearchTerm.toLowerCase()))
  );

  // Handle selecting a subreddit from dropdown
  const handleSubredditSelect = (value: string) => {
    if (value === 'custom') {
      setShowCustomSubredditInput(true);
      setSubreddit('');
      setShowSubredditDropdown(false);
    } else {
      setSubreddit(value);
      setSubredditSearchTerm(`r/${value}`);
      setShowSubredditDropdown(false);
      setShowCustomSubredditInput(false);
      setCustomSubreddit('');
      setSubredditValidationMessage('');
      
      // Clear previous validation and run new validation if a subreddit is selected
      setValidationResult(null);
      setValidationError('');
      setClientSecret(null);
      setPaymentIntentId(null);
      
      if (value) {
        setTimeout(() => validateCommission(COMMISSION_TYPES.SUBREDDIT, value, ''), 100);
      }
    }
  };

  // Handle search input change
  const handleSubredditSearchChange = (value: string) => {
    setSubredditSearchTerm(value);
    setHighlightedIndex(-1);
    if (value.trim() === '') {
      setSubreddit('');
      setShowSubredditDropdown(false);
    } else {
      setShowSubredditDropdown(true);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSubredditDropdown) return;

    const options = ['custom', ...filteredSubreddits.map(sub => sub.subreddit_name)];
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => prev < options.length - 1 ? prev + 1 : prev);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : prev);
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0) {
          const selectedOption = options[highlightedIndex];
          handleSubredditSelect(selectedOption);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setShowSubredditDropdown(false);
        setHighlightedIndex(-1);
        break;
    }
  };

  // Validation function (now takes explicit args)
  const validateCommission = async (
    type = commissionType,
    sub = subreddit,
    post = postId
  ) => {
    if (type === COMMISSION_TYPES.SUBREDDIT && !sub) return;
    if (type === COMMISSION_TYPES.SPECIFIC && !post) return;
    setIsValidating(true);
    setValidationError('');
    setValidationResult(null);
    try {
      const validationRequest = {
        commission_type: type === COMMISSION_TYPES.SUBREDDIT ? 'random_subreddit' : 
                        type === COMMISSION_TYPES.SPECIFIC ? 'specific_post' : 'random_random',
        subreddit: type === COMMISSION_TYPES.RANDOM ? undefined : sub,
        post_id: type === COMMISSION_TYPES.SPECIFIC ? 
                (() => {
                  const extracted = extractPostIdFromUrl(post);
                  return extracted || (post && typeof post === 'string' && !post.includes('reddit.com') ? post : undefined);
                })() : undefined,
      };
      const response = await fetch(`${API_BASE}/api/commissions/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(validationRequest),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Validation failed');
      }
      const result: ValidationResult = await response.json();
      if (!isMounted.current) return;
      if (result.valid) {
        setValidationResult(result);
        setValidationError('');
        createPaymentIntent(result);
      } else {
        setValidationResult(null);
        setValidationError(result.error || 'Validation failed');
        setClientSecret(null);
        setPaymentIntentId(null);
      }
    } catch (error) {
      if (!isMounted.current) return;
      setValidationError(error instanceof Error ? error.message : 'Validation failed');
      setValidationResult(null);
      setClientSecret(null);
      setPaymentIntentId(null);
    } finally {
      setIsValidating(false);
    }
  };

  // Subreddit select handler (updated to use new logic above)

  // Post ID input handler
  const handlePostIdInput = (value: string) => {
    setPostId(value);
    // If it's a Reddit URL, extract subreddit and post ID
    const subredditFromUrl = extractSubredditFromUrl(value);
    if (subredditFromUrl) {
      setSubreddit(subredditFromUrl);
    } else {
      setSubreddit('');
    }
    setValidationResult(null);
    setValidationError('');
    setClientSecret(null);
    setPaymentIntentId(null);
    if (value) {
      setTimeout(() => validateCommission(COMMISSION_TYPES.SPECIFIC, subredditFromUrl || subreddit, value), 500);
    }
  };

  // Function to create new PaymentIntent
  const createPaymentIntent = async (validationData?: ValidationResult) => {
    if (!isOpen || !amount || parseFloat(amount) < minAmount) {
      console.log('Skipping payment intent creation:', { isOpen, amount, minAmount });
      return null;
    }

    // Use validation data if available, otherwise use form data
    const validatedSubreddit = validationData?.subreddit || subreddit;
    const validatedPostId = validationData?.post_id || postId;

    setError(''); // Clear any previous errors

    try {
      console.log('Creating payment intent for commission:', { 
        amount, 
        validatedSubreddit, 
        commissionType,
        validatedPostId 
      });
      
      const commissionRequest: CommissionRequest = {
        amount_usd: amount,
        subreddit: commissionType === COMMISSION_TYPES.RANDOM ? "" : validatedSubreddit,
        donation_type: 'commission',
        commission_type: commissionType === COMMISSION_TYPES.SUBREDDIT ? 'random_subreddit' : 
                        commissionType === COMMISSION_TYPES.SPECIFIC ? 'specific_post' : 'random_random',
        post_id: validatedPostId, // Always use the validated post_id from validation result
        commission_message: commissionMessage,
        customer_email: customerEmail || undefined,
        customer_name: customerName || undefined,
        reddit_username: redditUsername.trim() || undefined,
        is_anonymous: isAnonymous,
      };

      const response = await fetch(`${API_BASE}/api/donations/create-payment-intent`, {
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
      // Use validation data if available, otherwise use form data
      const validatedSubreddit = validationResult?.subreddit || subreddit;
      const validatedPostId = validationResult?.post_id || postId;

      const commissionRequest: CommissionRequest = {
        amount_usd: amount,
        subreddit: commissionType === COMMISSION_TYPES.RANDOM ? "" : validatedSubreddit,
        donation_type: 'commission',
        commission_type: commissionType === COMMISSION_TYPES.SUBREDDIT ? 'random_subreddit' : 
                        commissionType === COMMISSION_TYPES.SPECIFIC ? 'specific_post' : 'random_random',
        post_id: validatedPostId, // Always use the validated post_id from validation result
        commission_message: commissionMessage,
        customer_email: customerEmail || undefined,
        customer_name: customerName || undefined,
        reddit_username: redditUsername.trim() || undefined,
        is_anonymous: isAnonymous,
      };

      const response = await fetch(`${API_BASE}/api/donations/payment-intent/${paymentIntentId}/update`, {
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
  }, [paymentIntentId, amount, customerName, customerEmail, redditUsername, isAnonymous, commissionMessage]);

  // Track timeout for auto-closing success modal
  const successTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset success state when modal is closed
  useEffect(() => {
    if (!isOpen) {
      setSuccess(false);
      if (successTimeoutRef.current) {
        clearTimeout(successTimeoutRef.current);
        successTimeoutRef.current = null;
      }
    }
  }, [isOpen]);

  const navigate = useNavigate();

  const handleSuccess = (paymentIntentId?: string) => {
    onClose();
    if (paymentIntentId) {
      navigate(`/donation/success?payment_intent=${paymentIntentId}`);
    } else {
      navigate('/', { state: { showToast: true } });
    }
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };



  if (success) {
    return (
      <Modal isOpen={isOpen} onClose={() => { setSuccess(false); onClose(); }} title="Commission Submitted!">
        <div className="flex flex-col items-center justify-center p-6">
          <div className="text-green-600 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="text-lg text-green-600 font-semibold mb-2">Thank you for your commission!</p>
          <p className="text-gray-600 text-center">Your commission is being processed. You'll be redirected to the gallery shortly...</p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Commission Art">
      <div className="space-y-4 sm:space-y-6 p-4 sm:p-6">
        {error && (
          <p className="text-sm text-red-600 mb-2">{error}</p>
        )}
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
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => handleCommissionTypeChange(COMMISSION_TYPES.RANDOM)}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors touch-manipulation ${commissionType === COMMISSION_TYPES.RANDOM ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              <span role="img" aria-label="Random">🎲</span> Random<br />Random subreddit & post
            </button>
            <button
              type="button"
              onClick={() => handleCommissionTypeChange(COMMISSION_TYPES.SUBREDDIT)}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors touch-manipulation ${commissionType === COMMISSION_TYPES.SUBREDDIT ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              <span role="img" aria-label="Random Post">🎲</span> Random Post<br />From selected subreddit
            </button>
            <button
              type="button"
              onClick={() => handleCommissionTypeChange(COMMISSION_TYPES.SPECIFIC)}
              className={`p-3 border rounded-lg text-sm font-medium transition-colors touch-manipulation ${commissionType === COMMISSION_TYPES.SPECIFIC ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              <span role="img" aria-label="Specific Post">🎯</span> Specific Post<br />Choose exact post
            </button>
          </div>
        </div>

        {/* Subreddit Selection */}
        {commissionType === COMMISSION_TYPES.SUBREDDIT && (
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-2">Subreddit</label>
            
            {/* Search input */}
            <div className="relative">
              <input
                type="text"
                value={subredditSearchTerm}
                onChange={(e) => handleSubredditSearchChange(e.target.value)}
                onFocus={() => setShowSubredditDropdown(true)}
                onKeyDown={handleKeyDown}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 pr-8"
                placeholder="Search or type subreddit name..."
                autoComplete="off"
              />
              <div className="absolute inset-y-0 right-0 flex items-center pr-2">
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            {/* Dropdown */}
            {showSubredditDropdown && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
                {/* Add new subreddit option at the top */}
                <button
                  type="button"
                  onClick={() => handleSubredditSelect('custom')}
                  className={`w-full px-3 py-3 text-left border-b border-gray-100 text-purple-600 font-medium touch-manipulation ${
                    highlightedIndex === 0 ? 'bg-purple-50' : 'hover:bg-purple-50'
                  }`}
                >
                  <span className="mr-2">📝</span>
                  Add a new subreddit...
                </button>
                
                {/* Filtered subreddits */}
                {filteredSubreddits.length > 0 ? (
                  filteredSubreddits.map((sub, index) => (
                    <button
                      key={sub.id}
                      type="button"
                      onClick={() => handleSubredditSelect(sub.subreddit_name)}
                      className={`w-full px-3 py-3 text-left touch-manipulation ${
                        highlightedIndex === index + 1 ? 'bg-gray-100' : 'hover:bg-gray-50'
                      }`}
                    >
                      <span className="font-medium">r/{sub.subreddit_name}</span>
                    </button>
                  ))
                ) : subredditSearchTerm && (
                  <div className="px-3 py-3 text-gray-500 text-sm">
                    No matching subreddits found. Try adding a new one above.
                  </div>
                )}
              </div>
            )}

            {/* Click outside to close dropdown */}
            {showSubredditDropdown && (
              <div 
                className="fixed inset-0 z-5" 
                onClick={() => setShowSubredditDropdown(false)}
              />
            )}
            
            {/* Custom subreddit input */}
            {showCustomSubredditInput && (
              <div className="mt-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customSubreddit}
                    onChange={(e) => setCustomSubreddit(e.target.value)}
                    placeholder="Enter subreddit name (e.g., 'photography')"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleCustomSubredditValidation();
                      } else if (e.key === 'Escape') {
                        setShowCustomSubredditInput(false);
                        setCustomSubreddit('');
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleCustomSubredditValidation}
                    disabled={isValidatingSubreddit || !customSubreddit.trim()}
                    className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isValidatingSubreddit ? 'Validating...' : 'Add'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowCustomSubredditInput(false);
                      setCustomSubreddit('');
                      setSubredditValidationMessage('');
                    }}
                    className="px-3 py-2 text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                </div>
                {subredditValidationMessage && (
                  <p className={`mt-2 text-sm ${subredditValidationMessage.includes('successfully') || subredditValidationMessage.includes('already exists') ? 'text-green-600' : 'text-red-600'}`}>
                    {subredditValidationMessage}
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Post ID Input (only for specific posts) */}
        {commissionType === COMMISSION_TYPES.SPECIFIC && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Post ID or URL</label>
            <input
              type="text"
              value={postId}
              onChange={(e) => handlePostIdInput(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="e.g., 1llckgq or https://reddit.com/r/golf/comments/1llckgq/..."
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter the Reddit post ID or full URL
            </p>
            {/* Extracted post ID and subreddit display */}
            {(() => {
              const postIdFromUrl = extractPostIdFromUrl(postId);
              const displayPostId = postIdFromUrl || (postId && typeof postId === 'string' && !postId.includes('reddit.com') ? postId : '');
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

        {/* Validation Status */}
        {isValidating && (
          <div className="flex items-center gap-2 text-blue-600 text-sm">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            Validating commission...
          </div>
        )}

        {validationError && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
            {validationError}
          </div>
        )}

        {validationResult && validationResult.valid && (
          <div className="text-green-600 text-sm bg-green-50 p-3 rounded-md">
            <div className="font-semibold mb-1">✅ Commission Validated</div>
            <div>Subreddit: r/{validationResult.subreddit}</div>
            {validationResult.post_id && (
              <div>Post: {validationResult.post_title || validationResult.post_id}</div>
            )}
            {validationResult.agent_ratings && (
              <AgentRatingsDisplay agentRatings={validationResult.agent_ratings} />
            )}
          </div>
        )}

        {/* Preset Amount Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">Choose Amount</label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            {allowedTiers && allowedTiers.length > 0 ? allowedTiers.map((tier) => {
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
                  className={`flex flex-col items-center gap-2 px-3 py-3 border rounded-lg text-sm font-medium transition-colors min-h-[72px] touch-manipulation ${amount === tier.min_amount.toString() ? tDisplay.bgColor + ' ' + tDisplay.color + ' border-purple-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
                >
                  <div className="flex items-center gap-2">
                    <TIcon size={16} className={tDisplay.color} />
                    <span className="font-semibold">{tier.display_name}</span>
                    {(tier.name === 'sapphire' || tier.name === 'diamond') && (
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs font-bold rounded uppercase">HD</span>
                    )}
                  </div>
                  <span className="text-lg font-bold text-gray-900">${tier.min_amount}</span>
                </button>
              );
            }) : (
              <div className="col-span-2 sm:col-span-3 text-center text-gray-500 text-sm py-4">
                Loading tiers...
              </div>
            )}
            {/* Custom Amount as last grid cell */}
            <div className="flex flex-col items-center gap-2 px-3 py-3 border border-gray-300 rounded-lg min-h-[72px]">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">💰</span>
                <span className="font-semibold text-gray-700">Custom</span>
              </div>
              <div className="relative">
                <span className="absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-500 text-sm">$</span>
                <input
                  type="number"
                  min={allowedTiers && allowedTiers.length > 0 ? allowedTiers[0]?.min_amount || 1 : 1}
                  step="0.01"
                  value={customAmount}
                  onChange={e => {
                    setCustomAmount(e.target.value);
                    setAmount(e.target.value);
                    if (paymentIntentId) updatePaymentIntent();
                  }}
                  className="w-20 border border-gray-300 rounded-lg pl-6 pr-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent text-center"
                  placeholder="10"
                />
              </div>
            </div>
          </div>
          {isBelowMin && (
            <div className="text-sm text-red-500 bg-red-50 p-3 rounded-lg border border-red-200 mb-3">
              Minimum for {currentTier?.display_name} is ${minAmount.toFixed(2)}
            </div>
          )}
          <div className="text-sm text-gray-600 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-blue-600 font-semibold">✨ Premium Quality:</span>
            </div>
            <p>Sapphire ($25) and Diamond ($100) commissions include high-definition AI image generation for enhanced detail and quality.</p>
          </div>
        </div>
        {/* Reddit Username and Anonymous Toggle */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Reddit Username
              {!isAnonymous && <span className="text-red-500 ml-1">*</span>}
            </label>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Anonymous</span>
              <button
                type="button"
                onClick={() => {
                  const newAnonymousState = !isAnonymous;
                  setIsAnonymous(newAnonymousState);
                  if (newAnonymousState) {
                    setPreviousRedditUsername(redditUsername);
                    setRedditUsername('');
                  } else {
                    setRedditUsername(previousRedditUsername);
                  }
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none touch-manipulation ${isAnonymous ? 'bg-purple-500' : 'bg-gray-300'}`}
                aria-pressed={isAnonymous}
                aria-label="Toggle anonymous commission"
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${isAnonymous ? 'translate-x-5' : 'translate-x-1'}`}
                />
              </button>
            </div>
          </div>
          <div className="flex items-center">
            <span className="px-3 py-2 bg-gray-100 border border-gray-300 rounded-l text-gray-500 select-none">u/</span>
            <input
              type="text"
              value={redditUsername}
              onChange={e => {
                // Remove any leading u/, spaces, and enforce max length
                const val = e.target.value.replace(/^u\//i, '').replace(/\s/g, '');
                if (val.length > 20) {
                  setUsernameError('Reddit username must be at most 20 characters.');
                } else {
                  setUsernameError(null);
                }
                setRedditUsername(val.slice(0, 20));
              }}
              className={`flex-1 px-3 py-2 border-t border-b border-r border-gray-300 rounded-r focus:outline-none focus:ring-2 focus:ring-purple-500 ${isAnonymous ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`}
              placeholder="yourusername"
              disabled={isAnonymous}
              required={!isAnonymous}
              maxLength={20}
              autoComplete="off"
            />
          </div>
          <div className="text-xs text-gray-500">Do not include <span className="font-mono">u/</span>—just your username.</div>
          {!isAnonymous && !redditUsername.trim() && (
            <p className="text-xs text-red-500 bg-red-50 p-2 rounded border border-red-200">Reddit username is required unless you select Anonymous.</p>
          )}
          {usernameError && <div className="text-xs text-red-600 bg-red-50 p-2 rounded border border-red-200">{usernameError}</div>}
        </div>
        {/* Commission Message */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Commission Message <span className="text-gray-400 font-normal">(optional)</span>
          </label>
          <textarea
            className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
            placeholder="Describe your commission (max 100 characters)"
            value={commissionMessage}
            maxLength={100}
            rows={3}
            onChange={e => {
              if (e.target.value.length <= 100) {
                setCommissionMessage(e.target.value);
                if (messageError) setMessageError(null);
              }
            }}
          />
          <div className="flex justify-between text-xs text-gray-500">
            <span>{commissionMessage.length}/100</span>
            {messageError && <span className="text-red-600">{messageError}</span>}
          </div>
        </div>
        {/* Customer Information */}
        <div className="space-y-4 mt-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email Address *</label>
            <input
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-base"
              placeholder="your@email.com"
              pattern="[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$"
              title="Please enter a valid email address"
            />
            {customerEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(customerEmail) && (
              <p className="text-xs text-red-500 bg-red-50 p-2 rounded border border-red-200 mt-2">Please enter a valid email address</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name (optional)</label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-base"
              placeholder="Your Name"
            />
            <p className="text-xs text-gray-500 bg-gray-50 p-2 rounded border border-gray-200 mt-2">
              Required for card payments, optional for Apple Pay/Google Pay/PayPal
            </p>
          </div>
        </div>
        {/* Payment Area UX */}
        <div className="border-t pt-6 min-h-[340px] relative">
          {validationResult && validationResult.valid && clientSecret ? (
            <div className={`transition-opacity duration-300 ${stripeElementsReady ? 'opacity-100' : 'opacity-0'}`}>
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
              >
                <CommissionFormWrapper
                  amount={amount}
                  commissionMessage={commissionMessage}
                  customerEmail={customerEmail}
                  customerName={customerName}
                  redditUsername={redditUsername}
                  isAnonymous={isAnonymous}
                  subreddit={validationResult?.subreddit || subreddit}
                  postId={validationResult?.post_id || postId}
                  onSuccess={handleSuccess}
                  onError={handleError}
                  onElementsReady={() => setStripeElementsReady(true)}
                />
              </Elements>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center min-h-[200px] text-gray-500">
              {isValidating ? (
                <>
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mb-4"></div>
                  <span>Validating subreddit...</span>
                </>
              ) : validationError ? (
                <>
                  <span className="mb-2 text-lg text-red-500">⚠️</span>
                  <span className="text-red-600">{validationError}</span>
                </>
              ) : (
                <>
                  <span className="mb-2 text-lg">🖌️</span>
                  <span>
                    {commissionType === COMMISSION_TYPES.SUBREDDIT && !subreddit && 'Please select a subreddit to continue.'}
                    {commissionType === COMMISSION_TYPES.SPECIFIC && !postId && 'Please enter a post ID or URL to continue.'}
                    {commissionType === COMMISSION_TYPES.RANDOM && 'Generating a random commission...'}
                  </span>
                </>
              )}
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