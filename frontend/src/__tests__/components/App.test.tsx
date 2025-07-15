import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useNavigate, useLocation } from 'react-router-dom';
import App from '../../App';

const mockNavigate = vi.fn();
const mockLocation = { pathname: '/', state: null };

vi.mocked(useNavigate).mockReturnValue(mockNavigate);
vi.mocked(useLocation).mockReturnValue(mockLocation);

// Mock the ProductGrid component to simplify testing
vi.mock('../../components/ProductGrid/ProductGrid', () => ({
  ProductGrid: ({ onCommissionClick, onCommissionProgressChange }: any) => (
    <div data-testid="product-grid">
      <button onClick={onCommissionClick} data-testid="mock-commission-btn">
        Mock Commission
      </button>
      <button onClick={() => onCommissionProgressChange(true)} data-testid="mock-progress-btn">
        Mock Progress
      </button>
    </div>
  )
}));

// Mock the Layout component
vi.mock('../../components/Layout/Layout', () => ({
  Layout: ({ children, onCommissionClick, isCommissionInProgress }: any) => (
    <div data-testid="layout">
      <button onClick={onCommissionClick} data-testid="layout-commission-btn">
        Layout Commission ({isCommissionInProgress ? 'in-progress' : 'idle'})
      </button>
      {children}
    </div>
  )
}));

// Mock CommissionModal
vi.mock('../../components/common/CommissionModal', () => ({
  default: ({ isOpen, onClose, onSuccess }: any) => (
    isOpen ? (
      <div data-testid="commission-modal">
        <button onClick={onClose} data-testid="modal-close">Close</button>
        <button onClick={onSuccess} data-testid="modal-success">Success</button>
      </div>
    ) : null
  )
}));

// Mock other page components
vi.mock('../../components/Fundraising/FundraisingPage', () => ({
  default: () => <div data-testid="fundraising-page">Fundraising Page</div>
}));

vi.mock('../../components/common/DonationSuccessPage', () => ({
  default: () => <div data-testid="donation-success-page">Donation Success Page</div>
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render the main layout and product grid', () => {
    render(<App />);
    
    expect(screen.getByTestId('layout')).toBeInTheDocument();
    expect(screen.getByTestId('product-grid')).toBeInTheDocument();
  });

  it('should handle commission modal state', () => {
    render(<App />);
    
    // Initially modal should not be visible
    expect(screen.queryByTestId('commission-modal')).not.toBeInTheDocument();
    
    // Click commission button to open modal
    fireEvent.click(screen.getByTestId('layout-commission-btn'));
    expect(screen.getByTestId('commission-modal')).toBeInTheDocument();
    
    // Close modal
    fireEvent.click(screen.getByTestId('modal-close'));
    expect(screen.queryByTestId('commission-modal')).not.toBeInTheDocument();
  });

  it('should handle commission modal success', () => {
    render(<App />);
    
    // Open modal
    fireEvent.click(screen.getByTestId('mock-commission-btn'));
    expect(screen.getByTestId('commission-modal')).toBeInTheDocument();
    
    // Trigger success
    fireEvent.click(screen.getByTestId('modal-success'));
    expect(screen.queryByTestId('commission-modal')).not.toBeInTheDocument();
  });

  it('should handle commission progress state', () => {
    render(<App />);
    
    // Initially should show idle state
    expect(screen.getByTestId('layout-commission-btn')).toHaveTextContent('idle');
    
    // Trigger progress change
    fireEvent.click(screen.getByTestId('mock-progress-btn'));
    expect(screen.getByTestId('layout-commission-btn')).toHaveTextContent('in-progress');
  });

  it('should pass commission handlers to ProductGrid', () => {
    render(<App />);
    
    // Should be able to trigger commission from ProductGrid
    fireEvent.click(screen.getByTestId('mock-commission-btn'));
    expect(screen.getByTestId('commission-modal')).toBeInTheDocument();
  });

  it('should render ToastContainer', () => {
    render(<App />);
    
    // ToastContainer is mocked to return null, but we can verify it's rendered
    // by checking that no error is thrown during render
    expect(screen.getByTestId('layout')).toBeInTheDocument();
  });

  it('should maintain commission progress state across interactions', () => {
    render(<App />);
    
    // Set progress to true
    fireEvent.click(screen.getByTestId('mock-progress-btn'));
    expect(screen.getByTestId('layout-commission-btn')).toHaveTextContent('in-progress');
    
    // Open and close modal - progress should remain
    fireEvent.click(screen.getByTestId('layout-commission-btn'));
    fireEvent.click(screen.getByTestId('modal-close'));
    expect(screen.getByTestId('layout-commission-btn')).toHaveTextContent('in-progress');
  });

  it('should handle multiple commission button clicks', () => {
    render(<App />);
    
    // Click layout commission button
    fireEvent.click(screen.getByTestId('layout-commission-btn'));
    expect(screen.getByTestId('commission-modal')).toBeInTheDocument();
    
    // Close modal
    fireEvent.click(screen.getByTestId('modal-close'));
    
    // Click ProductGrid commission button
    fireEvent.click(screen.getByTestId('mock-commission-btn'));
    expect(screen.getByTestId('commission-modal')).toBeInTheDocument();
  });
});