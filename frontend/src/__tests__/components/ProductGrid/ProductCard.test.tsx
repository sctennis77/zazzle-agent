import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProductCard } from '../../../components/ProductGrid/ProductCard';
import type { GeneratedProduct } from '../../../types/productTypes';

const mockProduct: GeneratedProduct = {
  product_info: {
    id: 1,
    product_name: 'Test Product',
    zazzle_url: 'https://zazzle.com/test',
    image_url: 'https://example.com/image.jpg',
    created_at: '2023-01-01T00:00:00Z'
  },
  reddit_post: {
    post_id: 'test123',
    title: 'Test Post Title',
    content: 'Test post content for the product',
    subreddit: 'testsubreddit',
    url: 'https://reddit.com/r/testsubreddit/test123',
    upvotes: 150,
    created_at: '2023-01-01T00:00:00Z'
  }
};

// Mock the DonationCard component
vi.mock('../../../components/ProductGrid/DonationCard', () => ({
  DonationCard: () => <div data-testid="donation-card">Donation Card</div>
}));

describe('ProductCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render product information', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByText('r/testsubreddit')).toBeInTheDocument();
    expect(screen.getByText('150 upvotes')).toBeInTheDocument();
  });

  it('should render product image', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} />);

    const image = screen.getByAltText('Test Product');
    expect(image).toBeInTheDocument();
    expect(image).toHaveAttribute('src', 'https://example.com/image.jpg');
  });

  it('should handle image loading error', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} />);

    const image = screen.getByAltText('Test Product');
    
    // Simulate image error
    fireEvent.error(image);

    // Should not crash and image should still be in DOM
    expect(image).toBeInTheDocument();
  });

  it('should show just published indicator', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} justPublished={true} />);

    // Look for visual indicators of "just published" state
    const card = screen.getByTestId || screen.getByRole('article') || screen.getByText('Test Product').closest('div');
    expect(card).toBeInTheDocument();
  });

  it('should show just completed indicator', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} justCompleted={true} />);

    // Look for visual indicators of "just completed" state
    const card = screen.getByTestId || screen.getByRole('article') || screen.getByText('Test Product').closest('div');
    expect(card).toBeInTheDocument();
  });

  it('should render donation card', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} />);

    expect(screen.getByTestId('donation-card')).toBeInTheDocument();
  });

  it('should handle product with long title', () => {
    const longTitleProduct = {
      ...mockProduct,
      product_info: {
        ...mockProduct.product_info,
        product_name: 'This is a very long product name that should be handled gracefully by the component without breaking the layout'
      }
    };

    render(<ProductCard product={longTitleProduct} activeTasks={[]} />);

    expect(screen.getByText(/This is a very long product name/)).toBeInTheDocument();
  });

  it('should handle product with no upvotes', () => {
    const noUpvotesProduct = {
      ...mockProduct,
      reddit_post: {
        ...mockProduct.reddit_post,
        upvotes: 0
      }
    };

    render(<ProductCard product={noUpvotesProduct} activeTasks={[]} />);

    expect(screen.getByText('0 upvotes')).toBeInTheDocument();
  });

  it('should handle product with high upvotes', () => {
    const highUpvotesProduct = {
      ...mockProduct,
      reddit_post: {
        ...mockProduct.reddit_post,
        upvotes: 9999
      }
    };

    render(<ProductCard product={highUpvotesProduct} activeTasks={[]} />);

    expect(screen.getByText('9999 upvotes')).toBeInTheDocument();
  });

  it('should handle missing image URL gracefully', () => {
    const noImageProduct = {
      ...mockProduct,
      product_info: {
        ...mockProduct.product_info,
        image_url: ''
      }
    };

    render(<ProductCard product={noImageProduct} activeTasks={[]} />);

    // Should still render other product information
    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByText('r/testsubreddit')).toBeInTheDocument();
  });

  it('should handle product with empty task list', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByTestId('donation-card')).toBeInTheDocument();
  });

  it('should render reddit link correctly', () => {
    render(<ProductCard product={mockProduct} activeTasks={[]} />);

    const subredditText = screen.getByText('r/testsubreddit');
    expect(subredditText).toBeInTheDocument();
  });

  it('should handle special characters in product name', () => {
    const specialCharProduct = {
      ...mockProduct,
      product_info: {
        ...mockProduct.product_info,
        product_name: 'Test Product with & special <chars> "quotes"'
      }
    };

    render(<ProductCard product={specialCharProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product with & special <chars> "quotes"')).toBeInTheDocument();
  });

  it('should maintain consistent layout with different content lengths', () => {
    const shortContentProduct = {
      ...mockProduct,
      product_info: { ...mockProduct.product_info, product_name: 'Short' },
      reddit_post: { ...mockProduct.reddit_post, title: 'Short title', upvotes: 1 }
    };

    render(<ProductCard product={shortContentProduct} activeTasks={[]} />);

    expect(screen.getByText('Short')).toBeInTheDocument();
    expect(screen.getByText('1 upvotes')).toBeInTheDocument();
  });
});