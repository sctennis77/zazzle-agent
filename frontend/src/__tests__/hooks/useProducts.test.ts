import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { useProducts } from '../../hooks/useProducts';
import type { GeneratedProduct } from '../../types/productTypes';

const mockAxios = vi.mocked(axios);
const mockGet = vi.fn();

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
    title: 'Test Post',
    content: 'Test content',
    subreddit: 'test',
    url: 'https://reddit.com/test',
    permalink: '/r/test/test123',
    score: 100,
    num_comments: 5
  }
};

describe('useProducts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAxios.get = mockGet;
  });

  it('should fetch products successfully', async () => {
    mockGet.mockResolvedValueOnce({
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
    mockGet.mockRejectedValueOnce(new Error(errorMessage));

    const { result } = renderHook(() => useProducts());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.products).toEqual([]);
    expect(result.current.error).toBe(errorMessage);
  });

  it('should handle non-array response', async () => {
    mockGet.mockResolvedValueOnce({
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
    mockGet.mockResolvedValueOnce({
      data: [mockProduct]
    });

    const { result } = renderHook(() => useProducts());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    mockGet.mockResolvedValueOnce({
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
    
    act(() => {
      result.current.setProducts(newProducts);
    });

    expect(result.current.products).toEqual(newProducts);
  });
});