import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, ExpressCheckoutElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { Modal } from './Modal';

// Initialize Stripe (replace with your publishable key)
const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_key_here');

interface DonationModalProps {
  isOpen: boolean;
  onClose: () => void;
  subreddit: string;
  postId?: string;
}

interface DonationRequest {
  amount_usd: string;
  subreddit: string;
  donation_type: 'commission' | 'support';
  post_id?: string;
  commission_message?: string;
  message?: string;
  customer_email: string;
  customer_name: string;
  reddit_username?: string;
  is_anonymous: boolean;
}

const DonationModal: React.FC<DonationModalProps> = ({ isOpen, onClose, subreddit, postId }) => {
  const [amount, setAmount] = useState('5.00');
  const [donationType, setDonationType] = useState<'commission' | 'support'>('commission');
  const [message, setMessage] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [redditUsername, setRedditUsername] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setIsLoading(true);
    setError('');

    try {
      const donationRequest: DonationRequest = {
        amount_usd: amount,
        subreddit,
        donation_type: donationType,
        post_id: postId,
        commission_message: donationType === 'commission' ? message : undefined,
        message: donationType === 'support' ? message : undefined,
        customer_email: customerEmail,
        customer_name: customerName,
        reddit_username: redditUsername || undefined,
        is_anonymous: isAnonymous,
      };

      const response = await fetch('/api/donations/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(donationRequest),
      });

      if (!response.ok) {
        throw new Error('Failed to create checkout session');
      }

      const { url } = await response.json();
      
      // Redirect to Stripe Checkout
      window.location.href = url;
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Make a Donation">
      <div className="space-y-6">
        {/* Donation Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Donation Type
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                value="commission"
                checked={donationType === 'commission'}
                onChange={(e) => setDonationType(e.target.value as 'commission' | 'support')}
                className="mr-2"
              />
              <span className="text-sm">
                <strong>Commission</strong> - Create a new product from Reddit posts
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="support"
                checked={donationType === 'support'}
                onChange={(e) => setDonationType(e.target.value as 'commission' | 'support')}
                className="mr-2"
              />
              <span className="text-sm">
                <strong>Support</strong> - Support existing posts and subreddit goals
              </span>
            </label>
          </div>
        </div>

        {/* Amount */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Amount (USD)
          </label>
          <input
            type="number"
            min="0.50"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="5.00"
          />
        </div>

        {/* Customer Information */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email Address *
            </label>
            <input
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="your@email.com"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Name
            </label>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Your Name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Reddit Username
            </label>
            <input
              type="text"
              value={redditUsername}
              onChange={(e) => setRedditUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="u/username"
            />
          </div>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={isAnonymous}
              onChange={(e) => setIsAnonymous(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm">Make this donation anonymous</span>
          </label>
        </div>

        {/* Message */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {donationType === 'commission' ? 'Commission Message' : 'Support Message'}
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={3}
            placeholder={donationType === 'commission' 
              ? "Describe what kind of product you'd like created..." 
              : "Leave a message of support..."}
          />
        </div>

        {/* Error Display */}
        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
            {error}
          </div>
        )}

        {/* Express Checkout Element */}
        <div className="border-t pt-6">
          <Elements stripe={stripePromise}>
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
              onConfirm={() => {
                // The Express Checkout Element will handle the payment flow
                // We'll rely on the checkout session redirect for success/failure
              }}
            />
          </Elements>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !customerEmail}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Creating...' : 'Proceed to Payment'}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default DonationModal; 