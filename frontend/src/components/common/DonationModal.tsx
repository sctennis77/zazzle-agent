import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, ExpressCheckoutElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from './Modal';

// Initialize Stripe
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_key_here');

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
  donation_type: 'commission' | 'support';
  post_id?: string;
  commission_message?: string;
  message?: string;
  customer_email?: string;
  customer_name?: string;
  reddit_username?: string;
  is_anonymous: boolean;
}

// Component that uses the Express Checkout Element
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
      const { error } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/donation/success`,
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
      
      {isProcessing && (
        <div className="text-center text-sm text-gray-600">
          Processing payment...
        </div>
      )}
    </div>
  );
};

const DonationModal: React.FC<DonationModalProps> = ({ isOpen, onClose, subreddit, postId, supportOnly = false }) => {
  const [amount, setAmount] = useState('10');
  const [message, setMessage] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [customAmount, setCustomAmount] = useState('');
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [showMessage, setShowMessage] = useState(false);
  const presetAmounts = [5, 10, 25, 50, 100];

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setAmount('10');
      setCustomAmount('');
      setMessage('');
      setCustomerEmail('');
      setCustomerName('');
      setRedditUsername('');
      setIsAnonymous(false);
      setError('');
      setSuccess(false);
      setClientSecret(null);
      setShowMessage(false);
    }
  }, [isOpen]);

  // Create payment intent when form data changes
  useEffect(() => {
    const createPaymentIntent = async () => {
      if (!isOpen || !amount) return;

      // For support donations, post_id is required
      if (!postId) {
        setError('Post ID is required for support donations');
        setClientSecret(null);
        return;
      }

      // Name is only required for card payments, not for Express Checkout methods
      // We'll let Stripe handle the validation based on the payment method chosen

      try {
        const donationRequest: DonationRequest = {
          amount_usd: amount,
          subreddit,
          donation_type: 'support',
          post_id: postId,
          message: message,
          customer_email: customerEmail || undefined,
          customer_name: customerName || undefined, // Make optional
          reddit_username: redditUsername || undefined,
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

        const { client_secret } = await response.json();
        setClientSecret(client_secret);
        setError(''); // Clear any previous errors
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Failed to create payment intent');
        setClientSecret(null);
      }
    };

    createPaymentIntent();
  }, [isOpen, amount, customerName, customerEmail, redditUsername, isAnonymous, message, subreddit, postId]);

  const handleSuccess = () => {
    setSuccess(true);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

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
          <p className="text-gray-600 text-center">Your donation helps keep this project running.</p>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={supportOnly ? 'Support This Post' : 'Make a Donation'}>
      <div className="space-y-6 p-6">
        {/* Preset Amount Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Choose Amount</label>
          <div className="grid grid-cols-3 gap-2 mb-2">
            {presetAmounts.map((preset, idx) => (
              <button
                key={preset}
                type="button"
                onClick={() => { setAmount(preset.toString()); setCustomAmount(''); }}
                className={`px-2 py-1 border rounded-lg text-xs font-medium transition-colors h-9 ${amount === preset.toString() ? 'bg-pink-600 text-white border-pink-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
              >
                ${preset}
              </button>
            ))}
            {/* Custom Amount as last grid cell */}
            <div className="relative flex items-center h-9">
              <span className="absolute left-2 text-gray-500 text-xs">$</span>
              <input
                type="number"
                min="0.50"
                step="0.01"
                value={customAmount}
                onChange={e => { setCustomAmount(e.target.value); setAmount(e.target.value); }}
                className="w-full border border-gray-300 rounded-lg pl-5 pr-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent h-9"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name (optional)</label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                className={`w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${isAnonymous ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''}`}
                placeholder="u/username"
                disabled={isAnonymous}
              />
            </div>
            <div className="flex flex-col items-center justify-end h-full">
              <label className="text-xs text-gray-600 mb-1">Anonymous</label>
              <button
                type="button"
                onClick={() => setIsAnonymous((v) => !v)}
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
              className="text-xs text-blue-500 underline mb-2"
              onClick={() => setShowMessage(true)}
            >
              + Add a support message
            </button>
          )}
          {showMessage && (
            <>
              <button
                type="button"
                className="text-xs text-blue-500 underline mb-2"
                onClick={() => setShowMessage(false)}
              >
                – Hide support message
              </button>
              <label className="block text-sm font-medium text-gray-700 mb-2 mt-2">Support Message</label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
                placeholder="Leave a message of support..."
              />
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
                    colorPrimary: '#ec4899',
                  },
                },
              }}
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

export default DonationModal; 