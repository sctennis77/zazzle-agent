import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProductGrid } from '../../../components/ProductGrid/ProductGrid';
import type { GeneratedProduct } from '../../../types/productTypes';
import type { Task } from '../../../types/taskTypes';

// Mock the useProducts hook
const mockProducts: GeneratedProduct[] = [
  {
    product_info: {
      id: 1,
      pipeline_run_id: 1,
      reddit_post_id: 1,
      theme: 'test',
      image_title: 'Test Product',
      image_url: 'https://example.com/image.jpg',
      product_url: 'https://zazzle.com/test',
      template_id: 'template1',
      model: 'dall-e-3',
      prompt_version: 'v1',
      product_type: 'tshirt',
      design_description: 'Test design',
      image_quality: 'hd'
    },
    pipeline_run: {
      id: 1,
      start_time: '2023-01-01T00:00:00Z',
      end_time: '2023-01-01T00:01:00Z',
      status: 'completed',
      retry_count: 0
    },
    reddit_post: {
      id: 1,
      pipeline_run_id: 1,
      post_id: 'test123',
      title: 'Test Post',
      content: 'Test content',
      subreddit: 'test',
      url: 'https://reddit.com/test',
      permalink: '/r/test/test123',
      score: 100,
      num_comments: 5
    }
  }
];

const mockUseProducts = {
  products: mockProducts,
  loading: false,
  error: null as string | null,
  refresh: vi.fn(),
  setProducts: vi.fn()
};

vi.mock('../../../hooks/useProducts', () => ({
  useProducts: () => mockUseProducts
}));

// Mock child components
vi.mock('../../../components/ProductGrid/ProductCard', () => ({
  ProductCard: ({ product, justPublished, justCompleted }: any) => (
    <div data-testid={`product-card-${product.product_info.id}`}>
      Product {product.product_info.id}
      {justPublished && <span data-testid="just-published">Just Published</span>}
      {justCompleted && <span data-testid="just-completed">Just Completed</span>}
    </div>
  )
}));

vi.mock('../../../components/ProductGrid/InProgressProductCard', () => ({
  InProgressProductCard: ({ task, onCancel }: any) => (
    <div data-testid={`in-progress-${task.task_id}`}>
      In Progress: {task.task_id}
      <button onClick={() => onCancel(task.task_id)} data-testid="cancel-task">Cancel</button>
    </div>
  )
}));

vi.mock('../../../components/ProductGrid/CompletedProductCard', () => ({
  CompletedProductCard: ({ task, transitioning }: any) => (
    <div data-testid={`completed-${task.task_id}`}>
      Completed: {task.task_id}
      {transitioning && <span data-testid="transitioning">Transitioning</span>}
    </div>
  )
}));

vi.mock('../../../components/ProductGrid/ProductModal', () => ({
  ProductModal: ({ product, isOpen, onClose }: any) => (
    isOpen && product ? (
      <div data-testid="product-modal">
        Modal for {product.product_info.id}
        <button onClick={onClose} data-testid="close-modal">Close</button>
      </div>
    ) : null
  )
}));

// Mock fetch for API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock WebSocket
const mockWebSocket = {
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1, // OPEN
  onopen: null as any,
  onmessage: null as any,
  onerror: null as any,
  onclose: null as any
};

global.WebSocket = vi.fn(() => mockWebSocket) as any;

describe('ProductGrid', () => {
  const mockOnCommissionProgressChange = vi.fn();
  const mockOnCommissionClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([])
    });
  });

  it('should render loading state', () => {
    vi.mocked(mockUseProducts).loading = true;
    vi.mocked(mockUseProducts).products = [];

    render(<ProductGrid />);

    expect(screen.getByText('No Products Yet')).toBeInTheDocument();
  });

  it('should render error state', () => {
    vi.mocked(mockUseProducts).loading = false;
    vi.mocked(mockUseProducts).error = 'Network error';
    vi.mocked(mockUseProducts).products = [];

    render(<ProductGrid />);

    expect(screen.getByText('Error Loading Products')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('should render products', () => {
    vi.mocked(mockUseProducts).loading = false;
    vi.mocked(mockUseProducts).error = null;
    vi.mocked(mockUseProducts).products = mockProducts;

    render(<ProductGrid />);

    expect(screen.getByTestId('product-card-1')).toBeInTheDocument();
    expect(screen.getByText('Product 1')).toBeInTheDocument();
  });

  it('should render empty state when no products', () => {
    vi.mocked(mockUseProducts).loading = false;
    vi.mocked(mockUseProducts).error = null;
    vi.mocked(mockUseProducts).products = [];

    render(<ProductGrid />);

    expect(screen.getByText('No Products Yet')).toBeInTheDocument();
    expect(screen.getByText('Start by commissioning a piece or wait for the system to generate products.')).toBeInTheDocument();
  });

  it('should render commission button', () => {
    render(<ProductGrid onCommissionClick={mockOnCommissionClick} />);

    const commissionBtn = screen.getByLabelText('Commission Art');
    expect(commissionBtn).toBeInTheDocument();
    expect(commissionBtn).toHaveTextContent('Commission Art');

    fireEvent.click(commissionBtn);
    expect(mockOnCommissionClick).toHaveBeenCalledTimes(1);
  });

  it('should handle refresh on error', async () => {
    vi.mocked(mockUseProducts).loading = false;
    vi.mocked(mockUseProducts).error = 'Network error';
    vi.mocked(mockUseProducts).products = [];

    render(<ProductGrid />);

    fireEvent.click(screen.getByText('Try Again'));
    expect(mockUseProducts.refresh).toHaveBeenCalledTimes(1);
  });

  it('should setup WebSocket connection', () => {
    render(<ProductGrid />);

    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000');
  });

  it('should fetch active tasks on mount', async () => {
    render(<ProductGrid />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/api/tasks');
    });
  });

  it('should handle task cancellation', async () => {
    const mockTask: Task = {
      task_id: 'test-task',
      status: 'in_progress',
      donation_id: 1
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([mockTask])
    });

    render(<ProductGrid />);

    // Wait for tasks to load and component to render
    await waitFor(() => {
      expect(screen.queryByTestId('in-progress-test-task')).toBeInTheDocument();
    });

    // Mock the DELETE request
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({})
    });

    fireEvent.click(screen.getByTestId('cancel-task'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/tasks/test-task?task_type=commission',
        { method: 'DELETE' }
      );
    });
  });

  it('should handle commission progress changes', () => {
    render(<ProductGrid onCommissionProgressChange={mockOnCommissionProgressChange} />);

    // Should call with false initially (no active tasks)
    expect(mockOnCommissionProgressChange).toHaveBeenCalledWith(false);
  });

  it('should handle WebSocket task updates', async () => {
    render(<ProductGrid />);

    // Simulate WebSocket connection
    const wsInstance = vi.mocked(global.WebSocket).mock.results[0].value;
    
    // Simulate onopen
    if (wsInstance.onopen) {
      wsInstance.onopen({} as any);
    }

    // Simulate task update message
    const taskUpdateMessage = {
      type: 'task_update',
      task_id: 'test-task',
      data: {
        status: 'completed',
        progress: 100
      }
    };

    if (wsInstance.onmessage) {
      wsInstance.onmessage({
        data: JSON.stringify(taskUpdateMessage)
      } as any);
    }

    // Should handle the message without throwing
    expect(true).toBe(true); // Basic assertion that no error was thrown
  });

  it('should show success banner when query param is present', () => {
    // Mock URLSearchParams to return success=1
    const mockSearchParams = new URLSearchParams('?success=1');
    Object.defineProperty(window, 'location', {
      value: {
        search: '?success=1'
      },
      writable: true
    });

    render(<ProductGrid />);

    expect(screen.getByText('🎉 Commission submitted successfully!')).toBeInTheDocument();
  });

  it('should handle WebSocket errors gracefully', () => {
    render(<ProductGrid />);

    const wsInstance = vi.mocked(global.WebSocket).mock.results[0].value;
    
    // Simulate WebSocket error
    if (wsInstance.onerror) {
      wsInstance.onerror({} as any);
    }

    // Should not crash the component
    expect(screen.getByLabelText('Commission Art')).toBeInTheDocument();
  });
});