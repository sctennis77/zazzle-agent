import axios from 'axios';
import type { ProductSubredditPost } from '../types/productTypes';

const API_BASE = '/api/publish';

export const publishService = {
  /**
   * Publish a product to the clouvel subreddit
   */
  async publishProduct(productId: string, dryRun: boolean = true): Promise<ProductSubredditPost> {
    const response = await axios.post<ProductSubredditPost>(
      `${API_BASE}/product/${productId}`,
      null,
      {
        params: { dry_run: dryRun }
      }
    );
    return response.data;
  },

  /**
   * Get the ProductSubredditPost for a given product
   */
  async getProductSubredditPost(productId: string): Promise<ProductSubredditPost | null> {
    try {
      const response = await axios.get<ProductSubredditPost>(
        `${API_BASE}/product/${productId}`
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null; // Product not published yet
      }
      throw error;
    }
  }
}; 