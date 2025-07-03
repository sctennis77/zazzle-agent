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
            // Auto-redirect after 4 seconds
            const timeout = window.setTimeout(() => {
              navigate('/');
            }, 4000);
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

  if (loading) return (
    <div className="p-8 text-center">
      <div>Loading your donation details...</div>
      {attempts > 0 && (
        <div className="text-sm text-gray-500 mt-2">
          Attempt {attempts}/15 - This may take a few seconds while we process your payment.
        </div>
      )}
    </div>
  );
  if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
  if (!donation) return <div className="p-8 text-center text-gray-600">No donation found.</div>;

  return (
    <div className="donation-success-page">
      {loading && <div>Processing your donation...</div>}
      {error && <div className="error">{error}</div>}
      {showSuccess && donation && (
        <div className="success-notification">
          <h2>Thank you for your donation!</h2>
          <p>Tier: <b>{donation.tier}</b></p>
          <p>Amount: <b>${donation.amount_usd}</b></p>
          <p>Subreddit: <b>{donation.subreddit}</b></p>
          <p>Commission Type: <b>{donation.commission_type}</b></p>
          <p>Message: {donation.commission_message || '—'}</p>
          <div style={{ marginTop: '1em' }}>
            <button onClick={() => navigate('/')} className="go-to-gallery-btn">
              Go to Gallery Now
            </button>
            <div style={{ fontSize: '0.9em', color: '#888', marginTop: '0.5em' }}>
              Redirecting to gallery in a few seconds...
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DonationSuccessPage; 