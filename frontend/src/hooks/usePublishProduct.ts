import { useState, useCallback } from 'react';
import { publishService } from '../services/publishService';
import type { ProductRedditComment } from '../types/productTypes';

export const usePublishProduct = () => {
  const [publishing, setPublishing] = useState(false);
  const [publishedPost, setPublishedPost] = useState<ProductRedditComment | null>(null);
  const [error, setError] = useState<string | null>(null);

  const publishProduct = useCallback(async (productId: string, dryRun?: boolean) => {
    try {
      setPublishing(true);
      setError(null);
      
      const result = await publishService.publishProduct(productId, dryRun);
      setPublishedPost(result);
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to publish product';
      setError(errorMessage);
      throw err;
    } finally {
      setPublishing(false);
    }
  }, []);

  const getPublishedPost = useCallback(async (productId: string) => {
    try {
      setError(null);
      const result = await publishService.getProductSubredditPost(productId);
      setPublishedPost(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch published post';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    publishing,
    publishedPost,
    error,
    publishProduct,
    getPublishedPost,
    clearError
  };
}; 