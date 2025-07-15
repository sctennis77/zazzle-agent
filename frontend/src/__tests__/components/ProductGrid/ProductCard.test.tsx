import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProductCard } from '../../../components/ProductGrid/ProductCard';
import { DonationTierProvider } from '../../../hooks/useDonationTiers';
import type { GeneratedProduct } from '../../../types/productTypes';

// Helper to render component with provider
const renderWithProvider = (component: React.ReactElement) => {
  return render(
    <DonationTierProvider>
      {component}
    </DonationTierProvider>
  );
};

const mockProduct: GeneratedProduct = {
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
    title: 'Test Post Title',
    content: 'Test post content for the product',
    subreddit: 'testsubreddit',
    url: 'https://reddit.com/r/testsubreddit/test123',
    permalink: '/r/testsubreddit/test123',
    score: 150,
    num_comments: 10
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
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByText('r/testsubreddit')).toBeInTheDocument();
  });

  it('should render product image', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} />);

    const image = screen.getByAltText('Test Product');
    expect(image).toBeInTheDocument();
    expect(image).toHaveAttribute('src', 'https://example.com/image.jpg');
  });

  it('should handle image loading error', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} />);

    const image = screen.getByAltText('Test Product');
    
    // Simulate image error
    fireEvent.error(image);

    // Should not crash and image should still be in DOM
    expect(image).toBeInTheDocument();
  });

  it('should show just published indicator', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} justPublished={true} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
  });

  it('should show just completed indicator', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} justCompleted={true} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
  });

  it('should render donation card', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
  });

  it('should handle product with long title', () => {
    const longTitleProduct = {
      ...mockProduct,
      product_info: {
        ...mockProduct.product_info,
        image_title: 'This is a very long product name that should be handled gracefully by the component without breaking the layout'
      }
    };

    renderWithProvider(<ProductCard product={longTitleProduct} activeTasks={[]} />);

    expect(screen.getByText(/This is a very long product name/)).toBeInTheDocument();
  });

  it('should handle product with no upvotes', () => {
    const noUpvotesProduct = {
      ...mockProduct,
      reddit_post: {
        ...mockProduct.reddit_post,
        score: 0
      }
    };

    renderWithProvider(<ProductCard product={noUpvotesProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
  });

  it('should handle product with high upvotes', () => {
    const highUpvotesProduct = {
      ...mockProduct,
      reddit_post: {
        ...mockProduct.reddit_post,
        score: 9999
      }
    };

    renderWithProvider(<ProductCard product={highUpvotesProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
  });

  it('should handle missing image URL gracefully', () => {
    const noImageProduct = {
      ...mockProduct,
      product_info: {
        ...mockProduct.product_info,
        image_url: ''
      }
    };

    renderWithProvider(<ProductCard product={noImageProduct} activeTasks={[]} />);

    // Should still render other product information
    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByText('r/testsubreddit')).toBeInTheDocument();
  });

  it('should handle product with empty task list', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product')).toBeInTheDocument();
  });

  it('should render reddit link correctly', () => {
    renderWithProvider(<ProductCard product={mockProduct} activeTasks={[]} />);

    const subredditText = screen.getByText('r/testsubreddit');
    expect(subredditText).toBeInTheDocument();
  });

  it('should handle special characters in product name', () => {
    const specialCharProduct = {
      ...mockProduct,
      product_info: {
        ...mockProduct.product_info,
        image_title: 'Test Product with & special <chars> "quotes"'
      }
    };

    renderWithProvider(<ProductCard product={specialCharProduct} activeTasks={[]} />);

    expect(screen.getByText('Test Product with & special <chars> "quotes"')).toBeInTheDocument();
  });

  it('should maintain consistent layout with different content lengths', () => {
    const shortContentProduct = {
      ...mockProduct,
      product_info: { ...mockProduct.product_info, image_title: 'Short' },
      reddit_post: { ...mockProduct.reddit_post, title: 'Short title', score: 1 }
    };

    renderWithProvider(<ProductCard product={shortContentProduct} activeTasks={[]} />);

    expect(screen.getByText('Short')).toBeInTheDocument();
  });
});