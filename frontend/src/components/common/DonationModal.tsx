import React, { useState } from 'react';
import { Modal } from './Modal';
import type { GeneratedProduct } from '../../types/productTypes';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements
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
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    if (!stripe || !elements) {
      setError('Stripe is not loaded.');
      setLoading(false);
      return;
    }
    try {
      // Call backend to create payment intent
      const resp = await fetch('/api/donations/create-payment-intent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount_usd: amount,
          customer_email: email,
          customer_name: name,
          message,
          is_anonymous: isAnonymous
        })
      });
      if (!resp.ok) {
        throw new Error('Failed to create payment intent.');
      }
      const data = await resp.json();
      const clientSecret = data.client_secret;
      // Confirm card payment
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: elements.getElement(CardElement)!,
          billing_details: {
            name: isAnonymous ? 'Anonymous' : name || undefined,
            email: isAnonymous ? undefined : email || undefined
          }
        }
      });
      if (result.error) {
        setError(result.error.message || 'Payment failed.');
      } else if (result.paymentIntent && result.paymentIntent.status === 'succeeded') {
        setSuccess(true);
        setTimeout(() => {
          onClose();
        }, 2000);
      } else {
        setError('Payment was not successful.');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center p-6">
        <p className="text-lg text-green-600 font-semibold mb-2">Thank you for your support!</p>
        <p className="text-gray-600 text-center">Your donation helps keep this project running.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Amount (USD)</label>
        <input
          type="number"
          min="0.50"
          step="0.01"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-pink-400"
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Name (optional)</label>
        <input
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-pink-400"
          disabled={isAnonymous}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email (optional)</label>
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-pink-400"
          disabled={isAnonymous}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Message (optional)</label>
        <textarea
          value={message}
          onChange={e => setMessage(e.target.value)}
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-pink-400"
          rows={2}
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={isAnonymous}
          onChange={e => setIsAnonymous(e.target.checked)}
          id="anon"
        />
        <label htmlFor="anon" className="text-sm text-gray-700">Donate anonymously</label>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Card Details</label>
        <div className="border rounded-lg px-3 py-2 bg-white">
          <CardElement options={{ style: { base: { fontSize: '16px' } } }} />
        </div>
      </div>
      {error && <div className="text-red-600 text-sm text-center">{error}</div>}
      <button
        type="submit"
        className="w-full bg-pink-500 hover:bg-pink-600 text-white font-semibold py-2 px-4 rounded-lg transition-colors disabled:opacity-60"
        disabled={loading || !stripe}
      >
        {loading ? 'Processing...' : 'Donate'}
      </button>
    </form>
  );
};

export const DonationModal: React.FC<DonationModalProps> = ({ isOpen, onClose, product }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Support this Project">
      <Elements stripe={stripePromise}>
        <DonationForm product={product} onClose={onClose} />
      </Elements>
    </Modal>
  );
}; 