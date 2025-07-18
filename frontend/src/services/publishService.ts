import axios from 'axios';
import type { ProductSubredditPost, ProductRedditComment } from '../types/productTypes';
import { API_BASE } from '../utils/apiBase';

const PUBLISH_API_BASE = `${API_BASE}/api/publish`;

export const publishService = {
  /**
   * Comment on the original Reddit post for a product
   */
  async publishProduct(productId: string, dryRun?: boolean): Promise<ProductRedditComment> {
    const params = dryRun !== undefined ? { dry_run: dryRun } : {};
    const response = await axios.post<ProductRedditComment>(
      `${PUBLISH_API_BASE}/product/${productId}`,
      null,
      { params }
    );
    return response.data;
  },

  /**
   * Get the ProductRedditComment for a given product (with backward compatibility)
   */
  async getProductSubredditPost(productId: string): Promise<ProductRedditComment | null> {
    try {
      const response = await axios.get<ProductRedditComment>(
        `${PUBLISH_API_BASE}/product/${productId}`
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