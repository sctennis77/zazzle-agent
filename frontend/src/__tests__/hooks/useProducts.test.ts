import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { useProducts } from '../../hooks/useProducts';
import type { GeneratedProduct } from '../../types/productTypes';

const mockAxios = vi.mocked(axios);

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
    title: 'Test Post',
    content: 'Test content',
    subreddit: 'test',
    url: 'https://reddit.com/test',
    upvotes: 100,
    created_at: '2023-01-01T00:00:00Z'
  }
};

describe('useProducts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch products successfully', async () => {
    mockAxios.get.mockResolvedValueOnce({
      data: [mockProduct]
    });

    const { result } = renderHook(() => useProducts());

    expect(result.current.loading).toBe(true);
    expect(result.current.products).toEqual([]);
    expect(result.current.error).toBe(null);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.products).toEqual([mockProduct]);
    expect(result.current.error).toBe(null);
    expect(mockAxios.get).toHaveBeenCalledWith('http://localhost:8000/api/generated_products');
  });

  it('should handle API errors', async () => {
    const errorMessage = 'Network error';
    mockAxios.get.mockRejectedValueOnce(new Error(errorMessage));

    const { result } = renderHook(() => useProducts());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.products).toEqual([]);
    expect(result.current.error).toBe(errorMessage);
  });

  it('should handle non-array response', async () => {
    mockAxios.get.mockResolvedValueOnce({
      data: { invalid: 'response' }
    });

    const { result } = renderHook(() => useProducts());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.products).toEqual([]);
    expect(result.current.error).toBe(null);
  });

  it('should refresh products', async () => {
    mockAxios.get.mockResolvedValueOnce({
      data: [mockProduct]
    });

    const { result } = renderHook(() => useProducts());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    mockAxios.get.mockResolvedValueOnce({
      data: [{ ...mockProduct, product_info: { ...mockProduct.product_info, id: 2 } }]
    });

    result.current.refresh();

    await waitFor(() => {
      expect(result.current.products[0].product_info.id).toBe(2);
    });

    expect(mockAxios.get).toHaveBeenCalledTimes(2);
  });

  it('should set products manually', async () => {
    const { result } = renderHook(() => useProducts());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const newProducts = [mockProduct];
    result.current.setProducts(newProducts);

    expect(result.current.products).toEqual(newProducts);
  });
});