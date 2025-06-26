import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import type { GeneratedProduct } from '../../types/productTypes';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  useStripe,
  useElements,
  ExpressCheckoutElement
} from '@stripe/react-stripe-js';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

interface DonationModalProps {
  isOpen: boolean;
  onClose: () => void;
  product: GeneratedProduct;
}

const DonationForm: React.FC<{ product: GeneratedProduct; onClose: () => void }> = ({ product, onClose }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [amount, setAmount] = useState('5.00');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [subreddit, setSubreddit] = useState(product.reddit_post.subreddit || '');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [clientSecret, setClientSecret] = useState<string | null>(null);

  // Create payment intent when amount changes
  useEffect(() => {
    const createPaymentIntent = async () => {
      if (!amount || parseFloat(amount) < 0.50) return;
      
      try {
        setLoading(true);
        setError(null);
        
        const resp = await fetch('/api/donations/create-payment-intent', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            amount_usd: parseFloat(amount),
            customer_email: isAnonymous ? undefined : email || undefined,
            customer_name: isAnonymous ? 'Anonymous' : name || undefined,
            message: message || undefined,
            subreddit: subreddit || undefined,
            reddit_username: redditUsername || undefined,
            is_anonymous: isAnonymous
          })
        });
        
        if (!resp.ok) {
          throw new Error('Failed to create payment intent.');
        }
        
        const data = await resp.json();
        setClientSecret(data.client_secret);
      } catch (err: any) {
        setError(err.message || 'Failed to initialize payment.');
      } finally {
        setLoading(false);
      }
    };

    // Debounce the API call
    const timeoutId = setTimeout(createPaymentIntent, 500);
    return () => clearTimeout(timeoutId);
  }, [amount, name, email, message, subreddit, redditUsername, isAnonymous]);

  // Handle Express Checkout payment
  useEffect(() => {
    if (!stripe || !elements || !clientSecret) return;

    const expressCheckoutElement = elements.getElement('expressCheckout');
    if (!expressCheckoutElement) return;

    const handleConfirm = async (event: any) => {
      if (event.detail.paymentMethod) {
        try {
          setLoading(true);
          setError(null);

          const { error: confirmError } = await stripe.confirmPayment({
            elements,
            clientSecret,
            confirmParams: {
              return_url: window.location.origin,
              payment_method_data: {
                billing_details: {
                  name: isAnonymous ? 'Anonymous' : name || undefined,
                  email: isAnonymous ? undefined : email || undefined,
                },
              },
            },
          });

          if (confirmError) {
            setError(confirmError.message || 'Payment failed.');
          } else {
            setSuccess(true);
            setTimeout(() => {
              onClose();
            }, 3000);
          }
        } catch (err: any) {
          setError(err.message || 'An error occurred.');
        } finally {
          setLoading(false);
        }
      }
    };

    // Use the correct event listener API for Express Checkout Element
    expressCheckoutElement.on('confirm', handleConfirm);
    return () => {
      expressCheckoutElement.off('confirm', handleConfirm);
    };
  }, [stripe, elements, clientSecret, name, email, isAnonymous, onClose]);

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center p-6">
        <div className="text-green-600 mb-4">
          <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <p className="text-lg text-green-600 font-semibold mb-2">Thank you for your support!</p>
        <p className="text-gray-600 text-center">Your donation helps keep this project running.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Donation Details Form */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Amount (USD)</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
            <input
              type="number"
              min="0.50"
              step="0.01"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              className="w-full border border-gray-300 rounded-lg pl-8 pr-3 py-3 focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent"
              placeholder="5.00"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Subreddit (optional)</label>
          <select
            value={subreddit}
            onChange={e => setSubreddit(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-3 focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent bg-white"
          >
            <option value="">None</option>
            <option value={product.reddit_post.subreddit}>{product.reddit_post.subreddit}</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            This helps us track which communities are supporting the project
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Reddit Username (optional)</label>
          <input
            type="text"
            value={redditUsername}
            onChange={e => setRedditUsername(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-3 focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent"
            placeholder="u/your_username"
            disabled={isAnonymous}
          />
          <p className="text-xs text-gray-500 mt-1">
            We'll credit you as a sponsor (unless you choose to donate anonymously)
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Name (optional)</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-3 focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent"
              placeholder="Your name"
              disabled={isAnonymous}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email (optional)</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-3 focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent"
              placeholder="your@email.com"
              disabled={isAnonymous}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Message (optional)</label>
          <textarea
            value={message}
            onChange={e => setMessage(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-3 focus:outline-none focus:ring-2 focus:ring-pink-400 focus:border-transparent"
            rows={3}
            placeholder="Leave a message of support..."
          />
        </div>

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={isAnonymous}
            onChange={e => setIsAnonymous(e.target.checked)}
            id="anonymous"
            className="w-4 h-4 text-pink-600 border-gray-300 rounded focus:ring-pink-500"
          />
          <label htmlFor="anonymous" className="text-sm text-gray-700">
            Donate anonymously
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Express Checkout Element */}
      {clientSecret && !loading && (
        <div className="space-y-4">
          <div className="border-t border-gray-200 pt-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Choose Payment Method</h3>
            <ExpressCheckoutElement />
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-600"></div>
          <span className="ml-3 text-gray-600">Setting up payment...</span>
        </div>
      )}

      {/* Info Text */}
      <div className="text-xs text-gray-500 text-center">
        Your payment is secure and encrypted. We use Stripe to process all payments.
      </div>
    </div>
  );
};

export const DonationModal: React.FC<DonationModalProps> = ({ isOpen, onClose, product }) => {
  const options = {
    mode: 'payment' as const,
    amount: Math.round(parseFloat('5.00') * 100), // Convert to cents
    currency: 'usd' as const,
    appearance: {
      theme: 'stripe' as const,
      variables: {
        colorPrimary: '#ec4899', // Pink color to match theme
        borderRadius: '12px',
      },
    },
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Support this Project">
      <Elements stripe={stripePromise} options={options}>
        <DonationForm product={product} onClose={onClose} />
      </Elements>
    </Modal>
  );
}; 