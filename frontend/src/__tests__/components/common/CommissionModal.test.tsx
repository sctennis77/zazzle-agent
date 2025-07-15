import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useNavigate } from 'react-router-dom';
import CommissionModal from '../../../components/common/CommissionModal';
import { DonationTierProvider } from '../../../hooks/useDonationTiers';

const mockNavigate = vi.fn();
vi.mocked(useNavigate).mockReturnValue(mockNavigate);

const mockTiers = [
  { name: 'bronze', min_amount: 1, display_name: 'Bronze' },
  { name: 'silver', min_amount: 5, display_name: 'Silver' },
  { name: 'gold', min_amount: 10, display_name: 'Gold' },
  { name: 'diamond', min_amount: 25, display_name: 'Diamond' }
];

const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock Modal component
vi.mock('../../../components/common/Modal', () => ({
  Modal: ({ children, isOpen, title }: any) => (
    isOpen ? (
      <div data-testid="modal">
        <h2>{title}</h2>
        {children}
      </div>
    ) : null
  )
}));

// Mock Stripe components (already mocked in setup, but ensuring they work in this context)
const MockCommissionForm = ({ onSuccess, onError }: any) => (
  <div data-testid="commission-form">
    <button onClick={() => onSuccess('pi_test_123')} data-testid="mock-success">
      Mock Success
    </button>
    <button onClick={() => onError('Mock error')} data-testid="mock-error">
      Mock Error
    </button>
  </div>
);

// Mock the Elements wrapper to pass through the CommissionForm
vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }: any) => children,
  useStripe: vi.fn(() => ({
    confirmPayment: vi.fn()
  })),
  useElements: vi.fn(() => ({})),
  PaymentElement: () => <div data-testid="payment-element">Payment Element</div>,
  ExpressCheckoutElement: ({ onConfirm }: any) => (
    <button onClick={onConfirm} data-testid="express-checkout">
      Express Checkout
    </button>
  ),
}));

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <DonationTierProvider>{children}</DonationTierProvider>
);

describe('CommissionModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSuccess: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock donation tiers API
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/donation-tiers')) {
        return Promise.resolve({
          json: () => Promise.resolve(mockTiers)
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });
  });

  it('should not render when closed', () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} isOpen={false} />
      </TestWrapper>
    );

    expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
  });

  it('should render commission types', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText(/Random/)).toBeInTheDocument();
      expect(screen.getByText(/Random Post/)).toBeInTheDocument();
      expect(screen.getByText(/Specific Post/)).toBeInTheDocument();
    });
  });

  it('should handle commission type selection', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const specificButton = screen.getByText(/Specific Post/);
      fireEvent.click(specificButton);
    });

    expect(screen.getByPlaceholderText(/e.g., 1llckgq/)).toBeInTheDocument();
  });

  it('should show subreddit selector for subreddit commission type', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const subredditButton = screen.getByText(/Random Post/);
      fireEvent.click(subredditButton);
    });

    expect(screen.getByText('Select a subreddit...')).toBeInTheDocument();
  });

  it('should handle amount selection', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const silverButton = screen.getByText('Silver');
      fireEvent.click(silverButton);
    });

    // Should show Silver tier information
    expect(screen.getByText('Silver Tier')).toBeInTheDocument();
  });

  it('should handle custom amount input', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const customInput = screen.getByPlaceholderText('Custom');
      fireEvent.change(customInput, { target: { value: '15' } });
    });

    expect(screen.getByDisplayValue('15')).toBeInTheDocument();
  });

  it('should validate reddit username', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const usernameInput = screen.getByPlaceholderText('yourusername');
      fireEvent.change(usernameInput, { target: { value: 'u/testuser' } });
    });

    expect(screen.getByText(/Do not include 'u\/'—just your username/)).toBeInTheDocument();
  });

  it('should handle anonymous toggle', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const anonymousToggle = screen.getByLabelText('Toggle anonymous commission');
      fireEvent.click(anonymousToggle);
    });

    const usernameInput = screen.getByPlaceholderText('yourusername');
    expect(usernameInput).toBeDisabled();
  });

  it('should validate commission message length', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const messageInput = screen.getByPlaceholderText(/Describe your commission/);
      const longMessage = 'a'.repeat(101);
      fireEvent.change(messageInput, { target: { value: longMessage } });
    });

    expect(screen.getByDisplayValue('a'.repeat(100))).toBeInTheDocument();
  });

  it('should handle email validation', async () => {
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const emailInput = screen.getByPlaceholderText('your@email.com');
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    });

    expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument();
  });

  it('should handle commission validation for specific post', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/donation-tiers')) {
        return Promise.resolve({
          json: () => Promise.resolve(mockTiers)
        });
      }
      if (url.includes('/api/commissions/validate')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            valid: true,
            subreddit: 'golf',
            post_id: '1llckgq',
            post_title: 'Test Golf Post',
            commission_type: 'specific_post'
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });

    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const specificButton = screen.getByText(/Specific Post/);
      fireEvent.click(specificButton);
    });

    const postInput = screen.getByPlaceholderText(/e.g., 1llckgq/);
    fireEvent.change(postInput, { target: { value: '1llckgq' } });

    await waitFor(() => {
      expect(screen.getByText('✅ Commission Validated')).toBeInTheDocument();
    });
  });

  it('should handle validation errors', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/donation-tiers')) {
        return Promise.resolve({
          json: () => Promise.resolve(mockTiers)
        });
      }
      if (url.includes('/api/commissions/validate')) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({
            detail: 'Post not found'
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });

    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const specificButton = screen.getByText(/Specific Post/);
      fireEvent.click(specificButton);
    });

    const postInput = screen.getByPlaceholderText(/e.g., 1llckgq/);
    fireEvent.change(postInput, { target: { value: 'invalid-post' } });

    await waitFor(() => {
      expect(screen.getByText('Post not found')).toBeInTheDocument();
    });
  });

  it('should show payment form when validation succeeds', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/donation-tiers')) {
        return Promise.resolve({
          json: () => Promise.resolve(mockTiers)
        });
      }
      if (url.includes('/api/commissions/validate')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            valid: true,
            subreddit: 'test',
            commission_type: 'random_subreddit'
          })
        });
      }
      if (url.includes('/api/donations/create-payment-intent')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            client_secret: 'pi_test_123_secret',
            payment_intent_id: 'pi_test_123'
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });

    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    await waitFor(() => {
      const subredditButton = screen.getByText(/Random Post/);
      fireEvent.click(subredditButton);
    });

    const subredditSelect = screen.getByText('Select a subreddit...');
    fireEvent.click(subredditSelect);
    
    // Find and select golf option
    const golfOption = screen.getByText('r/golf');
    fireEvent.click(golfOption);

    await waitFor(() => {
      expect(screen.getByTestId('payment-element')).toBeInTheDocument();
    });
  });

  it('should handle successful payment', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/donation-tiers')) {
        return Promise.resolve({
          json: () => Promise.resolve(mockTiers)
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          client_secret: 'pi_test_123_secret',
          payment_intent_id: 'pi_test_123'
        })
      });
    });

    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} />
      </TestWrapper>
    );

    // Wait for validation and payment setup
    await waitFor(() => {
      const mockSuccess = screen.queryByTestId('mock-success');
      if (mockSuccess) {
        fireEvent.click(mockSuccess);
      }
    });

    expect(mockNavigate).toHaveBeenCalledWith('/donation/success?payment_intent=pi_test_123');
  });

  it('should close modal when cancel is clicked', async () => {
    const onClose = vi.fn();
    render(
      <TestWrapper>
        <CommissionModal {...defaultProps} onClose={onClose} />
      </TestWrapper>
    );

    await waitFor(() => {
      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);
    });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('should reset form when modal is reopened', async () => {
    const { rerender } = render(
      <TestWrapper>
        <CommissionModal {...defaultProps} isOpen={false} />
      </TestWrapper>
    );

    rerender(
      <TestWrapper>
        <CommissionModal {...defaultProps} isOpen={true} />
      </TestWrapper>
    );

    await waitFor(() => {
      const usernameInput = screen.getByPlaceholderText('yourusername');
      expect(usernameInput).toHaveValue('');
    });
  });
});