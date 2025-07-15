import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock environment variables
process.env.VITE_STRIPE_PUBLISHABLE_KEY = 'pk_test_mock_key_for_testing';
process.env.VITE_API_BASE = 'http://localhost:8000';
process.env.VITE_WS_BASE = 'ws://localhost:8000';

// Mock Stripe
vi.mock('@stripe/stripe-js', () => ({
  loadStripe: vi.fn(() => Promise.resolve({
    confirmPayment: vi.fn(),
    elements: vi.fn(),
  })),
}));

vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }: { children: React.ReactNode }) => children,
  useStripe: vi.fn(() => ({
    confirmPayment: vi.fn(() => Promise.resolve({
      paymentIntent: { id: 'pi_test_123', status: 'succeeded' },
      error: null
    }))
  })),
  useElements: vi.fn(() => ({})),
  PaymentElement: vi.fn(() => null),
  ExpressCheckoutElement: vi.fn(() => null),
}));

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1, // OPEN
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3,
  onopen: null,
  onclose: null,
  onmessage: null,
  onerror: null,
}));

// Mock fetch for API calls
global.fetch = vi.fn();

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }
}));

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => children,
  Routes: ({ children }: { children: React.ReactNode }) => children,
  Route: () => null,
  useSearchParams: vi.fn(() => [new URLSearchParams(), vi.fn()]),
  useLocation: vi.fn(() => ({ pathname: '/', state: null })),
  useNavigate: vi.fn(() => vi.fn()),
}));

// Mock react-toastify
vi.mock('react-toastify', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  ToastContainer: () => null,
}));

// Mock react-icons
vi.mock('react-icons/fa', () => ({
  FaCrown: () => null,
  FaStar: () => null,
  FaGem: () => null,
  FaHeart: () => null,
}));

// Setup window.location mock
Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:3000',
    pathname: '/',
    search: '',
    hash: '',
  },
  writable: true,
});

// Mock window.history
Object.defineProperty(window, 'history', {
  value: {
    replaceState: vi.fn(),
    pushState: vi.fn(),
  },
  writable: true,
});

// Mock URL constructor for URL manipulation
global.URL = class URL {
  href: string;
  pathname: string;
  search: string;
  searchParams: URLSearchParams;

  constructor(url: string) {
    this.href = url;
    this.pathname = '/';
    this.search = '';
    this.searchParams = new URLSearchParams();
  }

  toString() {
    return this.href;
  }
};